# Strong Gym – Setup / Infrastruktur

## Middleman (proxy til holdplan-data)

Hjemmesidens holdplan henter **live data** fra stronggym.dk's offentlige
kalender-API. Browseren kan ikke kalde det API direkte (CORS – stronggym.dk
sender ikke de nødvendige headers), så vi bruger en lille mellem-service
("middleman") der henter data server-til-server og videresender det til siden
med korrekte CORS-headers.

- **Provider:** Cloudflare Workers (gratis tier)
- **URL:** https://stronggym.jbchristophersen.workers.dev/
- **Kildekode:** [`worker.js`](worker.js) i dette projekt
- **Login/credentials:** Ingen. Data er offentligt tilgængeligt (synligt for
  ikke-indloggede besøgende), så middleman'en bruger hverken login eller nøgler.

### Sådan kaldes den
```
https://stronggym.jbchristophersen.workers.dev/?from=2026-06-01&to=2026-06-30
```
- `from` / `to` er valgfrie (format `YYYY-MM-DD`). Uden dem bruges
  indeværende måned.
- Returnerer JSON: array af `{ date, slots: [...] }`, hvor hver slot er en
  holdinstans med bl.a. `name`, `startTime`, `endTime`, `maxAttendees`,
  `booked`, `waitingList`, `status`, `responsible[].displayName` (coach).

### Bagvedliggende API (upstream)
```
<portal-adresse>/api/activity/event/days?eventsToShow=300&fromOffset=<ISO>&toTime=<ISO>
```

API'et findes kun på det domæne goMember serverer. Derfor har worker'en en
**liste** af adresser i `UPSTREAM_HOSTS` ([`worker.js`](worker.js)) og bruger
den første der svarer med rigtige holdplan-data:

1. `https://medlem.stronggym.dk` — portalen efter domæneskiftet
2. `https://www.stronggym.dk` — portalen i dag

Det gør domæneskiftet ufarligt: samme worker virker både før og efter, uden
et tidsvindue der skal rammes. Når skiftet er gennemført, kan www-linjen
slettes fra listen. Se afsnittet om domæneskiftet i
[`Stronggym.md`](Stronggym.md).

Et svar tæller kun som gyldigt, hvis det er et **array af dage** — ikke blot
HTTP 200. Det er med vilje: når `www.stronggym.dk` bliver vores eget statiske
site, vil `/api/...` på den adresse sandsynligvis svare 200 med HTML, og en
rå status-tjek ville tro at det var data.

Svaret bærer headeren `X-Upstream-Host` med den adresse der leverede data —
brug den til at se hvad worker'en faktisk henter fra:

```
curl -sI "https://stronggym.jbchristophersen.workers.dev/?from=2026-11-10&to=2026-11-16" | findstr /i upstream
```

Fejler alle adresser, svarer worker'en 502 med en liste over hvad der blev
forsøgt, og siden falder selv tilbage til sin faste ugeplan.

### Vedligehold / noter
- Hvis Cloudflare-kontoen eller worker'en fjernes, holder holdplanen op med at
  vise live data.
- Hvis stronggym.dk (Memberlink) ændrer deres API-format, skal `worker.js`
  og/eller render-koden i siden opdateres.
- Worker'en husker den adresse der sidst virkede i 10 minutter (`HOST_MEMO_MS`)
  og prøver hele listen forfra derefter. Et domæneskifte bliver altså fanget
  af sig selv senest 10 minutter efter, uden deploy.
- CORS er sat til `*` (alle origins). Kan låses til kun sidens eget domæne ved
  at ændre `ALLOW_ORIGIN` i [`worker.js`](worker.js) og re-deploye.
