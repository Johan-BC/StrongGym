# Strong Gym Helsingør — Projekt Noter

## Projektoversigt
Single-file HTML-website for Strong Gym Helsingør (CrossFit-center). Bygget som en eksakt kopi af et Lovable.dev-projekt, derefter videreudviklet med rigtig holdplan-data fra stronggym.dk.

**Output-fil:** `/mnt/user-data/outputs/stronggym.html`
**Sprog:** Dansk
**Arkitektur:** Ren HTML/CSS/vanilla JS i én fil — ingen build-step, ingen frameworks. Client-side routing via JS (ingen rigtig URL-routing, kun en `currentPage`-state der styrer hvad `#app` viser).

---

## Baggrund / kilde
- Oprindelig anmodning: lav en hjemmeside baseret på farver/logo fra stronggym.dk, med nyt look.
- Derefter: kopiér et eksisterende Lovable-projekt 1:1 (`stronggymbeta.lovable.app`).
- Lovable-kildefiler modtaget som upload: `plan.md`, `App.tsx`, `Index.tsx`, `Contact.tsx`, `News.tsx`, `Schedule.tsx`, `Signup.tsx`, `Coaches.tsx`, `App.css`.
- Disse var React/TSX-komponenter (shadcn/ui, framer-motion, react-router) — konverteret til vanilla JS-ækvivalent i én HTML-fil, da det er enklere at distribuere og redigere uden build-toolchain.

---

## Design-system
- **Baggrund:** `#111111` (primær), `#1a1a1a` (sekundær/cards-baggrund)
- **Card-baggrund:** `#1f1f1f`
- **Border:** `#2a2a2a` / `#333`
- **Tekst:** `#f0ede8` (primær), `#888` (muted)
- **Accentfarve (primary/gold):** `#D4A843`, hover `#e8bc55`
- **Statusfarver:** rød `#ef4444`, blå `#60a5fa`, grøn `#4ade80`, lilla `#c084fc`
- **Typografi:** 'Bebas Neue' til alle headings/knapper (uppercase, bred letter-spacing), 'DM Sans' (300/400/500) til brødtekst
- **Logo:** hentes fra `https://cdn-02.memberlink.dk/azure/sitesite2518137197226848565/FormFile/logo sort.jpeg` — med `onerror`-fallback til tekst "STRONG GYM" i guld, hvis billedet ikke loader

---

## Sidestruktur (7 sider, vist via JS-routing)
1. **Forside (index)** — Hero m. logo + tagline "Her løfter vi ikke kun vægte, men også hinanden", CrossFit-forklaring, kommende WODs (3 stk.), galleri-placeholders (8 stk.), nyheder-preview (2 stk.)
2. **Log Ind (login)** — Mock login (email + password, ingen rigtig backend). Sætter `isLoggedIn = true` og giver adgang til tilmelding på holdplan.
3. **Trænere (coaches)** — Grid med 6 trænere (navn, speciale, bio)
4. **Nyheder (news)** — 4 nyhedsartikler + social media sidebar (Facebook/Instagram links)
5. **Bliv Medlem (signup)** — Valg af medlemskabstype + formular (navn, email, telefon) → success-state efter submit
6. **Kontakt (contact)** — Kontaktformular + telefon/email/adresse + åbningstider + map-placeholder
7. **Holdplan (schedule)** — Se separat sektion nedenfor; dette er den mest komplekse side

---

## Holdplan — vigtig beslutningshistorik

### Iteration 1 (forkastet tilgang)
Først genereret med **tilfældige mock-data** (`generateWorkouts()`) for marts 2026 — tilfældig type, tid, træner, ledige pladser pr. dag. Dette var IKKE retvisende for den rigtige holdplan og blev senere udskiftet.

