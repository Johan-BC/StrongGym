# Kortlægning: hvad kan man læse i goMember uden login?

Dato: 14. november 2026. Kilde: www.stronggym.dk (goMember/MemberLink).
Metode: kun læsekald (GET), uden login, via `kortlaeg.py`. Der er ikke ændret
eller slettet noget i goMember, og login-adressen `/auth/token` er ikke brugt.

## Kort fortalt

**Det kan læses uden login**

- **Holdplanen** for de kommende uger: hvert hold med dato, start- og
  sluttid, navn (fx "WOD Mandag 0600", "HYROX", "TONS", "Basis/teknik hold"),
  træner, farve, status (planlagt/fuldt booket/aflyst), max. antal pladser,
  **antal tilmeldte**, antal på venteliste og hvilke ugedags-/medlemsgrupper
  holdet er knyttet til. Det er de samme oplysninger som hjemmesiden allerede
  viser.
- **Holdtyperne** ("aktiviteter"): 39 stk. med navn, beskrivelse, farve,
  max. deltagere, om der er venteliste, om fremmøde registreres m.m.
- **Etiketter/grupper** ("tags"): 51 stk. - ugedage, medlemskabstyper
  (Premium, Ung 15-24, Børn 7-14, Klippekort), og interne admin-etiketter som
  "Udmeld slut nov", "Bero slut jan", "Rykker", "Manglende fremmøde". Kun
  navnene - ikke hvilke medlemmer der har dem.
- **Priser på medlemskaber** (indmeldelses-siden): Premium 499 kr./md, Ung 15-24
  år 299 kr./md, Klippekort (10 klip) 850 kr., Børnemedlemskab 7-14 0 kr.
  (Feltet `price` viser 283 / 169 kr. - det er den forholdsmæssige pris for
  resten af november, ikke månedsprisen. Månedsprisen står i `displayPrice`.)
- **Udeblivelsesgebyr** pr. hold (25 kr.) og at holdene bruger klippekort
  (1 klip pr. online-tilmelding).
- **Tilmeldingsformularen** til nye medlemmer (hvilke felter den spørger om).

**Det kan IKKE læses uden login**

- Hvem der er tilmeldt et hold (navne) - serveren svarer med en tom liste.
- Fremmøde/fremmødehistorik - afvist ("Du har ikke rettighed").
- Medlemslister, antal medlemmer, medlemmer pr. etiket - alt afvist.
- Detaljer om etiket-kategorier, prisopsætning pr. etiket/produkt, ressourcer.
- **Historik**: holdplanen bagud i tid er næsten tom. For de 8 uger før i dag
  kom der kun 18 hold, mens der fremover er ca. 30 hold om ugen. Gamle hold med
  deres tilmeldingstal kan altså ikke hentes bagud uden login (og måske heller
  ikke med login - det er ikke afprøvet).

**Det ville kræve det skrivebeskyttede login**

- Antal medlemmer i alt og pr. medlemskabstype/etiket.
- Fremmøde pr. hold over tid (hvem kom, no-shows).
- Ældre holdplaner/belægning, hvis de overhovedet gemmes.
- Etiket-kategorier og prisopsætning i detaljer.

**Bemærk:** tilmeldingstallet (`booked`) kan læses for hvert kommende hold. Hvis
det hentes løbende (fx dagligt), kan man selv opbygge en belægningshistorik
uden login.

## Sikkerhedsfund

