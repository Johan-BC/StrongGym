# Deltagelse på holdene - 14. maj til 14. november 2026

Dato: 14. november 2026. Kilde: goMember, hentet med det skrivebeskyttede
login via `deltagelse.py` (kun læsekald). Alle tal står i `deltagelse.json`.
Ingen navne eller andre personoplysninger er gemt - kun antal.

---

## Kort fortalt (til bestyrelsen)

**I de sidste 6 måneder er der afholdt 560 træningshold med i alt 4.526
tilmeldinger** - i snit **8 pr. hold**, og **64 % af pladserne** blev brugt.
95 hold var fuldt bookede. 53 hold blev aflyst: 22 på grund af flytningen til
Industrivej (især 9.-14. oktober), 23 fordi for få var tilmeldt, 6 fordi
træneren var forhindret.

| Holdtype | Hold afholdt | Tilmeldte i alt | Gennemsnit pr. hold | Fyldningsgrad | Fuldt booket | Aflyst |
|---|---|---|---|---|---|---|
| WOD | 376 | 3.354 | 8,9 | 70 % | 81 | 29 |
| WOD uden træner | 53 | 280 | 5,3 | 44 % | 1 | 3 |
| HYROX | 33 | 348 | 10,5 | 75 % | 5 | 5 |
| TONS | 25 | 113 | 4,5 | 38 % | 0 | 1 |
| Lang WOD | 24 | 162 | 6,8 | 45 % | 2 | 1 |
| Basis/teknik | 22 | 139 | 6,3 | 79 % (8 pladser) | 6 | 3 |
| MASH | 18 | 72 | 4,0 | 33 % | 0 | 1 |
| Børnehold 5-12 år | 9 | 58 | 6,4 | 53 % | 0 | 10 |
| **I alt** | **560** | **4.526** | **8,1** | **64 %** | **95** | **53** |

**Mest brugte faste hold** (snit tilmeldte): Torsdag 16:30 WOD (12,4 - fuldt
booket 16 af 26 gange), Onsdag 17:00 HYROX (12,4), Mandag 16:00 WOD (11,6),
Fredag 08:15 WOD (11,4), Søndag 08:00 WOD (11,2).
**Mindst brugte:** Fredag 16:30 MASH (4,0), Tirsdag 19:00 WOD (4,5), Tirsdag
17:45 TONS (4,5), Mandag 06:00 WOD uden træner (4,6), Torsdag 08:15 WOD (4,7).

**Udvikling pr. måned:** stabilt omkring 8 tilmeldte pr. hold hele perioden.
Lavest i juni (7,4 og 58 %), højest i august (8,8 og 68 %). Oktober havde 22
aflyste hold pga. flytningen, men de afholdte hold var lige så fyldte som
ellers.

**Fremmøde:** Fra maj til midt i oktober blev der registreret fremmøde på de
fleste hold, og 9 ud af 10 tilmeldte mødte op. Siden flytningen er det næsten
holdt op - i november er fremmøde kun registreret på 11 af 46 hold. Tallene
ovenfor er derfor **tilmeldte**, ikke fremmødte.

**Hvad skal bestyrelsen tage stilling til?**

- Fem faste hold har i snit under 5 tilmeldte (MASH, Tirsdag 19:00, TONS,
  Mandag 06:00, Torsdag 08:15). Skal de fortsætte, flyttes eller lægges sammen?
- Torsdag 16:30 og Mandag 16:00 er fulde mere end halvdelen af gangene - der
  er måske plads til et ekstra hold omkring det tidspunkt.
- Skal trænerne igen registrere fremmøde? Det er det eneste der kan vise
  hvor mange der faktisk kommer (og om udeblivelsesgebyret bruges).

---

## 1. Metode

1. Alle 39 aktiviteter fra `/api/activity` (+ 2 der kun findes i holdplanen).
2. Holdplanen `/api/activity/event/days` for vinduet i månedsbidder. Den
   gav 160 hold i vinduet, men kun 104 før 1/11 - den viser ikke de hold der
   genereres ud fra en gentagelse, så næsten alle almindelige WOD før
   november mangler.
