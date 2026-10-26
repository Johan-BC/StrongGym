# Bestyrelsessiden - økonomi og medlemmer

Lukket side for Strong Gyms bestyrelse på `/bestyrelse/`. Her registreres hver måned
aktive medlemmer, lønudgift fra Danløn og variable udgifter, og siden viser historik,
prognose for den fri kasse og ønskelisten til udstyr.

## Opbygning

| Del | Hvad |
|---|---|
| `public/bestyrelse/index.html` | Siden. Ren HTML/JS, samme design som hjemmesiden |
| `src/worker.js` | Cloudflare Worker: serverer siden og API'et under `/bestyrelse/api/` |
| `schema.sql` | Tabeller i Cloudflare D1 (måneder, ønskeliste, indstillinger, audit-log) |
| `seed-eksempel.sql` | Eksempeldata - ikke rigtige tal. Kan slettes med knappen på siden |
| `wrangler.toml` | Opsætning af worker, database og adgang |

Adgang sker i to lag:

1. **Cloudflare Access** ligger foran `/bestyrelse/*`. Man logger ind med en engangskode
   sendt til sin e-mail - ingen kodeord at administrere.
2. **Worker'en** verificerer selv Access-tokenet og tjekker e-mailen mod `BOARD_EMAILS`
   (kan registrere) og `VIEW_EMAILS` (kan kun se). Mangler opsætningen, afviser den alt.

Hver ændring skrives i tabellen `audit` med e-mail og tidspunkt.

## Opsætning (én gang)

Kræver en Cloudflare-konto (den samme som holdplan-worker'en) og Node.js.

```bash
cd bestyrelse
npm i -g wrangler          # eller brug npx wrangler ...
wrangler login

# 1. Database
wrangler d1 create stronggym-bestyrelse
#    -> kopiér database_id ind i wrangler.toml
wrangler d1 execute stronggym-bestyrelse --remote --file=schema.sql
wrangler d1 execute stronggym-bestyrelse --remote --file=seed-eksempel.sql   # valgfrit

# 2. Hvem har adgang (secrets, så e-mails ikke ligger i det offentlige repo)
wrangler secret put BOARD_EMAILS     # fx formand@...,kasserer@...
wrangler secret put VIEW_EMAILS      # kan være tom

# 3. Deploy
wrangler deploy
```

### Cloudflare Access

1. Cloudflare-dashboard > **Zero Trust** (gratis op til 50 brugere). Vælg et team-navn,
   fx `stronggym` -> team-domæne `https://stronggym.cloudflareaccess.com`.
2. **Access > Applications > Add an application > Self-hosted**.
   - Domæne: der hvor siden ligger (se nedenfor), sti `bestyrelse`.
   - Policy: *Allow*, *Emails* = bestyrelsens e-mails. Login-metode: *One-time PIN*.
3. Kopiér **Application Audience (AUD) Tag** fra appens oversigt.
4. Sæt `ACCESS_TEAM_DOMAIN` og `ACCESS_AUD` i `wrangler.toml` og kør `wrangler deploy` igen.

Ændres bestyrelsen, opdateres både Access-policyen og `BOARD_EMAILS`.

### Hvor siden ligger

- **På stronggym.dk/bestyrelse** (anbefalet): kræver at domænet bruger Cloudflare DNS.
  Fjern kommentaren ved `routes` i `wrangler.toml`. Linket i hjemmesidens footer peger på
  `/bestyrelse/` og virker så uden ændringer.
- **Indtil da på workers.dev**: `https://stronggym-bestyrelse.<konto>.workers.dev/bestyrelse/`.
  Slå *Cloudflare Access* til for workers.dev under worker'ens *Settings > Domains & Routes*,
  og ret footer-linket i `index.html` til den fulde adresse.

## Lokal udvikling

```bash
cp .dev.vars.example .dev.vars
echo 'BOARD_EMAILS=din@mail.dk' >> .dev.vars
wrangler d1 execute stronggym-bestyrelse --local --file=schema.sql
wrangler d1 execute stronggym-bestyrelse --local --file=seed-eksempel.sql
wrangler dev
# åbn http://localhost:8787/bestyrelse/
```

`DEV_MODE` springer login over, men kun når siden kaldes på localhost.

## Danløn

Feltet *Samlet lønudgift* er foreningens samlede omkostning (bruttoløn plus ATP og
feriepenge). Importen læser en CSV- eller Excel-eksport, gætter kolonnen med beløb og timer,
springer "I alt"-rækker over og lægger sammen. Filen bliver ikke gemt - kun totalen.
Importen er ikke testet mod en rigtig Danløn-eksport endnu.

## Regler

- Læg aldrig rigtige økonomital, lønsedler eller bestyrelsens e-mails i repoet - det er offentligt.
- Siden må ikke få adgang uden om Cloudflare Access. Fjern ikke tjekket af `Cf-Access-Jwt-Assertion`.
