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
- Adresse: Haderslevvej 27D, 3000 Helsingør
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
- Selve tilmelding/login/signup er stadig mock (client-side state der nulstilles ved refresh) — KUN holdplan-/forside-visningen er live. Rigtig tilmelding ville kræve autentificeret skrive-adgang til Memberlink (bevidst undladt).
- Middleman'en afhænger af at Cloudflare-worker'en kører og at Memberlinks API-format er uændret (se [`setup.md`](setup.md)).
