/*
 * Strong Gym holdplan-proxy ("middleman")
 * ----------------------------------------
 * Henter den OFFENTLIGE holdplan fra goMember-portalen og videresender den
 * til din egen hjemmeside med de CORS-headers browseren kræver.
 *
 * Ingen login. Ingen credentials. Læser kun data alle kan se i forvejen.
 *
 * Kald:  https://DIN-WORKER.workers.dev/?from=2026-06-01&to=2026-06-30
 *        (from/to er valgfrie — uden dem bruges indeværende måned)
 *
 * DOMÆNESKIFTET (se Stronggym.md): API'et findes kun på det domæne goMember
 * serverer. Når www.stronggym.dk bliver vores eget site, flytter API'et til
 * medlem.stronggym.dk. Derfor prøver worker'en adresserne i rækkefølge
 * nedenfor og bruger den første der svarer med rigtige holdplan-data.
 * Det gør skiftet ufarligt: den virker både før og efter, uden at nogen
 * behøver at ramme et tidsvindue.
 *
 * Når skiftet er helt gennemført, kan www-linjen slettes fra listen.
 */

// Prøves i denne rækkefølge. Første gyldige svar vinder.
const UPSTREAM_HOSTS = [
  "https://medlem.stronggym.dk", // portalen efter domæneskiftet
  "https://www.stronggym.dk",    // portalen i dag — slet linjen når skiftet er gennemført
];

const UPSTREAM_PATH = "/api/activity/event/days";

// Hvor længe vi venter på én adresse, før vi går videre til den næste.
const UPSTREAM_TIMEOUT_MS = 8000;

// Når en adresse har virket, husker vi den her og springer de øvrige over.
// Nulstilles af sig selv efter HOST_MEMO_MS, så skiftet fanges automatisk.
const HOST_MEMO_MS = 10 * 60 * 1000;
let memoHost = null;
let memoAt = 0;

// Lås evt. til kun din egen side senere, fx "https://www.stronggym.dk"
const ALLOW_ORIGIN = "*";

export default {
  async fetch(request) {
    // Browserens "må jeg?"-forespørgsel (preflight)
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "GET") {
      return json({ error: "Kun GET er tilladt" }, 405);
    }

    const url = new URL(request.url);

    // Datointerval: brug ?from / ?to hvis givet, ellers indeværende måned
    const { fromOffset, toTime } = resolveRange(
      url.searchParams.get("from"),
      url.searchParams.get("to")
    );

    const query =
      `?eventsToShow=300` +
      `&fromOffset=${encodeURIComponent(fromOffset)}` +
      `&toTime=${encodeURIComponent(toTime)}`;

    const result = await fetchFromAnyHost(query);

    if (!result.ok) {
      // Siden falder selv tilbage til sin faste ugeplan ved fejl.
      return json(
        { error: "Kunne ikke hente holdplan", forsøgt: result.attempts },
        502
      );
    }

    return json(result.data, 200, {
      // cache i browseren i 60 sek. så vi ikke spammer portalen
      "Cache-Control": "public, max-age=60",
      // til fejlfinding: hvilken adresse leverede data
      "X-Upstream-Host": result.host,
    });
  },
};

/**
 * Prøver adresserne i UPSTREAM_HOSTS indtil én leverer gyldige holdplan-data.
 * Returnerer { ok, data, host } eller { ok: false, attempts }.
 */
export async function fetchFromAnyHost(query, deps = {}) {
  const doFetch = deps.fetch || fetch;
  const now = deps.now ? deps.now() : Date.now();
  const hosts = deps.hosts || UPSTREAM_HOSTS;

  // Husket adresse først — ellers i opsat rækkefølge.
  const memoValid = memoHost && now - memoAt < HOST_MEMO_MS;
  const order = memoValid
    ? [memoHost, ...hosts.filter((h) => h !== memoHost)]
    : hosts.slice();

  const attempts = [];

  for (const host of order) {
    const target = host + UPSTREAM_PATH + query;
    try {
      const res = await doFetch(target, {
        headers: { Accept: "application/json" },
        // server-til-server kald — CORS gælder ikke her
        signal: timeoutSignal(UPSTREAM_TIMEOUT_MS),
      });

      if (!res.ok) {
        attempts.push({ host, resultat: "HTTP " + res.status });
        continue;
      }

      const data = await res.json().catch(() => null);

      // Vigtigt: et statisk site på samme adresse kan svare 200 med HTML
      // (SPA-fallback). Derfor er status 200 ikke nok — svaret skal have
      // den form siden faktisk bruger: et array af dage.
      if (!isSchedulePayload(data)) {
        attempts.push({ host, resultat: "svarede ikke med holdplan-data" });
        continue;
      }

      memoHost = host;
      memoAt = now;
      return { ok: true, data, host };
    } catch (err) {
      attempts.push({ host, resultat: String(err && err.message) || "fejl" });
    }
  }

  // Ingen adresse virkede — glem en evt. husket adresse, så næste kald
  // prøver hele listen forfra.
  memoHost = null;
  memoAt = 0;
  return { ok: false, attempts };
}

/**
 * Siden kræver et array af dage (`Array.isArray(data)` i index.html).
 * Et tomt array er gyldigt: en uge uden hold er et reelt svar.
 */
export function isSchedulePayload(data) {
  if (!Array.isArray(data)) return false;
  if (data.length === 0) return true;
  return data.every((d) => d && typeof d === "object" && !Array.isArray(d));
}

function timeoutSignal(ms) {
  // AbortSignal.timeout findes i Workers; faldgrube hvis ikke, så vi tjekker.
  if (typeof AbortSignal !== "undefined" && AbortSignal.timeout) {
    return AbortSignal.timeout(ms);
  }
  return undefined;
}

export function resolveRange(from, to) {
  const now = new Date();
  // Standard: første til sidste dag i indeværende måned (UTC)
  const start = from
    ? new Date(from + "T00:00:00.000Z")
    : new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = to
    ? new Date(to + "T23:59:59.999Z")
    : new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0, 23, 59, 59, 999));
  return { fromOffset: start.toISOString(), toTime: end.toISOString() };
}

export function _resetHostMemo() {
  memoHost = null;
  memoAt = 0;
}

function corsHeaders(extra = {}) {
  return {
    "Access-Control-Allow-Origin": ALLOW_ORIGIN,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    ...extra,
  };
}

function json(body, status = 200, extra = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...corsHeaders(extra) },
  });
}