### Iteration 2 (skærmbillede-baseret, nu erstattet)
Brugeren delte det rigtige holdplan-link: `https://www.stronggym.dk/Activity/ActivityView`. Denne side er beskyttet af robots.txt (kan ikke web_fetch'es), så data blev indsamlet via **Claude i Chrome-browserudvidelsen** (skærmbilleder af den rigtige kalendervisning på stronggym.dk, maj 2026) og hardcodet som et fast ugentligt mønster i `holdplan`-arrayet.

### Iteration 3 (nuværende, korrekt tilgang — LIVE DATA)
Holdplanen henter nu **live data** fra stronggym.dk's offentlige kalender-API via en middleman/proxy. Detaljer om infrastrukturen står i [`setup.md`](setup.md).

- **API (upstream):** `https://www.stronggym.dk/api/activity/event/days?eventsToShow=300&fromOffset=<ISO>&toTime=<ISO>` — offentligt tilgængeligt (synligt for ikke-indloggede), så ingen credentials.
- **Middleman:** Cloudflare Worker (`https://stronggym.jbchristophersen.workers.dev/`), kildekode i [`worker.js`](worker.js). Nødvendig fordi browseren ikke kan kalde API'et direkte (CORS — stronggym.dk sender ikke `Access-Control-Allow-Origin`). Worker'en henter server-til-server og videresender med korrekte CORS-headers.
- **Funktioner i koden:** `ensureWeek(days)` henter en uges data, `liveCache` (per-dato), `mapSlot()` mapper API-felter til kort, `classifyType(name)` udleder holdtype fra navnet, `classesForDate(date)` returnerer live-data hvis hentet ellers fallback.
- **Fallback:** Det hardcodede `holdplan`-array (tabellen herunder) bruges nu KUN som fallback mens data hentes, eller hvis worker'en er utilgængelig (status-linje viser da "Kunne ikke hente live-data – viser standardplan").
- **Forsiden** ("Kommende WODs") bruger samme live-data via `getUpcomingLive(n)` / `ensureUpcoming()` — viser de næste reelle hold (springer afsluttede, aflyste og rengøring over) med rigtig coach og booket/max. Falder tilbage til mock (`generateWorkouts`) hvis intet er hentet.
- **Status-værdier fra API:** `scheduled` (normal), `booked` (fyldt — IKKE aflyst), `cancelled` (= "Aflyst"). Kun `cancelled` markeres som aflyst.
- **Visning:** booket/max (fx "9/12"). Fyldt hold (booket ≥ max) vises rødt + "Venteliste"-badge (med antal hvis kendt). Begivenheder uden kapacitet (`maxAttendees = 0`, fx POP UP WOD) vises som "X tilmeldt".

### Den faste ugeplan (FALLBACK — hardcoded i `holdplan`-arrayet)
> Bruges kun når live-data ikke kan hentes. Den rigtige plan kommer nu fra API'et.
| Dag | Hold | Tid | Pladser | Type |
|---|---|---|---|---|
| Mandag | Members WOD – uden coach | 06:00–07:00 | 12 | members |
| Mandag | WOD | 08:15–09:15 | 12 | wod |
| Mandag | WOD Mandag 1600 | 16:00–17:00 | 12 | wod |
| Mandag | WOD Mandag 1700 | 17:00–18:00 | 12 | wod |
| Mandag | WOD Mandag 1945 | 19:45–20:45 | 12 | wod |
| Tirsdag | MIKKOS – uden træner | 08:15–09:15 | 12 | mikkos |
| Tirsdag | WOD | 16:30–17:30 | 12 | wod |
| Tirsdag | Tons | 17:45–18:45 | 12 | tons |
| Tirsdag | WOD | 19:00–20:00 | 12 | wod |
| Onsdag | WOD | 06:00–07:00 | 12 | wod |
| Onsdag | WOD | 08:15–09:15 | 12 | wod |
| Onsdag | WOD Onsdag 1600 | 16:00–17:00 | 12 | wod |
| Onsdag | HYROX | 17:00–18:00 | 16 | hyrox |
| Onsdag | Rengøring – begrænset t. | 18:30–21:00 | 12 | rengoring |
| Torsdag | MEMBERS WOD – uden coach | 08:15–09:15 | 12 | members |
| Torsdag | Ungeenheden Helsingør | 09:30–11:00 | 12 | unge |
| Torsdag | WOD Torsdag 1630 | 16:30–17:30 | 18 | wod |
| Torsdag | Basis/teknik hold | 18:00–19:00 | 8 | basis |
| Fredag | WOD | 08:15–09:15 | 12 | wod |
| Fredag | WOD | 15:30–16:30 | 12 | wod |
| Fredag | MASH – lidt mere udfordrende | 16:30–18:00 | 12 | mash |
| Lørdag | WOD | 08:00–09:00 | 16 | wod |
| Lørdag | WOD | 09:00–10:00 | 16 | wod |
| Søndag | WOD | 08:00–09:00 | 16 | wod |
| Søndag | WOD (Laaang workout) | 09:00–10:30 | 16 | wod |
| Søndag | Børne hold 5–12 år | 10:45–11:45 | 20 | boern |
| Søndag | Rengøring – begrænset t. | 13:00–15:30 | 12 | rengoring |

### Holdplan-UI/UX-beslutninger
- Skiftet fra dato-for-dato-liste (marts 2026, statisk) til **uge-grid-visning** (7 kolonner: Man–Søn), der matcher den rigtige sides struktur tættere
- Tilføjet **uge-navigation** (← / → knapper) der beregner mandag-baseret uge ud fra dags dato + offset, så man kan bladre frem/tilbage i tid — ikke bundet til marts 2026 længere
- "Gå til denne uge"-knap vises når man har navigeret væk fra den aktuelle uge
- Dags dato highlightes med guld border i kolonne-headeren
- **Farvekodning** pr. holdtype (inspireret af stronggym.dk's eget board): hvert kort har tonet baggrund + farvet venstre kant + farvet tid-tekst. **grøn=WOD/Members** (ændret fra guld for at matche det rigtige board), blå=HYROX, grå=MASH, pink=Børnehold, orange/amber=Basis/MIKKOS, lilla=Tons/Unge, rød=Rengøring + legend øverst på siden. Implementeret med CSS `color-mix()` og en `--tc`-variabel pr. `.type-*` (virker i moderne browsere; falder tilbage til ren mørk card-baggrund i ældre)
- Guld (`--primary`) er stadig brandfarven på resten af siden; kun holdkortene bruger nu grøn til WOD
- Tilmeld-knap vises kun når `isLoggedIn === true` (samme login-gate som hele siden havde fra start). Knappen siger "Skriv på venteliste" på fyldte hold
- Hvert hold får et unikt instance-ID (`holdId_dato`) så tilmelding er specifik per ugedag-instans, ikke kun per holdtype
- Lille status-indikator under uge-navigationen: grøn prik "Live booking-tal fra stronggym.dk", pulserende ved load, rød ved fejl

---

## Kendte bugs og hvordan de blev løst

### Bug 1: Medlemskabstyper sort/usynlig tekst
**Problem:** Teksten i medlemskabs-knapperne på "Bliv Medlem"-siden var sort og svær at se mod den mørke baggrund.
**Årsag:** Browseres default `color: ButtonText` (sort) på `<button>`-elementer overskriver CSS-variabler, hvis ikke explicit sat.
**Løsning:** Tilføjet `color: var(--fg) !important` på `.membership-type`, `.membership-type h3`, samt `!important` på `.price` og `.desc` for at tvinge de korrekte farver igennem.

### Bug 2: "navigate is not defined" — hele siden virkede ikke
**Problem:** Filen blev afbrudt midt i generering (file-creation blev truncated), så `</script>`, `</body>`, `</html>` samt sidste del af JS-koden (inkl. `navigate`, `render`, `renderIndex`, `doLogin` m.fl.) manglede helt eller delvist.
**Løsning:** Hele filen blev genskrevet fra bunden i ét samlet script for at garantere komplet, syntaktisk korrekt output. Verificeret efterfølgende med `node --check` på det udtrukne JS for at sikre ingen syntaksfejl.

---

## Tekniske detaljer / konventioner brugt i koden
- State holdes i globale JS-variabler: `currentPage`, `isLoggedIn`, `signedUpIds` (Set), `pendingWId`, `weekOffset`, `selectedMembership`, `signupSubmitted`
- `render()` skifter indhold i `#app` baseret på `currentPage` via et objekt-lookup af render-funktioner (`renderIndex`, `renderLogin`, osv.)
- Toast-notifikationer via simpel `toast(title, desc, type)`-funktion der injicerer og auto-fjerner DOM-elementer
- Bekræftelsesdialog (tilmelding til hold) er en generisk overlay (`#confirm-dialog`) der genbruges af holdplan-siden
- Ingen ægte backend — alt er mock/in-memory. Sider nulstilles ved refresh.

---

## Kontaktoplysninger brugt i indhold
- Telefon: +45 31 16 55 53
- Email: info@stronggym.dk
- Adresse: Industrivej 8, 3000 Helsingør (ny adresse, oplyst 10. november 2026)
- CVR: 45733467
- Facebook: facebook.com/stronggym3000
- Instagram: instagram.com/stronggym3000

## Åbningstider
| Dag | Tid |
|---|---|
| Mandag–Fredag | 06:00–21:00 |
| Lørdag | 08:00–16:00 |
| Søndag | 10:00–14:00 |
| Helligdage | 10:00–13:00 |

## Medlemskabstyper
| Type | Pris | Beskrivelse |
|---|---|---|
| Premium Medlem | 499 kr/md | Ubegrænset adgang til alle hold og faciliteter |
| Barn | 199 kr/md | For børn under 15 år. Inkluderer udvalgte hold |
| Ung (18–25 år) | 299 kr/md | Særlig ung-pris for studerende og unge |
| 10-turs Klippekort | 850 kr | Fleksibel adgang – brug det i dit eget tempo |

---

## Brugerpræferencer (relevant for fremtidigt arbejde i dette projekt)
- Foretrækker direkte kommunikation, ikke overdrevent poleret/høfligt sprog
- Vil gerne udfordres på beslutninger — interesseret i den bedste løsning, ikke nødvendigvis sin egen first idea

---

## Åbne punkter / mulige fremtidige forbedringer
- Holdplanen viser nu live-data (inkl. engangsbegivenheder og aflysninger) direkte fra API'et — den gamle begrænsning til det faste ugentlige mønster er løst. Det hardcodede array bruges kun som fallback.
- Galleri-sektionen på forsiden er stadig placeholder-ikoner (🏋️), ikke rigtige billeder.
- Selve tilmelding/login/signup er stadig mock (client-side state der nulstilles ved refresh) — KUN holdplan-/forside-visningen er live. Rigtig tilmelding ville kræve autentificeret skrive-adgang til Memberlink (bevidst undladt). Se **Opgave: Login og tilmelding** nedenfor.
- Middleman'en afhænger af at Cloudflare-worker'en kører og at Memberlinks API-format er uændret (se [`setup.md`](setup.md)).

---

## Opgave: Login og tilmelding — embed eller link til goMember

**Status:** ikke påbegyndt. Login og tilmelding er stadig mock — client-side
state der nulstilles ved refresh.

**Beslutningen er i princippet allerede truffet** i Phase 1 længere nede:
login, redigering af persondata og indmeldelse skal pege på goMembers eget
portal — via link eller embed — frem for at blive bygget om. To grunde
holder stadig:

1. At bygge det selv flytter ansvaret for passwords og persondata over på
   os, GDPR-forpligtelsen inklusive. goMember har allerede en fungerende og
   vedligeholdt løsning.
2. Rigtig tilmelding kræver autentificeret **skrive**-adgang til goMember.
   Hele projektet er bygget uden en eneste skrivevej: `gomember_client.py`
   har kun `get()`, og `generate.py` parser kun GET-operationer. At åbne en
   skrivevej fra en offentlig hjemmeside er en væsentligt større beslutning
   end denne opgave — den skal i givet fald tages for sig.

Det reelle valg er derfor **link kontra iframe**, ikke embed kontra rebuild.

### Undersøgt 21. oktober 2026 — resultat

**Framing er ikke blokeret.** Hverken `/`, `/Account/Login` eller
tilmeldingssiden sender `X-Frame-Options` eller `Content-Security-Policy`.
Iframe er altså teknisk muligt i dag.

Fundne URL'er:

- Tilmelding: `https://www.stronggym.dk/Account/Signup/Tag2517869245434174618`
- Login: `https://www.stronggym.dk/Account/Login`
- Medlemsadministration: `https://www.stronggym.dk/info/medlemsadministration`

**Men det vigtigste fund er et andet: www.stronggym.dk ER goMember-sitet.**
Det er ikke en gammel hjemmeside der henter data fra goMember — det er
goMembers egen hostede tenant. Beviserne:

- `X-AspNetMvc-Version: 5.3`, `X-Powered-By: ASP.NET`, Azure-`ARRAffinity`-cookies
- Aktiver fra `memberlinkcdn.blob.core.windows.net` og `gomember.com`
- En `memberlink-footer` og et goMember-POS-logo i markup'en

Det flytter det blokerende spørgsmål et niveau op.

### Det ægte blokerende spørgsmål: hvor skal det nye site bo?

`/Account/Login` og `/Account/Signup/...` findes kun, fordi goMember
serverer hele `www.stronggym.dk`. Overtager det nye statiske site det
domæne, forsvinder de to stier med det samme — og så er både link og
iframe brudt.

| Model | Konsekvens for login/tilmelding |
|---|---|
| Nyt site på `www.stronggym.dk`, goMember flyttet til subdomæne | Login/tilmelding bliver **cross-origin**. Third-party cookies i spil igen, og iframe bliver skrøbelig. Link er det robuste valg |
| Nyt site på subdomæne, goMember beholder `www` | Alt virker uden ændringer, men medlemmerne møder to forskellige sites |
| Nyt site erstatter dele af det nuværende | Ikke muligt — man kan ikke delvist erstatte en hostet ASP.NET-app |

Det spørgsmål skal afklares med goMember, ikke i kode. Og det skal afklares
**før** der bruges tid på login- og tilmeldingssiderne, fordi svaret
bestemmer hvilken af dem der overhovedet er mulig.

**Afklaret 10. november 2026 — model 1 er valgt.** Se afsnittet nedenfor.

En note til iframe-sporet uanset udfald: at framing virker i dag skyldes
at goMember **ikke** sætter en header. Det er deres valg, og det kan ændre
sig uden varsel. At bygge foreningens indmeldelsesflow oven på en manglende
sikkerhedsheader hos en leverandør er skrøbeligt, også når det virker.

### Afklaret med goMember 10. november 2026

goMember kan servere medlemsportalen på `medlem.stronggym.dk` med certifikat,
uden ekstra betaling. Model 1 i tabellen ovenfor er altså farbar, og det er
den vi går efter: nyt statisk site på `www.stronggym.dk`, goMember-portalen
på `medlem.stronggym.dk`.

Hvad de bekræftede:

- **Subdomæne og certifikat.** Vi opretter det selv under Site indstillinger →
  Domain adresser → "Opret ny domain adresse" → "Et domæne vi selv ejer".
  DNS-værdierne vises under "DNS ændring krævet"; adressen er klar når der
  står "Live og klar til brug". Certifikat er inkluderet, ingen ekstra pris.
- **Stierne følger med uændret.** `/Account/Login` bliver
  `medlem.stronggym.dk/Account/Login`, og det samme gælder
  `/Account/Signup/Tag2517869245434174618` og resten.
- **Mails og betaling klarer sig selv.** Links i de automatiske mails og
  retur-URL'en fra MobilePay/Vipps bruger den **primære** adresse. Når
  `medlem.stronggym.dk` er sat som primær, følger de med automatisk.
- **Redirects er vores opgave.** goMember laver dem ikke. Når www peger på
  vores site, rammer de gamle links og medlemmernes bogmærker os — ikke dem.

#### Rækkefølgen er kritisk

"Sæt som primær"-knappen vises kun når **alle** tenantens adresser står som
Live. Derfor:

1. Opret `medlem.stronggym.dk` hos goMember, indsæt DNS-værdierne hos
   domæneudbyderen, vent på "Live og klar til brug".
2. Sæt `medlem.stronggym.dk` som primær.
3. **Først nu** skiftes DNS for `www.stronggym.dk` og `stronggym.dk` til det
   nye site.
4. Skriv til goMember, så de fjerner `www.stronggym.dk` og `stronggym.dk` fra
   tenanten.

**Ret samtidig `PORTAL` i [`index.html`](index.html)** til
`https://medlem.stronggym.dk`. Den konstant styrer, hvor "Log ind" og
"Tilmeld i portalen" peger hen. Modsat worker'en kan siden ikke selv prøve
sig frem — et link skal virke på det første klik — så den skal rettes i hånden
ved trin 3.

Ændres www først, er den ikke længere Live hos goMember, og så kan medlem
ikke sættes som primær. Man sidder da fast med portalen på et domæne man
netop har peget væk — mails og MobilePay-returlinks peger ind i vores nye
site, hvor der ikke er nogen portal.

#### To ting goMember ikke nævnte, og som brækker sitet

**1. Holdplanens live-data dør ved trin 3.** `UPSTREAM` i
[`worker.js`](worker.js) peger på
`https://www.stronggym.dk/api/activity/event/days`. Det endpoint findes kun,
fordi goMember serverer www. Efter trin 3 svarer www vores eget statiske
site, og proxyen får intet brugbart tilbage — både holdplan-siden og
"Kommende WODs" på forsiden falder tilbage til det hardcodede fallback-array
med "Kunne ikke hente live-data".

**Løst 10. november 2026.** [`worker.js`](worker.js) har ikke længere én
hardkodet adresse, men en liste (`UPSTREAM_HOSTS`): `medlem.stronggym.dk`
først, `www.stronggym.dk` som fallback. Den bruger den første adresse der
svarer med et array af dage — ikke blot HTTP 200, fordi vores eget statiske
site sandsynligvis svarer 200 med HTML på `/api/...`. Den adresse der virkede,
huskes i 10 minutter, så skiftet fanges automatisk derefter.

Dermed er der ikke længere et tidsvindue der skal rammes: samme worker virker
før, under og efter skiftet. To ting at huske alligevel:

- **Deploy worker'en før trin 3.** Koden i repoet hjælper ikke, hvis det er den
  gamle version der kører på Cloudflare.
- **Slet www-linjen fra `UPSTREAM_HOSTS`, når trin 4 er gennemført.** Ellers
  bliver hvert kald, hvor medlem svarer dårligt, først forsøgt mod vores eget
  site — unods ventetid på noget der aldrig leverer holdplan-data.

Svaret bærer `X-Upstream-Host`, så man kan se hvilken adresse der leverede
data. Verificér med den efter trin 1 og igen efter trin 3. Logikken er testet
med stubbet fetch (17 cases: fallback, HTML-200 afvist, 503, tomt array,
hukommelse og udløb) og validatoren er prøvet mod det rigtige API-svar.

**2. Redirects fra de gamle stier.** Når www er vores, skal mindst disse
sendes videre til `medlem.stronggym.dk`:

| Gammel sti | Sendes til |
|---|---|
| `/Account/Login` | `medlem.stronggym.dk/Account/Login` |
| `/Account/Signup/*` | samme sti på medlem |
| `/info/medlemsadministration` | samme sti på medlem |
| `/Activity/ActivityView` | vores egen holdplan-side (eller medlem) |

Lav dem som rigtige 301'ere på hostingen af det nye site, ikke som
JS-redirect — bogmærker, mails og Google-resultater skal følge med.

#### Det løbende vedligehold de advarede om

Certifikatet fornyes ikke altid lydløst. Står der rød "DNS ændring krævet"
ud for en adresse under Site indstillinger → Domain adresser, skal den nye
værdi indsættes hos domæneudbyderen, ellers udløber certifikatet og portalen
vises som usikker. Der kommer ingen notifikation — det opdages ved at se på
den side. Sæt en kvartalsvis kalenderpåmindelse. En medlemsportal med
certifikatadvarsel er reelt nede.

#### Konsekvens for login/tilmelding-opgaven

Model 1 betyder cross-origin: `www.stronggym.dk` → `medlem.stronggym.dk`.
Dermed er iframe-sporet reelt dødt. Third-party cookie-blokering i Safari og
Chrome brækker login i iframe, og det rammer nu også tilmeldingsflowet, fordi
det foregår på et andet origin end sitet. **Link (ny fane) er valget for
både login og tilmelding** — det er ikke længere et åbent spørgsmål.
Afhængigheden til dashboardet (`isLoggedIn`-mock'en) står uændret.

#### Stadig uafklaret

- Hvor hostes det nye statiske site? Valget af hosting afgør hvordan 301'erne
  ovenfor laves, så de to punkter hænger sammen.
- goMember svarede ikke konkret på hvad de plejer at se gå galt ud over
  rækkefølgen og certifikatet. De to punkter ovenfor er fundet her, ikke
  oplyst af dem — der kan være mere af samme slags, som først viser sig ved
  selve skiftet. Hav et rollback klar: DNS tilbage til goMember.


### Link kontra iframe

| | Link (ny fane) | Iframe |
|---|---|---|
| Virker det | Altid | Kun hvis headers tillader framing |
| Visuel sammenhæng | Brugeren forlader sitet | Ser ud som en del af sitet |
| Login og cookies | Virker | Third-party cookie-blokering i Safari og Chrome brækker ofte login i iframe |
| Mobil | Fint | Formularer i iframe fungerer ofte dårligt på mobil |
| Arbejde | Minimalt | Højde, scroll, styling, fejlhåndtering |

**Anbefaling:** link for login — cookie-blokering gør iframe-login for
skrøbeligt til at satse på. For tilmelding kan iframe overvejes hvis
headers tillader det, men link er fortsat det robuste valg.

### Hvad opgaven omfatter

- Find de faktiske URL'er til goMembers login- og tilmeldingsside for Strong Gym
- Kør framing-tjekket ovenfor
- Erstat `renderLogin()` og `renderSignup()` i `index.html` med sider der
  forklarer hvad der sker og sender brugeren videre — ikke mock-formularer
  der ser ægte ud
- `navigate('login')` og `navigate('signup')` kaldes flere steder: topmenu,
  mobilmenu og CTA-knapper på forsiden. Alle skal pege det rigtige sted hen
- Ryd op i `isLoggedIn`-mock'en

### Afhængighed til dashboardet

Dashboard-siden er gemt bag `isLoggedIn`, som er mock og ikke er
adgangskontrol. Flyttes login ud til goMember, findes der ikke længere
nogen login-tilstand på sitet overhovedet — og så skal Dashboard-linket
enten fjernes eller have en rigtig adgangsmekanisme. Afklar det sammen med
denne opgave, ikke bagefter.

---

# Strong Gym Website Rebuild — Project Plan

> Note (dansk): Denne plan taler om "goMember" som medlemsplatform. I resten af
> dette dokument og i [`setup.md`](setup.md) er platformen kaldt **Memberlink**
> (jf. `cdn-02.memberlink.dk` og `stronggym.dk/api/activity/event/days`). Det er
> sandsynligvis samme system/leverandør under to navne — bekræft i Fase 0.

## Context

Strong Gym (stronggym.dk) is a CrossFit-based sports association (forening) in Helsingør, Denmark, with ~130 members. The current website is old, outdated, and hard to maintain. It pulls live data — member info, class schedules, workouts (WODs) — from goMember, a Danish membership-management platform built for foreninger. Members currently log into the existing site to view/edit their personal data and to sign up for classes and membership.

A Swagger/OpenAPI documentation page for the goMember integration was previously seen at a URL resembling `stronggym.dk/swagger` (or similar), but it is no longer accessible. This suggests goMember exposes a per-tenant REST API, but it is not publicly documented or discoverable — it needs to be rediscovered and/or requested directly from goMember.

## Goal

Rebuild stronggym.dk as a modern, fast, maintainable website that:

- Displays live class schedules and gym information pulled from goMember
- Preserves (or improves) the member login experience for viewing/editing personal data and signing up
- Looks modern and is easy for a non-developer (Johan) to maintain going forward

## Phase 0 — Discover the goMember API (do this before any code)

This phase is manual/investigative and should happen before involving Claude Code on implementation, since the whole architecture depends on what's actually available.

1. **Find the Swagger endpoint again.**
   - Check browser history for the exact URL previously visited (search history for "swagger" or "stronggym").
   - Try common patterns directly in a browser:
     - `https://stronggym.dk/swagger`
     - `https://stronggym.dk/api/swagger`
     - `https://api.stronggym.dk/swagger`
     - `https://[tenant].gomember.dk/swagger` (check goMember admin panel for the tenant subdomain)
   - Check the current live site's network requests (browser DevTools → Network tab) while loading the class schedule or login page — this will reveal the actual API host being called right now, even without Swagger docs.
2. **Check the goMember admin backend.**
   - Log into the goMember admin panel and look for a section called "Integration," "API," "Udvikler," or "Developer."
   - If nothing is visible, contact goMember support directly and ask specifically:
     - Do they expose a REST API for reading member data, class schedules, and bookings for existing customers?
     - Is there a private/partner API even if not publicly documented?
     - What authentication method is used (API key, OAuth token, tenant-scoped credentials)?
     - Are there rate limits or usage terms relevant to a public-facing website?
3. **Document what's found, specifically:**
   - Base API URL
   - Authentication method and how to obtain credentials
   - Available endpoints (classes/schedule, member roster if needed, sign-up/booking)
   - Whether member login/personal-data editing can or should stay inside goMember's own hosted portal (recommended — avoids handling sensitive member data and GDPR compliance in the new site)

**Outcome of Phase 0:** a short doc answering "what can the new site actually call, and how."

## Phase 1 — Architecture Decision

Once Phase 0 is resolved, decide:

- **If goMember has a usable API:** New site is a fully separate, modern front end that calls the goMember API for live class schedules/gym data. Member login, personal data editing, and membership sign-up continue to point to goMember's own secure hosted portal (via link or embed) rather than being rebuilt from scratch — this keeps sensitive data and GDPR compliance inside goMember's existing system.
- **If goMember has no usable API:** Fall back to embedding goMember's existing widgets/iframes for schedule and login (similar to how the current site likely works), and focus the rebuild on everything else — design, content, navigation, performance.
