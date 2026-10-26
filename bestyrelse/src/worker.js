/*
 * Strong Gym - bestyrelsens økonomiside
 * --------------------------------------
 * Serverer siden under /bestyrelse/ og et lille JSON-API under /bestyrelse/api/.
 *
 * Adgang:
 *   1. Cloudflare Access ligger foran hele /bestyrelse/* og kræver login med
 *      e-mail-kode. Uden login når ingen request frem hertil.
 *   2. Worker'en verificerer selv Access-tokenet (Cf-Access-Jwt-Assertion)
 *      og tjekker e-mailen mod BOARD_EMAILS / VIEW_EMAILS. Så er data også
 *      beskyttet hvis Access-reglen ved en fejl bliver for bred.
 *
 * Fail closed: mangler ACCESS_TEAM_DOMAIN eller ACCESS_AUD, svarer API'et 500,
 * medmindre DEV_MODE="1" (kun i .dev.vars til lokal udvikling).
 */

const BASE = "/bestyrelse";
const API = BASE + "/api";
const MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;
const ID_RE = /^[A-Za-z0-9_-]{1,64}$/;

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === BASE) return Response.redirect(url.origin + BASE + "/", 301);

    if (url.pathname.startsWith(API + "/") || url.pathname === API) {
      try {
        return await handleApi(request, env, url);
      } catch (err) {
        if (err instanceof HttpError) return json({ error: err.message }, err.status);
        console.error(err);
        return json({ error: "Serverfejl" }, 500);
      }
    }

    // Statiske filer (siden selv). Kun under /bestyrelse/.
    if (url.pathname.startsWith(BASE + "/")) return env.ASSETS.fetch(request);
    return new Response("Ikke fundet", { status: 404 });
  },
};

class HttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

/* ---------- adgang ---------- */

const emailList = (s) => String(s || "").split(",").map((e) => e.trim().toLowerCase()).filter(Boolean);

async function identify(request, env) {
  let email;
  const host = new URL(request.url).hostname;
  if (env.DEV_MODE === "1" && (host === "localhost" || host === "127.0.0.1")) {
    email = String(env.DEV_EMAIL || "dev@localhost").toLowerCase();
  } else {
    if (!env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD) throw new HttpError(500, "Adgangskontrol er ikke sat op");
    const token = request.headers.get("Cf-Access-Jwt-Assertion");
    if (!token) throw new HttpError(401, "Ikke logget ind");
    const claims = await verifyAccessJwt(token, env.ACCESS_TEAM_DOMAIN, env.ACCESS_AUD);
    email = String(claims.email || "").toLowerCase();
    if (!email) throw new HttpError(403, "Ingen e-mail i login");
  }
  const writers = emailList(env.BOARD_EMAILS);
  const viewers = emailList(env.VIEW_EMAILS);
  if (writers.includes(email)) return { email, canWrite: true };
  if (viewers.includes(email)) return { email, canWrite: false };
  throw new HttpError(403, "Din e-mail har ikke adgang til bestyrelsessiden");
}

let certCache = { at: 0, keys: null, team: null };

async function accessKeys(team) {
  const now = Date.now();
  if (certCache.keys && certCache.team === team && now - certCache.at < 10 * 60 * 1000) return certCache.keys;
  const res = await fetch(team.replace(/\/$/, "") + "/cdn-cgi/access/certs");
  if (!res.ok) throw new HttpError(502, "Kunne ikke hente Access-nøgler");
  const { keys } = await res.json();
  certCache = { at: now, keys, team };
  return keys;
}

const b64urlBytes = (s) => {
  const b = atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4));
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
};

async function verifyAccessJwt(token, team, aud) {
  const parts = token.split(".");
  if (parts.length !== 3) throw new HttpError(401, "Ugyldigt login");
  let header, payload;
  try {
    header = JSON.parse(new TextDecoder().decode(b64urlBytes(parts[0])));
    payload = JSON.parse(new TextDecoder().decode(b64urlBytes(parts[1])));
  } catch {
    throw new HttpError(401, "Ugyldigt login");
  }
  if (header.alg !== "RS256") throw new HttpError(401, "Ugyldigt login");
  const keys = await accessKeys(team);
  const jwk = keys.find((k) => k.kid === header.kid);
  if (!jwk) { certCache.keys = null; throw new HttpError(401, "Ugyldigt login"); }
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64urlBytes(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
  if (!ok) throw new HttpError(401, "Ugyldigt login");
  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp !== "number" || payload.exp < now) throw new HttpError(401, "Login er udløbet - genindlæs siden");
  if (payload.nbf && payload.nbf > now + 60) throw new HttpError(401, "Ugyldigt login");
  const auds = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
  if (!auds.includes(aud)) throw new HttpError(401, "Ugyldigt login");
  if (payload.iss && payload.iss.replace(/\/$/, "") !== team.replace(/\/$/, "")) throw new HttpError(401, "Ugyldigt login");
  return payload;
}

