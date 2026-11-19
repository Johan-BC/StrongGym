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

## Udvidelse af scopet: styringssiden (14. november 2026)

Scopet ovenfor gælder MCP-serveren. Til styringssiden (`styring.html`) har
klubben (Johan) bevidst åbnet for mere læsning, altid via
`GoMemberClient.get()` og altid kun som antal:

- `gomember-mcp/kortlaegning/opdater.py` er den ene kommando, der opdaterer
  sidens data. Den kører hver nat som en planlagt opgave.
- Udmeldte medlemmer slettes ikke i goMember; de står som "ikke aktive"
  (bekræftet af klubben 19. november 2026: 25 udmeldte).
- Medlemslisten (`/api/members`) læses tre gange: alle (kun `createdTs`, til
  nye pr. måned), aktive (`filter.isActive=true`: etiketter, til medlemstal pr.
  medlemskab) og ikke aktive (`filter.isActive=false`: kun `entityId`, til
  opslag af udmeldingsdato). Aktive + ikke aktive skal give hele listen.
- `GET /api/memberdata/{id}` kaldes én gang pr. ikke aktivt medlem og pr.
  aktivt medlem med etiketten "Ønsker udmelding" - kun for felterne `LeftDate`
  (udmeldingsdato) og `JoinedDate`
  (indmeldingsdato). Svaret er medlemmets fulde stamkort; alt andet kasseres
  straks. Intet id, ingen præcis dato og intet andet fra svaret må printes,
  logges eller gemmes - kun antal pr. måned og grove grupper.
- Bookinglister pr. hold læses for at tælle tilmeldte og fremmødte.

- Testkonti og læse-kontoen tælles aldrig med i medlemstal. Læse-kontoen
  kendes på sit id (`GET /api/members/me`). Testkonti kendes på ordet "test"
  i navnet (klubbens valg, 19. november 2026). Det er den ENESTE undtagelse
  fra reglen om aldrig at læse navne: navnet bruges kun inde i
  `er_testkonto()` i `byg_medlemsstatistik.py` til et ja/nej og gemmes,
  printes eller logges aldrig. Kun antallet af udelukkede gemmes.
- "Aktive medlemmer" på Overblik er beregnet ud fra betalende medlemskaber
  (summen af medlemskabs-etiketterne blandt aktive). Månederne bagud er
  genskabt; fra 19. november 2026 gemmes det faktiske tal hver nat i
  `styring-medlemmer.json` (`maalinger`).

Regel: der må aldrig vises, gemmes eller printes oplysninger om enkelte
medlemmer - heller ikke i fejlbeskeder eller under fejlsøgning. Grupper på
1-2 personer vises som "<3", undtagen udmeldinger pr. måned, som klubben har
godkendt med præcise antal.

## Status

**Login virker (bekræftet 14. november 2026).** `/auth/token` kræver, ud
over `grant_type=password&username=...&password=...`, en fast klient-kode i
`Authorization: Basic ...` - den samme som goMembers egen login-boks bruger
(fundet i deres offentlige main.js). Uden den svarer serveren HTTP 500, også
på forkerte logins. Klubben (Johan) har godkendt at vi bruger koden. Den står
i `WEB_CLIENT_BASIC` i `gomember_client.py` og kan overstyres med
`GOMEMBER_CLIENT_BASIC`. Login-oplysningerne ligger som miljøvariabler i
cloud-miljøet "stronggym", ikke i en `.env` i repoet.

**Det fiktive medlem er IKKE skrivebeskyttet i goMember.** `/api/members/me`
viser `adminRoles: activity, booking, createEvent, tagsAndTeams, partAdmin`
- administrator af hold, bookinger og etiketter, præcis som frygtet ovenfor.
Det kan også læse hele medlemslisten (navne, medlemsnummer, etiketter).
Koden er derfor stadig det eneste værn mod skrivning. Brugerens rettigheder
bør skæres ned i goMember (Site indstillinger > Rettigheder).

**Stadig ikke testet:** om goMember afviser skrivekald fra brugeren. Med de
roller ovenfor må man gå ud fra, at det IKKE gør.

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

## Sådan skal Claude forklare ting til Johan

Forklar i almindeligt sprog, ikke teknisk. Sig hvad der sker, hvorfor, og
hvad Johan skal tage stilling til. Undgå fagord som proxy, miljø, branch,
endpoint osv. - eller forklar dem kort, hvis de ikke kan undgås. Bed aldrig
om godkendelse af noget, uden først at have forklaret hvad det betyder.