3. For hver aktivitet og hver fast tid (fra `holdtyper.json` + holdplanen) er
   hver uge i vinduet slået op direkte med
   `/api/activity/{activityId}/event/{yyyyMMddHHmm}`. Hold-id'et er seriens
   tidspunkt; flyttes et hold, beholder det id'et men får ny `startTime`
   (fx MURPH 25/5 kl. 09:00 på serien Mandag 16:00). Alle tal bruger den
   faktiske `startTime`.
4. TONS bruger id 60 min før lokal tid; varianter -60/-120 min er prøvet.
5. Huller: for hver aktivitet og måned hvor intet hold blev fundet (før
   aktivitetens sidste fund, eller hele vinduet for hvilende aktiviteter) er
   én dato prøvet med alle tidspunkter huset bruger den ugedag (±0/60/120
   min). 427 opslag - **alle gav 404**, dvs. der er ingen skjulte serier.
6. For alle afholdte hold med tilmeldte er bookinglisten hentet og straks
   talt op (antal, på venteliste, med fremmøde). Kun antallene er gemt.

Kald i alt: ca. **1.990** (979 i første kørsel, som blev afbrudt af en
tidsgrænse men havde gemt alt i cachen, 988 i anden, ca. 25 i forundersøgelse).
Statuskoder i anden kørsel: 561 × 200, 427 × 404. Maks 2 kald/sek.

## 2. Fantom-regel - hvad tæller som "afholdt"

**Forundersøgelse** (WOD Lørdag 0900, serie siden 2021):

| Opslag | Svar |
|---|---|
| 6/6 2026 09:00 (rigtig tid) | 200, 6 tilmeldte |
| 6/6 2026 09:15 (forkert tid) | 404 "Event not found" |
| 7/6 2026 (forkert ugedag) | 404 |
| 4/1 2020, 5/1 2019 (langt tilbage) | 404 |
| WOD Tir 08:15 (oprettet 31/10) den 2/6 | 404 |

goMember opfinder altså **ikke** hold: findes der ingen serie på datoen, svarer
den 404. Det er den vigtigste beskyttelse mod fantomer.

**Regel, i rækkefølge:**

| Klasse | Regel | Antal i vinduet |
|---|---|---|
| ikke slået op | 404 fra detaljekaldet | 702 opslag (ingen hold) |
| ikke træning | Rengøring, Ungeenheden, "Fodbold Unge i Boxen" | 49 |
| aflyst | `status = cancelled` | 53 |
| udeladt af serien | `status = excluded` - datoen er taget ud af serien i goMember | 22 |
| fantom | seriens `createdTs` efter holdets dato (eller aktiviteten oprettet efter) | **0** |
| **afholdt** | ellers, og mindst 1 tilmeldt | **560** |
| afholdt med 0 tilmeldte | ellers (serien fandtes, ikke aflyst, ingen tilmeldte) | 30 |

"Udeladt" (22) er fx pinsedag 25/5, lørdag 30/5, Børnehold i sommerferien og
weekenden 25.-27/9, hvor de faste hold var taget ud og erstattet af
engangshold på en anden aktivitet (…140362, "POP UP WOD", "LANG WOD" osv.).
Ét udeladt hold havde `booked = 1` men ingen bookinger - talt som udeladt.

"0 tilmeldte" (30) er rapporteret for sig og **ikke** med i gennemsnittene:
13 er "MIKKO(S) - uden træner" (tirsdag 08:15 maj-sep), 6 "MEMBERS WOD - uden
coach" (torsdag 08:15 i sommer), 7 MASH fredage, resten enkeltstående. Om
holdet reelt fandt sted kan ikke ses - der var bare ingen tilmeldt.

## 3. Pr. måned (hele huset, træningshold)

