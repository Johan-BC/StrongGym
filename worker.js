/*
 * Strong Gym holdplan-proxy ("middleman")
 * ----------------------------------------
 * Henter den OFFENTLIGE holdplan fra stronggym.dk og videresender den
 * til din egen hjemmeside med de CORS-headers browseren kr�ver.
 *
 * Ingen login. Ingen credentials. L�ser kun data alle kan se i forvejen.
 *
 * Kald:  https://DIN-WORKER.workers.dev/?from=2026-06-01&to=2026-06-30
 *        (from/to er valgfrie � uden dem bruges indev�rende m�ned)
 */

const UPSTREAM = "https://www.stronggym.dk/api/activity/event/days";

// L�s evt. til kun din egen side senere, fx "https://stronggym-din-side.dk"
const ALLOW_ORIGIN = "*";

export default {
  async fetch(request) {
    // Browserens "m� jeg?"-foresp�rgsel (preflight)
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }
    if (request.method !== "GET") {
      return json({ error: "Kun GET er tilladt" }, 405);
    }

    const url = new URL(request.url);

    // Datointerval: brug ?from / ?to hvis givet, ellers indev�rende m�ned
    const { fromOffset, toTime } = resolveRange(
      url.searchParams.get("from"),
      url.searchParams.get("to")
    );

    const upstreamUrl =
      `${UPSTREAM}?eventsToShow=300` +
      `&fromOffset=${encodeURIComponent(fromOffset)}` +
      `&toTime=${encodeURIComponent(toTime)}`;

    try {
      const res = await fetch(upstreamUrl, {
        headers: { "Accept": "application/json" },
        // server-til-server kald � CORS g�lder ikke her
      });

      if (!res.ok) {
        return json({ error: "Upstream svarede " + res.status }, 502);
      }

      const data = await res.json();
      return json(data, 200, {
        // cache i browseren i 60 sek. s� vi ikke spammer stronggym.dk
        "Cache-Control": "public, max-age=60",
      });
    } catch (err) {
      return json({ error: "Kunne ikke hente holdplan", detail: String(err) }, 502);
    }
  },
};

function resolveRange(from, to) {
  const now = new Date();
  // Standard: f�rste til sidste dag i indev�rende m�ned (UTC)
  const start = from
    ? new Date(from + "T00:00:00.000Z")
    : new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const end = to
    ? new Date(to + "T23:59:59.999Z")
    : new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 0, 23, 59, 59, 999));
  return { fromOffset: start.toISOString(), toTime: end.toISOString() };
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
