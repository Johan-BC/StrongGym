# goMember read-only integration - kontekst til Claude Code

Dette er en MCP-server der giver læse-adgang til goMember/MemberLink API'et
(Strong Gyms medlemssystem), til brug i strong-gym.dk-hjemmesiden - primært
for at hente hold- og aktivitetsoversigter til visning på sitet.

## Baggrund og beslutninger

goMember har ingen indbygget skrivebeskyttet API-nøgle. Support anbefalede
selv løsningen: opret et fiktivt medlem i goMember, giv det kun de
rettigheder du ønsker via Site indstillinger > Rettigheder, og brug det
medlems login i integrationen.

Den løsning er ikke nok alene. goMembers rettighedssystem er feltgranulært
for medlemslister, men for Hold/Aktiviteter er rollerne binære
("administrator" af området, ikke "kan se men ikke ændre") - jf. deres egen
dokumentation af træneradgang, som eksplicit giver redigeringsret sammen med
visningsret. Der er ingen bekræftelse i deres dokumentation af at skrivekald
rent faktisk bliver afvist server-side for en sådan konto.

Derfor er den egentlige garanti for read-only lagt i koden, ikke i
goMember-kontoen:

- `gomember_client.py` implementerer udelukkende `get()`. Ingen
  `post()`/`put()`/`patch()`/`delete()`-metode findes i klassen.
- `server.py` er auto-genereret af `generate.py`, som kun læser
  GET-operationer fra swagger-filen (`SGSwagger.json`) - POST/PUT/PATCH/DELETE
  bliver aldrig parset, uanset scope.
- `DENIED_PATHS` i `generate.py` holder fire GET-paths ude, fordi GET-verbet
  ikke i sig selv betyder at kaldet er uden sideeffekter. De fire er
  `/api/activitydata/batchupdate/{id}`, `/api/activitydata/clone/{id}`,
  `/api/tagcategorydata/clone/{id}` og `/api/tagdata/clone/{id}` - alle
  defineret som GET i swagger, men navngivet som om de opretter eller ændrer
  data. Ingen af dem er nødvendige for at vise holdplaner på sitet.
- Det fiktive goMembers-medlems rettigheder er andet forsvarslag, ikke det
  primære.

**Regel for videre arbejde i dette projekt: tilføj aldrig en skrivemetode i
`gomember_client.py`, og lav aldrig et rå HTTP-kald mod goMember uden om den
klasse.** Hvis en fremtidig opgave kræver at skrive til goMember (opdatere
medlemsdata, oprette bookinger osv.), er det en bevidst, separat beslutning -
ikke noget der skal snige sig ind som en bekvem udvidelse af denne klient.

## Scope

49 GET-værktøjer, afgrænset til disse swagger-tags: ActivityApi,
ActivityDataApi, ActivityEventDataApi, EventApi, EventNewApi, BookingApi,
TagApi, TagDataApi, TagCategoryDataApi ("Tag" = hold/etikette i goMembers
datamodel).

Bevidst udeladt: medlemslister/-data, økonomi/bank/fakturaer, døradgang,
betalinger og alt andet af de i alt 841 endpoints i swagger-filen. Det var et
aktivt valg for at holde angrebsfladen minimal, ikke en begrænsning i
swagger-filen.

Hvis scopet skal udvides: rediger `SCOPED_TAGS` og `NAME_MAP` i `generate.py`,
kør `python3 generate.py SGSwagger.json` igen. Overvej hver udvidelse for sig
- se ovenstående regel om at det er et sikkerhedsvalg, ikke bare en
teknikalitet. Vurder samtidig om et nyt endpoint hører hjemme i
`DENIED_PATHS`: et GET-kald der hedder noget med clone/update/create/assign
skal holdes ude, indtil nogen har bekræftet mod den faktiske server hvad det
gør.

## Status - hvad er IKKE testet endnu

- `check_auth.py` er ikke kørt mod produktion endnu. Autentificeringsformen
  (OAuth2 Resource Owner Password, POST til `/auth/token`) er antaget ud fra
  swagger-filens `securityDefinitions`, men selve request-body'en
  (`grant_type=password&username=...&password=...`, evt. `client_id`) er ikke
  bekræftet mod den faktiske server.
- Om goMember rent faktisk afviser skrivekald fra det fiktive medlems login
  er ikke testet og kan ikke testes af denne kodebase, fordi den aldrig
  foretager et skrivekald. Det er stadig en åben antagelse.
- `.env` er ikke udfyldt endnu - login til det fiktive medlem mangler.

## Filer

| Fil | Formål |
|---|---|
| `SGSwagger.json` | Swagger-specifikationen for hele goMember/MemberLink API'et |
| `generate.py` | Genererer `server.py` ud fra swagger-filen - eneste sted scope ændres |
| `gomember_client.py` | HTTP/auth-klient - kun `get()` findes, med vilje |
| `server.py` | Auto-genereret MCP-server (rediger ikke direkte) |
| `check_auth.py` | Selvstændig test af login + ét GET-kald, kør før Claude Code-opsætning |
| `.env.example` | Skabelon til credentials (kopiér til `.env`, som ikke må committes) |
| `README.md` | Opsætningstrin (venv, Claude Code-registrering) |

## Bestyrelsessiden (`bestyrelse/`)

Lukket økonomiside for bestyrelsen på `/bestyrelse/`: Cloudflare Worker + D1-database
med Cloudflare Access foran. Se `bestyrelse/README.md` for opsætning.

- Hjemmesidens tidligere mock-"Dashboard" er fjernet; footeren linker til `/bestyrelse/`.
- Adgang tjekkes to steder: Access-policy og `BOARD_EMAILS`/`VIEW_EMAILS` i worker'en,
  som selv verificerer Access-tokenet. Fjern aldrig det tjek, og lad `DEV_MODE` kun
  virke på localhost.
- Repoet er offentligt: ingen rigtige økonomital, lønsedler eller e-mails i filer.
  Bestyrelsens e-mails sættes som wrangler-secrets.
- Siden henter ikke data fra goMember. Medlemstal tastes ind; at hente dem fra
  goMember ville kræve medlemsdata, som bevidst er uden for MCP-serverens scope.