| Måned | Afholdt | Tilmeldte | Snit | Fyldning | Fuldt booket | Aflyst | Udeladt | 0 tilm. | Fremmøde registreret på | Fremmødte / tilmeldte |
|---|---|---|---|---|---|---|---|---|---|---|
| maj (14.-31.) | 51 | 431 | 8,5 | 62 % | 6 | 3 | 6 | 3 | 43 hold | 93 % |
| juni | 97 | 717 | 7,4 | 58 % | 10 | 4 | 0 | 6 | 85 | 93 % |
| juli | 85 | 702 | 8,3 | 64 % | 15 | 10 | 5 | 7 | 75 | 95 % |
| august | 99 | 870 | 8,8 | 68 % | 25 | 4 | 2 | 6 | 86 | 95 % |
| september | 97 | 772 | 8,0 | 65 % | 16 | 6 | 8 | 7 | 81 | 94 % |
| oktober | 85 | 665 | 7,8 | 64 % | 16 | 22 | 1 | 1 | 75 (heraf 17 uden nogen) | 77 % |
| november (1.-14.) | 46 | 369 | 8,0 | 67 % | 7 | 4 | 0 | 0 | 11 | 49 % |

Ugetal står i `deltagelse.json` → `pr_uge`. Uge 42 (12.-18/10) havde kun 11
afholdte hold og 13 aflyste (flytning).

**Kontrol mod november-tallet i HOLDTYPER.md/RAPPORT:** 1.-14. nov. giver
præcis **46 hold, 369 tilmeldte, 555 pladser (66,5 %)**, 7 fuldt booket, 4
aflyst - samme som før.

## 4. Pr. fast tid (mindst 8 afholdte hold)

| Tid | Afholdt | Tilmeldte | Snit | Fyldning | Fulde |
|---|---|---|---|---|---|
| Torsdag 16:30 WOD | 26 | 323 | 12,4 | 90 % | 16 |
| Onsdag 17:00 HYROX | 24 | 298 | 12,4 | 83 % | 5 |
| Mandag 16:00 WOD | 24 | 278 | 11,6 | 94 % | 15 |
| Fredag 08:15 WOD | 26 | 295 | 11,4 | 83 % | 7 |
| Søndag 08:00 WOD | 25 | 281 | 11,2 | 81 % | 6 |
| Lørdag 08:00 WOD | 26 | 280 | 10,8 | 81 % | 8 |
| Onsdag 16:00 WOD | 25 | 267 | 10,7 | 85 % | 9 |
| Mandag 08:15 WOD | 24 | 218 | 9,1 | 70 % | 4 |
| Onsdag 08:15 WOD | 25 | 224 | 9,0 | 72 % | 5 |
| Tirsdag 16:30 WOD | 24 | 204 | 8,5 | 71 % | 5 |
| Lørdag 09:00 WOD | 25 | 212 | 8,5 | 64 % | 2 |
| Mandag 17:00 WOD | 20 | 162 | 8,1 | 68 % | 2 |
| Fredag 15:30 WOD | 24 | 186 | 7,8 | 64 % | 2 |
| Søndag 09:00 Lang WOD | 24 | 162 | 6,8 | 45 % | 2 |
| Børnehold søndag 10:45 | 9 | 58 | 6,4 | 53 % | 0 |
| Torsdag 18:00 Basis/teknik | 22 | 139 | 6,3 | 79 % | 6 |
| Onsdag 06:00 WOD uden træner | 24 | 147 | 6,1 | 51 % | 0 |
| Lørdag 10:00 HYROX (fra 29/8) | 9 | 50 | 5,6 | 46 % | 0 |
| Mandag 19:45 WOD | 19 | 99 | 5,2 | 43 % | 0 |
| Torsdag 19:00 WOD (fra 13/8) | 9 | 46 | 5,1 | 42 % | 0 |
| Torsdag 08:15 WOD | 19 | 89 | 4,7 | 39 % | 0 |
| Mandag 06:00 WOD uden træner | 24 | 111 | 4,6 | 39 % | 0 |
| Tirsdag 17:45 TONS | 25 | 113 | 4,5 | 38 % | 0 |
| Tirsdag 19:00 WOD | 22 | 99 | 4,5 | 38 % | 0 |
| Fredag 16:30 MASH | 18 | 72 | 4,0 | 33 % | 0 |

Top 10 / bund 10 efter snit står også i `deltagelse.json`
(`top_10_faste_tider`, `bund_10_faste_tider`). Basis/teknik ligger lavt i
snit, men har kun 8 pladser og er 79 % fyldt.