/* ---------- API ---------- */

async function handleApi(request, env, url) {
  const who = await identify(request, env);
  const path = url.pathname.slice(API.length).replace(/\/+$/, "") || "/";
  const method = request.method;

  if (method !== "GET") {
    if (!who.canWrite) throw new HttpError(403, "Du har kun læseadgang");
    // Beskyttelse mod CSRF: kræv JSON-body og samme origin.
    const origin = request.headers.get("Origin");
    if (origin && origin !== url.origin) throw new HttpError(403, "Forkert afsender");
    if (method !== "DELETE" && !(request.headers.get("Content-Type") || "").includes("application/json")) throw new HttpError(415, "Forventede JSON");
  }

  if (path === "/state" && method === "GET") return json(await loadState(env, who));

  let m;
  if ((m = path.match(/^\/months\/([^/]+)$/))) {
    const month = m[1];
    if (!MONTH_RE.test(month)) throw new HttpError(400, "Ugyldig måned");
    if (method === "PUT") {
      const doc = cleanMonth(await body(request), month);
      await upsert(env, "months", "month", month, doc, who.email);
      await audit(env, who.email, "month.save", month, doc);
      return json({ ok: true });
    }
    if (method === "DELETE") {
      await env.DB.prepare("DELETE FROM months WHERE month = ?").bind(month).run();
      await audit(env, who.email, "month.delete", month, null);
      return json({ ok: true });
    }
  }

  if (path === "/settings" && method === "PUT") {
    const doc = cleanSettings(await body(request));
    await upsert(env, "settings", "id", 1, doc, who.email);
    await audit(env, who.email, "settings.save", "settings", doc);
    return json({ ok: true });
  }

  if (path === "/wishlist" && method === "POST") {
    const doc = cleanWish(await body(request), true);
    const id = crypto.randomUUID().replace(/-/g, "").slice(0, 16);
    doc.addedBy = who.email; doc.addedAt = new Date().toISOString();
    await upsert(env, "wishlist", "id", id, doc, who.email);
    await audit(env, who.email, "wish.add", id, doc);
    return json({ ok: true, id });
  }
  if ((m = path.match(/^\/wishlist\/([^/]+)$/))) {
    const id = m[1];
    if (!ID_RE.test(id)) throw new HttpError(400, "Ugyldigt id");
    if (method === "PATCH") {
      const row = await env.DB.prepare("SELECT data FROM wishlist WHERE id = ?").bind(id).first();
      if (!row) throw new HttpError(404, "Ønsket findes ikke");
      const doc = Object.assign(JSON.parse(row.data), cleanWish(await body(request), false));
      await upsert(env, "wishlist", "id", id, doc, who.email);
      await audit(env, who.email, "wish.update", id, doc);
      return json({ ok: true });
    }
    if (method === "DELETE") {
      await env.DB.prepare("DELETE FROM wishlist WHERE id = ?").bind(id).run();
      await audit(env, who.email, "wish.delete", id, null);
      return json({ ok: true });
    }
  }

  if (path === "/sample" && method === "DELETE") {
    await env.DB.batch([
      env.DB.prepare("DELETE FROM months WHERE json_extract(data, '$.sample') = 1"),
      env.DB.prepare("DELETE FROM wishlist WHERE json_extract(data, '$.sample') = 1"),
      env.DB.prepare("UPDATE settings SET data = json_set(data, '$.sample', json('false')) WHERE id = 1"),
    ]);
    await audit(env, who.email, "sample.delete", "*", null);
    return json({ ok: true });
  }

  throw new HttpError(404, "Ukendt handling");
}

async function loadState(env, who) {
  const [months, wish, settings] = await Promise.all([
    env.DB.prepare("SELECT data, updated_by, updated_at FROM months ORDER BY month").all(),
    env.DB.prepare("SELECT id, data FROM wishlist").all(),
    env.DB.prepare("SELECT data FROM settings WHERE id = 1").first(),
  ]);
  return {
    me: { email: who.email, canWrite: who.canWrite },
    settings: settings ? JSON.parse(settings.data) : null,
    months: months.results.map((r) => ({ ...JSON.parse(r.data), updatedBy: r.updated_by, updatedAt: r.updated_at })),
    wishlist: wish.results.map((r) => ({ ...JSON.parse(r.data), id: r.id })),
  };
}