1. **Ingen persondata kunne læses uden login.** Alle seks prøvekald mod
   medlemslister blev afvist (401 eller 500 med "Du har ikke rettighed til at
   hente medlemmer"). Booking-lister for et hold gav en tom liste, selv om holdet
   havde tilmeldte.
2. **Fejlbeskeder afslører interne detaljer (lav alvor).** Nogle kald giver
   HTTP 500 med .NET-stacktrace og interne klassenavne (fx
   `ClubPortal.Api.MemberApiController`, `ClubPortal.Shared.ServiceException`).
   Det er en almindelig, mindre informationslækage hos goMember - ikke noget
   Strong Gym selv kan rette, men kan nævnes for goMember support.
3. **Interne admin-etiketter er offentlige.** Navnene på etiketter som
   "Rykker", "Manglende fremmøde", "Ønsker udmelding" og "Bero slut ..." kan
   læses af alle. Det afslører ikke hvem der har dem, men viser intern
   administration. Overvej om det er i orden.
4. Trænernavne (`responsible`) er offentlige - som forventet, de står også på
   hjemmesiden. Trænernes medlems-id'er og -numre er fjernet fra de gemte filer.

---

## Teknisk bilag

### Omfang

- Kald i alt i den endelige kørsel: **102** (loft 400, maks 2/s, timeout 30 s).
  Statusfordeling: 200: 48 · 401: 42 · 403: 3 · 400: 1 · 500: 8.
- Tags afsøgt: ActivityApi, ActivityDataApi, ActivityEventDataApi, EventApi,
  EventNewApi, BookingApi, TagApi, TagDataApi, TagCategoryDataApi, PriceApi,
  PriceDataApi, ProductApi, SignupApi, TagPriceDataApi - 69 GET-paths, heraf 46
  kaldt og 23 sprunget over.
- Id'er i paths kommer kun fra data som offentlige kald allerede har
  returneret, maks 3 værdier pr. path.
- Fuldt katalog pr. path: `adgang.json`. Rå (rensede) svar: `data/`.

### Holdplan (`/api/activity/event/days`)

Hentet i månedsbidder fra 2026-09-19 til 2027-01-09 med `eventsToShow=300`.
Ingen bid ramte loftet på 300 (største: 130), så intet er afskåret.

| Periode | Dage med hold | Hold |
|---|---|---|
| 19/9 - 1/10 | 4 | 8 |
| 1/10 - 1/11 | 10 | 10 |
| 1/11 - 1/12 | 30 | 123 |
| 1/12 - 1/1 | 31 | 130 |
| 1/1 - 9/1 | 8 | 32 |
| **I alt** | | **303** (31 aktiviteter, 10 tags) |

November: 542 tilmeldte ud af 1315 pladser (41 %). Status: 107 planlagt,
11 fuldt booket, 5 aflyst.

Bemærk: parameteret skal hedde `fromOffset` (ikke `fromTime`, som gav 0 svar).
`/api/activity/event/list` ignorerer tilsyneladende `toTime` og returnerer
30 dage frem fra `fromOffset`.

### Felter pr. hold (event)

| Felt | Betydning |
|---|---|
| `activityId` | Holdtypen (aktiviteten) holdet hører til |
| `eventId` | Holdets id inden for aktiviteten (`yyyyMMddHHmm`) |
| `entityId` | Samlet id `activityId-eventId` (bruges af `/api/event/{id}`) |
| `name` | Holdnavn, fx "WOD Mandag 0600" |
| `description` | Beskrivelse (ofte tom) |
| `startTime` / `endTime` | Lokal start-/sluttid |
| `startTimeUtc` / `endTimeUtc` | Samme i UTC |
| `meetTime`, `signUpDeadline` (+Utc) | Mødetid og tilmeldingsfrist (kun på nogle hold) |
| `status` | `scheduled` / `booked` (fuldt) / `cancelled` |
| `cancellationMessage` | Tekst ved aflysning |
| `maxAttendees` | Max. pladser (mangler på hold uden loft) |
| `booked` | **Antal tilmeldte** |
| `waitingList` | Antal på venteliste |
| `hasWaitingList` | Om holdet har venteliste |
| `reservations` | Antal reserverede pladser |
| `responsible` | Træner(e) - kun `displayName` er gemt |
| `tagsAssigned` | Etiket-id'er (ugedag og/eller "Alle medlemmer"), slås op i `data/tag.json` |
| `color` | Farvekode til visning |
| `onlineSignup`, `signupOpen` | Om man kan tilmelde sig online / om tilmeldingen er åben nu |
| `onlyLoggedIn`, `allowNonMember`, `maxGuestsPerMember` | Hvem der må deltage |
| `hasPrice`, `price`, `activityHasPrice`, `paymentRules` | Pris (0 på alle hold - klippekort i stedet) |
| `registerAttendance` | Om der registreres fremmøde |
| `attendancePrivacy` | Hvor synlig deltagerlisten er |
| `invitationMedia` | Kanal til invitationer (sms) |
| `locationName`, `rules`, `attendanceMessage` | Sted, regler, besked ved tilmelding |
| `isSuperEvent`, `isParent`, `sequence`, `hideFromOverview` | Teknisk gruppering/visning |
| `allowPartner`, `allowInvite`, `disableComments`, `comments*` | Funktioner slået til/fra |
| `createdTs` / `modifiedTs` | Oprettet / sidst ændret |
| `inviteMembers`, `inviteTags`, `formDefinition` | Tomme lister i alle svar |

`/api/event/{id}` og `/api/activity/{activityId}/event/{id}` giver derudover
`noShowPrice` (25 kr.), `prices` og `assignedTags` (fulde etiket-objekter).

### Endpoints efter status

**200 med data (12)**

| Path | Indhold |
|---|---|
| `/api/activity/event/days` | Holdplan (se ovenfor) |
| `/api/activity/event/list` | Samme som days, 30 dage frem |
| `/api/activity` | 39 aktiviteter (holdtyper) |
| `/api/activity/{id}` | Én aktivitet |
| `/api/event/{id}` | Ét hold inkl. `noShowPrice` |
| `/api/activity/{activityId}/event/{id}` | Ét hold (samme felter) |
| `/api/activity/{activityId}/price` | Prisregler: 1 klip pr. online-tilmelding, 25 kr. no-show |
| `/api/product` | 4 medlemskabsprodukter med pris og alder |
| `/api/tag` | 51 etiketter med navn, type og kategori |
| `/api/signup/{id}` | Indmeldelsesformular for Klippekort (Tag2517869245434174618) |
| `/api/signup/family` | Formular-definition (samme struktur som signup); behandlet som mulig persondata, så kun feltnavne er registreret og intet er gemt |
| `/api/booking/grid/{activityId}` | Kun tidsskema-struktur (`days`, `slotPools`, `schedules`) - ingen personer; ikke gemt |

**200 men tomt svar (10):** `/api/booking/booked-resources/{activityId}`,
`/api/activity/{activityId}/event/{eventId}/bookings` (tom selv for hold med
tilmeldte), `/api/activity/{activityId}/event/{eventId}/locked`,
`/api/booking/calendar/{activityId}`, `/api/activity/{activityId}/event/{id}/myprice`,
`/api/activity/event/groups`, `/api/event/v3/calendar`,
`/api/activity/{activityId}/event/{eventId}/price`, `/api/price`, `/api/product/tags`.

**401 - kræver login (20):** `/api/activitydata/resource/{id}`,
`/api/activityeventdata/griddata`, `/api/booking/partners/{activityId}`,
`/api/event`, `/api/event/relevant`, `/api/event/v3/{eventId}`,
`/api/pricedata/product/{id}`, `/api/pricedata/tag/{id}`,
`/api/signup/GetOrderForMember/{exclusive}`, `/api/tag/{id}`,
`/api/tagcategorydata/griddata`, `/api/tagcategorydata/wizard`,
`/api/tagcategorydata/wizard/{id}`, `/api/tagcategorydata/{id}`,
`/api/tagdata/griddata`, `/api/tagdata/tagcategory/griddata/{id}`,
`/api/tagdata/members/{id}`, `/api/tagdata/category/{tagCategoryId}`,
`/api/tagdata/membershipcard`, `/api/tagpricedata/griddata`.
Svar: "Account credentials were good, but member authentication is required."

**403 (1):** `/api/activity/{activityId}/attendance` - "Du har ikke rettighed til
at hente booking".

**400 (1):** `/api/booking` - "Ugyldig filter".

**500 (2):** `/api/activity/{ActivityId}/event` (NullReference),
`/api/booking/griddata/{activityId}` (ArgumentNull) - begge med stacktrace.

Swaggerens sikkerhedsmarkering passer ikke med virkeligheden: fx er
`/api/activity` og `/api/activity/event/days` markeret som krævende login, men
er offentlige, mens `/api/activity/{activityId}/attendance` er umarkeret men
afvises.

### Medlems-probe (ét kald hver, mindste sidestørrelse)

| Path | Status | Svar |
|---|---|---|
| `/api/members?filter.pageSize=1` | 500 | "Du har ikke rettighed til at hente medlemmer" |
| `/api/memberdata/grid/data?rows=1` | 401 | kræver login |
| `/api/members/gallery` | 500 | NullReferenceException |
| `/api/members/family` | 401 | kræver login |
| `/api/members/dataresponsible` | 401 | kræver login |
| `/api/members/me` | 401 | kræver login |

Ingen af dem returnerede data, så der er ingen feltnavne eller antal at
rapportere.

### Sprunget over (23)

- `DENIED_PATHS`: `/api/activitydata/batchupdate/{id}`,
  `/api/activitydata/clone/{id}`, `/api/tagcategorydata/clone/{id}`,
  `/api/tagdata/clone/{id}`.
- Ord i path: `/api/booking/{id}/validatecancel` (cancel),
  `/api/tagdata/autoassign/{departmentId}/{id}` (assign).
- Usikker: `/api/tagdata/reorder/{category}/{id}` (lyder som en ændring),
  `/api/tagdata/category/{tagCategoryId}/{id}` (uklart hvilket id),
  `/api/activitydata/griddata/{id}` (uklart hvilket id).
- Ukendt parameterværdi (ikke gættet): `/api/activitydata/event/{xmlForm}/{id}`,
  `/api/pricedata/activity/{actType}/{id}`, `/api/tagdata/{type}/{id}`.
- Intet id i offentlige data: `/api/booking/{id}`,
  `/api/activity/{activityId}/event/{eventId}/bookings/{id}`,
  `/api/tagpricedata/{id}`.
- Persondata, ikke gættet: `/api/activity/{activityId}/member/{memberId}`.
- Lavniveau-entity (`?partitionKey=&rowKey=`): `/api/ActivityDataApi`,
  `/api/ActivityEventDataApi`, `/api/PriceDataApi`, `/api/SignupApi`,
  `/api/TagCategoryDataApi`, `/api/TagDataApi`, `/api/TagPriceDataApi`.

### Det er ikke verificeret

- Hvorfor historikken er så tynd: om goMember sletter/skjuler afholdte
  gentagne hold, eller om de kan hentes med andre parametre eller med login.
- Om de tomme 200-svar (fx bookinger pr. hold) giver data med login.
- Om `/api/product` viser alle produkter eller kun dem der kan købes online.
- Produkt-id'erne i `/api/product` er tag-id'er; `/api/pricedata/product/{id}`
  med dem gav 401, så det er ikke afklaret om id-typen er rigtig.
- Login-varianten (`check_auth.py`) er stadig ikke kørt.

### Persondata i de gemte filer

`kortlaeg.py` renser alle svar før de gemmes: medlemsnumre/-id'er fjernes,
lister med medlemmer (fx `responsibleUsersIds`, `inviteMembers`) erstattes af
antal, og `responsible` beholder kun trænerens navn. Svar fra booking-,
fremmøde- og medlems-endpoints gemmes aldrig; kun status, antal og feltnavne
står i `adgang.json`.
