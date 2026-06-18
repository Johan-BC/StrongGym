# Strong Gym – Setup / Infrastruktur

## Middleman (proxy til holdplan-data)

Hjemmesidens holdplan henter **live data** fra stronggym.dk's offentlige
kalender-API. Browseren kan ikke kalde det API direkte (CORS – stronggym.dk
sender ikke de n�dvendige headers), s� vi bruger en lille mellem-service
("middleman") der henter data server-til-server og videresender det til siden
med korrekte CORS-headers.

- **Provider:** Cloudflare Workers (gratis tier)
- **URL:** https://stronggym.jbchristophersen.workers.dev/
- **Kildekode:** [`worker.js`](worker.js) i dette projekt
- **Login/credentials:** Ingen. Data er offentligt tilg�ngeligt (synligt for
  ikke-indloggede bes�gende), s� middleman'en bruger hverken login eller n�gler.

### Sådan kaldes den
```
https://stronggym.jbchristophersen.workers.dev/?from=2026-06-01&to=2026-06-30
```
- `from` / `to` er valgfrie (format `YYYY-MM-DD`). Uden dem bruges
  indev�rende m�ned.
- Returnerer JSON: array af `{ date, slots: [...] }`, hvor hver slot er en
  holdinstans med bl.a. `name`, `startTime`, `endTime`, `maxAttendees`,
  `booked`, `waitingList`, `status`, `responsible[].displayName` (coach).

### Bagvedliggende API (upstream)
```
https://www.stronggym.dk/api/activity/event/days?eventsToShow=300&fromOffset=<ISO>&toTime=<ISO>
```

### Vedligehold / noter
- Hvis Cloudflare-kontoen eller worker'en fjernes, holder holdplanen op med at
  vise live data.
- Hvis stronggym.dk (Memberlink) �ndrer deres API-format, skal `worker.js`
  og/eller render-koden i siden opdateres.
- CORS er sat til `*` (alle origins). Kan l�ses til kun sidens eget domæne ved
  at �ndre `ALLOW_ORIGIN` i [`worker.js`](worker.js) og re-deploye.