async function upsert(env, table, keyCol, key, doc, email) {
  const now = new Date().toISOString();
  await env.DB.prepare(
    `INSERT INTO ${table} (${keyCol}, data, updated_by, updated_at) VALUES (?, ?, ?, ?)
     ON CONFLICT(${keyCol}) DO UPDATE SET data = excluded.data, updated_by = excluded.updated_by, updated_at = excluded.updated_at`
  ).bind(key, JSON.stringify(doc), email, now).run();
}

async function audit(env, email, action, target, data) {
  await env.DB.prepare("INSERT INTO audit (at, email, action, target, data) VALUES (?, ?, ?, ?, ?)")
    .bind(new Date().toISOString(), email, action, String(target), data == null ? null : JSON.stringify(data)).run();
}

async function body(request) {
  const text = await request.text();
  if (text.length > 64 * 1024) throw new HttpError(413, "For stor forespørgsel");
  try { const v = JSON.parse(text); if (v && typeof v === "object" && !Array.isArray(v)) return v; } catch {}
  throw new HttpError(400, "Ugyldig JSON");
}

/* ---------- validering ---------- */

const num = (v, { min = -1e9, max = 1e9, int = false, optional = true } = {}, label = "tal") => {
  if (v === null || v === undefined || v === "") {
    if (optional) return null;
    throw new HttpError(400, `Mangler ${label}`);
  }
  const n = Number(v);
  if (!Number.isFinite(n) || n < min || n > max || (int && !Number.isInteger(n))) throw new HttpError(400, `Ugyldigt ${label}`);
  return n;
};
const text = (v, max) => (v == null ? null : String(v).slice(0, max).trim() || null);

function cleanMonth(b, month) {
  const variable = {};
  if (b.variable && typeof b.variable === "object") {
    for (const [k, v] of Object.entries(b.variable).slice(0, 20)) {
      const name = String(k).slice(0, 40).trim();
      const n = num(v, { min: 0 }, "beløb for " + name);
      if (name && n != null) variable[name] = n;
    }
  }
  return {
    month,
    members: num(b.members, { min: 0, max: 100000, int: true, optional: false }, "antal medlemmer"),
    payroll: num(b.payroll, { min: 0, optional: false }, "lønudgift"),
    hours: num(b.hours, { min: 0, max: 10000 }, "antal timer"),
    variable,
    other_income: num(b.other_income, { min: 0 }, "øvrige indtægter"),
    contingent: num(b.contingent, { min: 0 }, "kontingent"),
    equipment: num(b.equipment, { min: 0 }, "udstyrskøb"),
    cash: num(b.cash, {}, "kassebeholdning"),
    note: text(b.note, 200),
    fixed_income: num(b.fixed_income, { min: 0 }, "faste indtægter"),
    fixed_expenses: num(b.fixed_expenses, { min: 0 }, "faste udgifter"),
    sample: false,
  };
}

function cleanSettings(b) {
  const fixed = Array.isArray(b.fixed) ? b.fixed.slice(0, 50).map((f) => ({
    name: text(f && f.name, 60) || "Post",
    type: f && f.type === "Indtægt" ? "Indtægt" : "Udgift",
    amount: num(f && f.amount, { min: 0, optional: false }, "beløb"),
  })) : [];
  const categories = Array.isArray(b.categories) ? b.categories.map((c) => text(c, 40)).filter(Boolean).slice(0, 20) : [];
  if (!categories.length) throw new HttpError(400, "Angiv mindst én variabel udgiftstype");
  return {
    avg_fee: num(b.avg_fee, { min: 0, max: 10000, optional: false }, "kontingent"),
    buffer_months: num(b.buffer_months, { min: 0, max: 24, optional: false }, "buffer"),
    growth: num(b.growth, { min: -1000, max: 1000, optional: false }, "tilgang"),
    opening_cash: num(b.opening_cash, { optional: false }, "kassebeholdning"),
    categories,
    fixed,
    sample: b.sample === true,
  };
}

function cleanWish(b, create) {
  const out = {};
  if (create || "item" in b) { out.item = text(b.item, 80); if (!out.item) throw new HttpError(400, "Mangler udstyr"); }
  if (create || "price" in b) out.price = num(b.price, { min: 0, optional: false }, "pris");
  if (create || "funding" in b) out.funding = b.funding === "fond" ? "fond" : "kasse";
  if (create || "priority" in b) out.priority = num(b.priority, { min: 0, max: 10000, int: true, optional: !create }, "prioritet") ?? 999;
  if (create || "bought" in b) out.bought = b.bought === true;
  if ("boughtAt" in b) out.boughtAt = text(b.boughtAt, 40);
  if (create) out.sample = false;
  return out;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
  });
}