Tirsdag 08:15 var "MIKKO(S) - uden træner" (5 hold med tilmeldte, 13 med 0)
indtil 22/9; derefter almindelig WOD fra november.
Lang WOD søndag skiftede aktivitet 6/9 ("WOD (Laaang workout)" → "Lang WOD").
Torsdag 19:00 WOD og Lørdag HYROX er startet i august.

## 5. Pr. goMember-aktivitet

Se `deltagelse.json` → `pr_aktivitet` (afholdt, tilmeldte, snit, fyldning,
fulde, venteliste, aflyst, fremmøde, første/sidste hold). Engangsaktiviteten
…140362 (findes ikke i `/api/activity`) havde 15 afholdte hold med 95
tilmeldte (POP UP WOD, opstartsweekenden 25.-27/9 m.fl.).

## 6. Venteliste og fremmøde

- **Venteliste:** 49 personer i alt på venteliste fordelt på 25 hold, næsten
  alle WOD (Torsdag 16:30: 20 på 5 hold). Tallet er det der står på holdet
  efter det er afholdt; om ventelisten ryddes ved afholdelse vides ikke.
- **Fremmøde (`attendedTs` på bookingen):** registreret på 456 af de 560
  afholdte hold. På dem mødte **3.316 af ca. 3.680 tilmeldte (90 %)**.
  Registreringen er pr. hold og skifter: nogle hold har fremmøde selv om
  holdets indstilling `registerAttendance` nu står til "nej" (62 hold), og
  27 hold har indstillingen slået til uden et eneste registreret fremmøde
  (17 af dem i oktober). HYROX onsdag og WOD Torsdag 08:15 har næsten aldrig
  fremmøde registreret. Fra uge 43 falder andelen (72 %, 59 %, 34 %) og i uge
  46 er der ingen.
- Det er **ikke** verificeret om goMember selv sætter fremmøde automatisk
  (fx ved holdstart) og trænerne kun fjerner udeblivere, eller om trænerne
  krydser af. 90 % er plausibelt for begge.

## 7. Forbehold

- **Holdtyper:** mapping fra `holdtyper.json`. Engangshold på …140362 er
  typebestemt ud fra navnet. Torsdag 08:15 hed "MEMBERS WOD - uden coach" i
  sommer, men tæller som WOD (aktivitetens type). Tirsdag 08:15 "MIKKO" tæller
  som "WOD uden træner".
- **Tilmeldte = `booked`** på holdet efter afholdelse (inkl. evt. flere
  deltagere på samme booking). Afmeldinger før holdet er ikke med.
- **Hold vi kan have overset:** et hold på en tid der aldrig er set i
  holdplanen, på en aktivitet der også havde hold på sin kendte tid samme
  måned, ville ikke blive fundet. Hul-søgningen fandt ingen ekstra serier, så
  risikoen vurderes som lille. Slettede serier kan ikke ses (404).
- **0-tilmeldte-hold** (30) er ikke regnet med i snit og fyldning; regnes de
  med, falder snittet fra 8,08 til 7,67 og fyldningen fra 64 % til ca. 61 %.
- Aflysningsårsag er grupperet i kategorier; selve teksten er ikke gemt (den
  nævner i nogle tilfælde trænere og hvor de er).
- Holdnavne gemmes som de står i den offentlige holdplan; et par af dem
  indeholder et trænernavn (fx "WOD med medtræner …").

## 8. Filer

| Fil | Indhold |
|---|---|
| `deltagelse.py` | Henter (med cache, 2 kald/s, loft 2.500 pr. manuel kørsel) og regner for de seneste 6 måneder til i dag. `--offline` bruger kun cachen, `--dato`/`--plan` til test. Køres hver nat af `opdater.py`. |
| `deltagelse_cache.json` | Afledte felter pr. hold-opslag og bookingantal - ingen personværdier. Slet for at hente forfra. |
| `deltagelse.json` | Alle summer + én række pr. hold (dato, aktivitet, type, status, tilmeldte, fremmøde, pladser, venteliste, klassifikation). |
