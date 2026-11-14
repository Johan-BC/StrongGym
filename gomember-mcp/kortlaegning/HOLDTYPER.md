# Holdtyper i goMember - kortlægning

> **Rettelse 14. november 2026 (senere samme dag):** Denne rapport siger, at
> holdplanen bagud i tid er næsten tom, og at den fulde plan først startede
> 1. november. Det er forkert. Holdplanskaldet viser bare ikke gamle hold fra
> faste serier. Med login kan hvert hold slås op enkeltvis, og der har kørt
> fuld ugeplan hele perioden. De rigtige tal for 14. maj - 14. november står i
> `DELTAGELSE.md` (560 afholdte hold, 4.526 tilmeldinger).


Dato: 14. november 2026. Grundlag: de anonyme snapshots i `data/` (hentet
14/11 kl. 20:37, se `RAPPORT.md`). Ingen nye kald mod goMember.
Alle tal kommer fra `analyse_holdtyper.py` (kør `python3 analyse_holdtyper.py`
for at se dem), som også skriver `holdtyper.json` til frontend-arbejdet.

---

## Kort fortalt (til bestyrelsen)

**Hvilke hold har vi?** Strong Gym har reelt **10 slags aktiviteter** i
kalenderen: WOD, WOD uden træner (kl. 06), Lang WOD, HYROX, TONS, MASH,
Basis/teknik, Børnehold, plus to ting der ikke er træningshold: Rengøring og
Ungeenheden (Helsingør Kommune låner lokalet). I goMember er de 10 typer
spredt ud på **39 "aktiviteter"** - fordi hvert fast tidspunkt typisk har sin
egen aktivitet. Alene WOD er oprettet **17 gange** (én pr. ugedag og
klokkeslæt), fx "WOD Mandag 0600", "WOD Lørdag 0900".

**Hvordan ser ugen ud?** En normal uge har **26 træningshold** + 2
rengøringer + 1 ungeenhed: mandag 5 hold, tirsdag-torsdag 4, fredag-søndag 3.
17 af de 26 er almindelige WOD. Morgenhold kl. 06 (man/ons) og 08:15
(hverdage), eftermiddag/aften 15:30-20:45, weekend om formiddagen.

**Hvor fyldt er holdene?** I de to uger med fuld holdplan (1.-14. nov.) var
der i snit **8 tilmeldte pr. hold, 67 % af pladserne** brugt. 7 af 46 hold
var fuldt bookede. Mest fyldt: Onsdag 16:00 og Torsdag 16:30 WOD (100 %) og
Basis/teknik (88 %). Mindst fyldt: Tirsdag 19:00 og Torsdag 19:00 WOD
(25-29 %) og Børneholdet (1 tilmeldt; 2 af 10 søndage aflyst).

**Hvad er rodet?**

1. Samme hold er oprettet mange gange. Skal noget ændres for "alle WOD"
   (fx max. pladser, venteliste), skal det gøres 17 steder.
2. Indstillingerne er ikke ens mellem "søskende": venteliste og
   fremmøderegistrering skifter fra uge til uge på de fleste hold, farverne
   er ikke ens, og samme hold staves forskelligt (Hyrox/HYROX, TONS/Tons).
3. Træneren står kun på hold, som nogen har rettet i manuelt. På **196 af de
   229 kommende hold** kan man ikke se hvem der er træner (navnet er skjult
   for offentligheden, hvis det ikke er sat på det enkelte hold).
4. Etiketter (tags) bruges til flere ting på én gang: medlemstyper, ugedage,
   interne påmindelser ("Rykker", "Udmeld slut nov") og adgang til hold.
5. 9 gamle aktiviteter ligger stadig og fylder, og juleaften, juledagene og
   nytårsdagene har alle hold som en normal uge (19 hold) - de er ikke aflyst endnu.

**Det anbefaler vi:** at en ny admin-skærm viser de 10 holdtyper og en
ugeplan (ugedag x tid) i stedet for 39 aktiviteter, og selv sørger for at
ændringer slår igennem på alle hold af samme type. Konkret: (1) én
"holdtype" med standard-pladser, farve, venteliste og fremmøde; (2) en
ugeplan hvor man sætter træner pr. fast tid; (3) knapper til "aflys dette
hold", "skift træner", "flyt tid" og "luk for jul". goMember har de
nødvendige skrive-funktioner (afsnit 9), men det er en separat beslutning -
denne integration må kun læse.

---

## 1. Datamodel

```
Aktivitet (Activity…)            = "holdtype" i goMembers forstand, ét pr. fast tid hos os
 └─ Serie (sequence = activityId) = gentagelsesregel med egne standardværdier
     └─ Hold/event (eventId)       = én dato; enten genereret fra serien
                                     eller med egen gemt record (overstyring)
Tags   → tagsAssigned på aktivitet/hold (hvem må se/booke)
Pris   → prisregler på aktiviteten (klip pr. online-tilmelding, udeblivelsesgebyr)
Produkt (medlemskab) = et tag (product.id er et tag-id)
```

**Id'er.** `entityId` = `activityId-eventId` på alle 303 hold. `eventId` er
lokal starttid `yyyyMMddHHmm` på 287 af 303. Undtagelser: 10 TONS-hold har
eventId 60 min før den lokale starttid (svarer til UTC-tiden 16:45 - om holdet
er flyttet fra 16:45 eller oprettet anderledes kan ikke afgøres), og 6 hold i
september (en aktivitet der ikke findes i `/api/activity`) har id'er med
bogstavsuffiks, fx `202609251330PB`. **En frontend må derfor ikke udlede tid
af eventId** - brug `startTime`.

**sequence / isParent / isSuperEvent.** `sequence` = `activityId` på 297
hold; mangler på de 6 september-hold. `isParent` og `isSuperEvent` er
`false` på alle 303 hold og 39 aktiviteter, `isGroup` false på alle. Der er
altså ingen hold-hierarkier i brug; hver aktivitet har præcis én serie.

**Genererede hold vs. hold med egen record.** 89 hold har felterne
`locationName`/`rules` (egen gemt record), 214 har ikke (genereret fra
serien). Det deler tydeligt:

| | egen record (89) | genereret (214) |
|---|---|---|
| navngiven træner | 89 | 0 |
| `signUpDeadline` sat | 76 | 0 |
| `meetTime` sat | 81 | 0 |

På de 214 genererede hold er antallet af `responsible`-objekter lig med
aktivitetens `responsibleUsersIds._count` (214 af 214) - de arver
aktivitetens standardansvarlige, men navnet vises ikke anonymt. Ingen hold har
en tom ansvarlig-liste.

**inviteTags / inviteMembers / formDefinition** er tomme på alle 303 hold -
ikke i brug.

**Felter kun på aktiviteten** (bl.a.): `responsibleUsersIds`, `activityMode`,
`allow*`-flagene, `assignedTags`, `viewOrder`, `eventsCount`, `minAttendees`,
`resourceIds`, `unitName`.
**Felter kun på holdet:** `startTime/endTime(+Utc)`, `meetTime`,
`signUpDeadline`, `status`, `cancellationMessage`, `booked`, `waitingList`,
`reservations`, `responsible` (navne), `sequence`, `isParent`,
`signupOpen`, `price/hasPrice/activityHasPrice/paymentRules`,
`locationName`, `rules`, `disableComments`.
**Fælles felter:** `name`, `description`, `color`, `maxAttendees`,
`hasWaitingList`, `registerAttendance`, `onlineSignup`, `onlyLoggedIn`,
`allowNonMember`, `allowPartner`, `allowInvite`, `attendancePrivacy`,
`maxGuestsPerMember`, `hideFromOverview`, `tagsAssigned`, `attendanceMessage`,
`invitationMedia`, m.fl.

**Hvilke felter varierer mellem hold af samme aktivitet** (antal aktiviteter
hvor feltet har mere end én værdi):

| Felt | aktiviteter | Eksempel |
|---|---|---|
| `responsible` | 27 | WOD Fredag 0815: 6 forskellige trænere |
| `registerAttendance` | 23 | WOD Fredag 0815: true/false |
| `hasWaitingList` | 18 | WOD Fredag 0815: true/false |
| `color` | 8 | `#9ccc65` vs `9ccc65` |
| `maxAttendees` | 5 | WOD Fredag 0815: 12/14 |
| `name` | 4 | WOD Onsdag 0600 → "WOD uden træner" / "WOD med gæste træner" |
| `description` | 2 | WOD Torsdag 1630: "2-personers MAKKER", "VIKAR:" |

**Varierer aldrig inden for en aktivitet:** `tagsAssigned`, `onlineSignup`,
`onlyLoggedIn`, `allowNonMember`, `allowPartner`, `allowInvite`,
`attendancePrivacy`, `maxGuestsPerMember`, `hideFromOverview`,
`disableComments`, `invitationMedia`, `paymentRules`, `activityHasPrice`.

**Hold vs. aktivitetens standardværdi.** Allerede på de *genererede* hold
afviger `hasWaitingList` (132/214), `registerAttendance` (121/214), `name`
(15/214) og `color` (8/214) fra aktiviteten. Det betyder at serien har sine
egne standardværdier, der ikke er de samme som aktivitetens - tre niveauer at
holde styr på (aktivitet → serie → hold). `maxAttendees`, `description` og
`tagsAssigned` afviger aldrig på genererede hold; kapacitet afviger kun på 5
hold med egen record.

**Pris.** Kun hentet for 3 aktiviteter: WOD Lørdag 0800 og 0900 har
`perOnlineSignup` = 1 klip (`currency: point`, tag Klippekort) og `noShow` =
25 kr.; Hyrox (lørdag) har ingen prisregler. Den anonyme holdplan viser
`activityHasPrice=false`/`paymentRules=0` på alle hold, mens detaljekaldet for
samme hold viser `true`/`2` - holdplanen kan altså ikke bruges til at se
priser. Medlemskaber (product.json, `displayPrice` = månedspris): Premium 499,
Ung 15-24 år 299, Klippekort 10 klip 850, Børnemedlemskab 7-14 0 kr.

## 2. Inventar - alle aktiviteter

Status: **29 aktive** (hold efter snapshot), **9 hvilende** (ingen hold i
vinduet 22/9 2026 - 8/1 2027), **1 kun fortid** (MIKKO, ét hold 22/9).
Derudover 1 aktivitet der kun findes i holdplanen (6 hold 25.-27/9).

Fælles for alle 39: `onlyLoggedIn=false`, `allowNonMember=false`,
`maxGuestsPerMember=0`, `hideFromOverview=false`, `invitationMedia=sms`,
`autoPromote=false`. `activityMode` = event (38) / resource (1, Test booking).
Tilmeldingsfrist (hold med feltet): ved holdets slut 64, ved start 11, 30 min
efter start 1; 227 hold har ingen frist sat. Kapacitet 0 = intet loft.

| Aktivitet (id-hale) | Type | Status | Hold | Ugedag/tid | Kap. | Vente-liste* | Fremmøde* | Online | Farve | Tags (aktivitet) | Navngivne trænere (hold) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| WOD Mandag 0600 (…660410) | WOD uden træner | aktiv | 10 | Man 06:00-07:00 | 12 | ja | nej | ja | aed581 | Alle, mandag | Johan Berlin Christophersen 8 |
| WOD Mandag 0815 (…154536) | WOD | aktiv | 10 | Man 08:15-09:15 | 12 | ja | nej | ja | 9ccc65 | Alle, mandag | Christian Gøtzsche 1, Peter A. Schougaard 1 |
| WOD (…700946) → "WOD Mandag 1600" | WOD | aktiv | 10 | Man 16:00-17:00 | 12 | ja | nej | ja | 9ccc65 | Alle | Ivan Munch Petersen 3 |
| WOD (…491831) → "WOD Mandag 1700" | WOD | aktiv | 10 | Man 17:00-18:00 | 12 | ja | nej | ja | 9ccc65 | Alle | Ivan Munch Petersen 2 |
| WOD Mandag 1945 (…176157) | WOD | aktiv | 10 | Man 19:45-20:45 | 12 | ja | nej | ja | 9ccc65 | Alle, mandag | Christian Gøtzsche 1 |
| WOD (…514920) | WOD | aktiv | 10 | Tir 08:15-09:15 | 12 | ja | nej | ja | 9ccc65 | (ingen) | Sussi Larsen 1, Mathias Wachenschwanz 1 |
| WOD Tirsdag 1630 (…951096) | WOD | aktiv | 10 | Tir 16:30-17:30 | 12 | ja | nej | ja | 9ccc65 | Alle, tirsdag | Jeppe Rasmussen 1 |
| TONS (…680950) | TONS | aktiv | 10 | Tir 17:45-19:00 | 12 | ja | nej | ja | bdbdbd | (ingen) | Jeppe Rasmussen 1 |
| WOD Tirsdag 1900 (…869245) | WOD | aktiv | 10 | Tir 19:00-20:00 | 12 | ja | nej | ja | 9ccc65 | Alle, tirsdag | Jeppe Rasmussen 1 |
| WOD Onsdag 0600 (…347887) | WOD uden træner | aktiv | 10 | Ons 06:00-07:00 | 12 | ja | nej | ja | 8bc34a | Alle, onsdag | Mick Nielsen 9 |
| WOD Onsdag 0815 (…337813) | WOD | aktiv | 10 | Ons 08:15-09:15 | 12 | ja | nej | ja | 9ccc65 | Alle, onsdag | Silja Andersen 2, Thomas Ronne 1 |
| WOD Onsdag 1600 (…157937) | WOD | aktiv | 10 | Ons 16:00-17:00 | 12 | ja | nej | ja | 9ccc65 | Alle, onsdag | Helena Levin Erting 2 |
| HYROX (…201999) | HYROX | aktiv | 10 | Ons 17:00-18:00 | 12 | ja | nej | ja | 039be5 | Alle | Christoffer Hviid 2 |
| Rengøring (…825494) | Rengøring | aktiv | 12 | Ons 18:30-21:00 | 0 | nej | nej | nej | f8bbd0 | (ingen) | - |
| WOD Torsdag 0815 (…284291) | WOD | aktiv | 10 | Tor 08:15-09:15 | 12 | ja | nej | ja | 9ccc65 | Alle, torsdag | Mia Foldager 1 |
| Ungeenheden Helsingør Kommune (…331666) | Ungeenhed | aktiv | 12 | Tor 09:30-11:00 | 0 | nej | nej | nej | ab47bc | (ingen) | - |
| WOD Torsdag 1630 (…558056) | WOD | aktiv | 10 | Tor 16:30-17:30 | 12 | ja | nej | ja | 9ccc65 | Alle, torsdag | Sebastian Meier 4, Jeppe Rasmussen 1 |
| Basis/teknik hold (…599010) | Basis/teknik | aktiv | 10 | Tor 18:00-19:00 | 8 | ja | nej | ja | ffd54f | Alle, Premium, Klippekort | Silja Andersen 8 |
| WOD (…174455) | WOD | aktiv | 10 | Tor 19:00-20:00 | 12 | ja | nej | ja | 4caf50 (hold: 81c784) | (ingen) | Christian Gøtzsche 2 |
| WOD Fredag 0815 (…615054) | WOD | aktiv | 16 | Fre 08:15-09:15 | 12 | ja | nej | ja | 9ccc65 | Alle, fredag | 6 forskellige (Peter A. Schougaard 2, Mia Foldager 2, …) |
| WOD Fredag 1530 (…903012) | WOD | aktiv | 9 | Fre 15:30-16:30 | 12 | ja | nej | ja | 9ccc65 | Alle, fredag | Jeppe Rasmussen 1 |
| MASH - lidt mere udfordrende end WOD (…738431) | MASH | aktiv | 9 | Fre 16:30-18:00 | 12 | ja | nej | ja | cfd8dc | Alle | Thomas Ronne 1 |
| WOD Lørdag 0800 (…783782) | WOD | aktiv | 9 | Lør 08:00-09:00 | 12 | ja | nej | ja | 9ccc65 | Alle, lørdag | Sebastian Meier 3, Jeppe Rasmussen 2, Mick Nielsen 1 |
| WOD Lørdag 0900 (…044562) | WOD | aktiv | 9 | Lør 09:00-10:00 | 12 | ja | nej | ja | 9ccc65 | Alle, lørdag | Sebastian Meier 3, Jeppe Rasmussen 2, Mick Nielsen 1 |
| Hyrox (…805210) | HYROX | aktiv | 9 | Lør 10:00-11:00 | 12 | ja | nej | ja | 039be5 | (ingen) | Peter A. Schougaard 1 |
| WOD Søndag 0800 (…333604) | WOD | aktiv | 10 | Søn 08:00-09:00 | 12 | ja | nej | ja | 9ccc65 | Alle, søndag | Mick Nielsen 1, Peter A. Schougaard 1, Thomas Ronne 1 |
| Lang WOD (…267054) | Lang WOD | aktiv | 10 | Søn 09:00-10:30 | 12 | ja | nej | ja | 66bb6a | Alle | Mick Nielsen 1, Peter A. Schougaard 1 |
| Børne hold 5-12 år (…362421) | Børnehold | aktiv | 10 | Søn 10:45-11:45 | 12 | ja | nej | ja | fce4ec | (ingen) | Maj Jeppesen 1, Mia Bertram 1 |
| Rengøring (…431091) | Rengøring | aktiv | 11 | Søn 13:00-15:30 | 0 | nej | nej | nej | f8bbd0 | (ingen) | - |
| MIKKO - uden træner (…025217) | WOD uden træner? | kun fortid | 1 | Tir 08:15 (22/9) | 12 | ja | ja | ja | FFD54F | Alle, tirsdag | Thomas Ronne 1 |
| WOD (…134130) | WOD? | hvilende | 0 | - | 12 | ja | ja | ja | 9ccc65 | Alle, Klippekort, mandag | - |
| WOD (…731663) | WOD? | hvilende | 0 | - | 12 | ja | ja | ja | 9ccc65 | Alle, mandag, Klippekort | - |
| WOD (Laaang workout) (…462084) | Lang WOD | hvilende | 0 | - | 16 | ja | ja | ja | 9ccc65 | Alle, søndag | - |
| Tons (…724635) | TONS | hvilende | 0 | - | 12 | ja | ja | ja | e0e0e0 | Alle, tirsdag | - |
| TONS (…736134) | TONS | hvilende | 0 | - | 12 | ja | ja | ja | e0e0e0 | Alle, tirsdag | - (0 ansvarlige) |
| Mash (…189885) | MASH | hvilende | 0 | - | 12 | ja | ja | ja | e0e0e0 | Alle, lørdag | - |
| Rengøring - begrænset træning muligt (…710625) | Rengøring | hvilende | 0 | - | 0 | nej | nej | nej | f44336 | Alle, onsdag | - |
| Rengøring - Begrænset træning muligt (…171449) | Rengøring | hvilende | 0 | - | 0 | nej | nej | nej | f44336 | Alle, søndag | - |
| Test booking (…288292) | Test | hvilende | 0 | - | 1 | nej | nej | ja | 9C27B0 | (ingen) | - |
| *(ikke i /api/activity)* (…140362) | Ukendt | kun fortid | 6 | Fre-Søn 25.-27/9 | - | - | - | - | - | - | Jeppe Rasmussen 2, Peter A. Schougaard 2, Mick Nielsen 1, Thomas Ronne 1 |

\* Venteliste/Fremmøde = aktivitetens standardværdi. På holdene skifter
værdien: venteliste på 18 og fremmøde på 23 af 29 aktive aktiviteter.
`registerAttendance` er true på 7 af 39 aktiviteter, men på 161 af 303 hold.
Alle aktive aktiviteter har 1 standard-ansvarlig, undtagen Hyrox (lørdag) og
Børnehold (2). Fuld liste med frist, priser og datoer: `holdtyper.json` →
`aktiviteter`.

## 3. Navnemønster og forslag til holdtyper

- **15** aktiviteter hedder `WOD <Ugedag> <hhmm>`; alle 15 passer med
  holdenes faktiske ugedag og tid. **17** aktiviteter har hold med et sådant
  navn (to aktiviteter hedder "WOD" men deres hold hedder "WOD Mandag
  1600/1700").
- Navne brugt flere gange: "WOD" ×6, "Rengøring" ×2, "TONS" ×2.
- Samme type, forskellig stavemåde: Hyrox/HYROX, TONS/Tons, Mash/MASH -
  lidt mere udfordrende end WOD, Lang WOD/WOD (Laaang workout), Rengøring -
  begrænset/Begrænset.
- De **29 aktive aktiviteter dækker 10 typer**; alle 39 (+1) fordeler sig
  på 12 (inkl. "ukendt" og "test").

**Foreslåede holdtyper** (farve/kapacitet = hyppigste værdi på holdene):

| id | Navn | Farve | Std. kap. | Aktiviteter (alle/aktive) | Hold i vinduet | Faste tider |
|---|---|---|---|---|---|---|
| `wod` | WOD | 9ccc65 | 12 | 19 / 17 | 173 | 17 (se afsnit 5) |
| `wod_uden_traener` | WOD uden træner | aed581 / 8bc34a (lige mange) | 12 | 3 / 2 | 21 | Man 06:00, Ons 06:00 |
| `lang_wod` | Lang WOD | 66bb6a | 12 | 2 / 1 | 10 | Søn 09:00 |
| `hyrox` | HYROX | 039be5 | 12 | 2 / 2 | 19 | Ons 17:00, Lør 10:00 |
| `tons` | TONS | bdbdbd | 12 | 3 / 1 | 10 | Tir 17:45 |
| `mash` | MASH | cfd8dc | 12 | 2 / 1 | 9 | Fre 16:30 |
| `basis` | Basis/teknik | ffd54f | 8 | 1 / 1 | 10 | Tor 18:00 |
| `boernehold` | Børnehold 5-12 år | fce4ec | 12 | 1 / 1 | 10 | Søn 10:45 |
| `rengoering` | Rengøring (ingen tilmelding) | f8bbd0 | 0 (intet loft) | 4 / 2 | 23 | Ons 18:30, Søn 13:00 |
| `ungeenhed` | Ungeenheden (ekstern, ingen tilmelding) | ab47bc | 0 | 1 / 1 | 12 | Tor 09:30 |
| `ukendt_opstart` | Ukendt engangs-aktivitet | 8bc34a | 12 | 1 / 0 | 6 | - |
| `test` | Test (slet) | 9c27b0 | 1 | 1 / 0 | 0 | - |

Mapping aktivitet → type står i tabellen i afsnit 2 og i
`holdtyper.json` → `mapping`.

**Usikre mappinger (ikke gættet - skal afklares med en admin):**

- *WOD Mandag 0600 / WOD Onsdag 0600*: aktivitetsnavnet siger WOD, 8/10 hold
  hedder "WOD uden træner", men 17 hold med "uden træner" i navnet har en
  navngiven ansvarlig (Johan Berlin Christophersen 8, Mick Nielsen 9 på 06-holdene).
  Er det "WOD uden træner" med en nøgleansvarlig, eller almindelig WOD?
- *WOD Onsdag 0600 11/11*: "WOD med gæste træner" - engangsvariant.
- *MIKKO - uden træner*: maskine-intervaller; kan være egen type.
- *To hvilende "WOD"* (mandag + Klippekort-tag): formentlig gamle kl. 06-hold.
- *Aktivitet …140362*: findes ikke i `/api/activity`; 6 hold 25.-27/9 kaldet
  WOD/MASH/LANG WOD. Ligner en opstartsweekend; kan være slettet eller skjult.
- *MASH vs TONS*: begge beskrives som "for folk som ser crossfit som en
  sport"; måske én type "Øvede". Holdt adskilt her.

## 4. Tags (51)

| Gruppe | Antal | Tags |
|---|---|---|
| Ugedag (kategori TC…9731) | 7 | mandag … søndag |
| Medlemskab/produkt | 9 | Premium medlemskab, Ung 15-24 år medlemskab, Klippekort (10 klip), Børnemedlemsskab 7-14, Fordels medlemskab, 6 måneder, 12 måneder, PT klippekort, Studerende |
| System/rolle | 4 | Alle medlemmer (Tag2), Administrator (Tag1), Trænere, Bestyrelsesmedlem |
| Intern status/administration | 28 | Pause, Ønsker udmelding, Rykker, Manglende fremmøde, Bero gebyr, 11× "Udmeld slut <måned>", 12× "Bero slut <måned>" |
| Andet | 3 | Sponsorat 15000 kr, Sponsorat 10000 kr., Oprettelse |

`tagType` 1 bruges på de 23 "Udmeld/Bero slut"-tags (kategori TC…8777),
resten er 0. "Udmeld slut sep" mangler i rækken. "Oprettelse" og
"Studerende" er placeret efter navn - deres funktion kan ikke ses i data.

**Tags på hold.** Kun 10 tags bruges på hold: Alle medlemmer (213 hold),
de 7 ugedage, Premium og Klippekort (kun Basis/teknik, 10 hold).

| Kombination på holdet | Hold |
|---|---|
| (ingen tags) | 90 |
| Alle medlemmer | 49 |
| Alle medlemmer + ugedag | 154 (man 30, ons 30, fre 25, tir 21, tor 20, lør 18, søn 10) |
| Alle medlemmer + Premium + Klippekort | 10 (Basis/teknik) |

- Ugedags-tags passer altid med holdets ugedag når de er sat (154), men 149
  hold har ingen ugedags-tag. Holdene oprettet de seneste år (fx Mandag
  16/17, Tirsdag 08:15, Torsdag 19:00, HYROX, Lang WOD, MASH) har ingen. De
  ser ud til at være et levn fra 2020 (oprettet 25/10 2020).
- Uden tags: Rengøring, Ungeenhed, TONS, Børnehold, Hyrox (lør), WOD Tir 08:15,
  WOD Tor 19:00 og september-holdene. Om "ingen tags" betyder "alle må se/booke"
  eller "ingen" kan ikke afgøres anonymt - holdene vises i den offentlige plan
  og har tilmeldte.
- **Hvad tags gater:** Basis/teknik er det eneste hold med medlemskabs-tags
  (Premium + Klippekort) ud over "Alle medlemmer". Da "Alle medlemmer" også
  er sat, er det uklart om de ekstra tags begrænser noget. Klip trækkes via
  prisreglen (tag Klippekort → 1 klip pr. online-tilmelding), ikke via
  holdets tags.
- `product.json`: Ung 15-24 og Børnemedlemskab har `tagRequired =
  Tag2516349743327791001`, som ikke findes blandt de 51 tags (skjult tag?).

## 5. Ugerytme

Grundlag: 259 hold i 9 hele uger (2/11 2026 - 3/1 2027).

| Tid | Man | Tir | Ons | Tor | Fre | Lør | Søn |
|---|---|---|---|---|---|---|---|
| 06:00 | WOD uden træner | | WOD uden træner | | | | |
| 08:00 | | | | | | WOD | WOD |
| 08:15 | WOD | WOD | WOD | WOD | WOD | | |
| 09:00 | | | | | | WOD | Lang WOD (-10:30) |
| 09:30 | | | | Ungeenhed (-11:00) | | | |
| 10:00 | | | | | | HYROX | |
| 10:45 | | | | | | | Børnehold |
| 13:00 | | | | | | | Rengøring (-15:30) |
| 15:30 | | | | | WOD | | |
| 16:00 | WOD | | WOD | | | | |
| 16:30 | | WOD | | WOD | MASH (-18:00) | | |
| 17:00 | WOD | | HYROX | | | | |
| 17:45 | | TONS (-19:00) | | | | | |
| 18:00 | | | | Basis/teknik | | | |
| 18:30 | | | Rengøring (-21:00) | | | | |
| 19:00 | | WOD | | WOD | | | |
| 19:45 | WOD | | | | | | |

29 faste tider; alle findes 9 af 9 uger, undtagen Fredag 15:30 WOD og Fredag
16:30 MASH, som først starter 13/11 (8/9). Ingen huller mellem første og
sidste forekomst af en fast tid. Hold varer 60 min, undtagen TONS 75, Lang
WOD og MASH 90, rengøring 150, ungeenhed 90.

**Afvigelser**

- *Status (alle 303):* scheduled 286, booked (fuldt) 12, cancelled 5. Alle 12
  "booked" har tilmeldte ≥ pladser; ingen "scheduled" er fulde.
- *Aflyste (5):* 1/11 Børnehold ("bero indtil gymmet er klar"), 2/11 WOD
  Mandag 1945 ("Aflyst"), 7/11 Hyrox ("kun 1 tilmeldt"), 12/11 WOD Tor 19:00
  ("Aflyst grundet manglende tilmelding"), 15/11 Børnehold ("Mangel på
  tilmeldte").
- *Helligdage:* ikke håndteret i planen. Juleaften 5 hold, 1. juledag 3,
  2. juledag 3, nytårsaften 5, nytårsdag 3 - alle "scheduled".
- *Engangsvarianter* (navn/beskrivelse sat på holdet): "WOD med gæste træner"
  (Ons 06:00 11/11), "WOD hold"/"Coach Mathias" (Tir 08:15 10/11), "2-personers
  MAKKER" (5/11), "VIKAR:" (12/11), "3-Personers MAKKER" (26/11).
- *Kapacitet ændret på enkelte hold:* WOD Fredag 0815 14 (2/10, 9/10), WOD Søndag
  0800 15 (1/11), Lang WOD 16 (8/11), HYROX 16 (11/11).
- *Før 1/11:* kun 18 hold (6 WOD, 6 på den ukendte aktivitet, 3 rengøring, 2
  ungeenhed, 1 "WOD uden træner"). Aflysningsteksten "bero indtil gymmet er
  klar" og datoerne tyder på en opstart i november, men det kan ikke bekræftes
  ud fra data.

## 6. Belastning

**Hvilke hold er talt med.** Kun hold der er afholdt i perioden med fuld
holdplan (1/11 til snapshot 14/11 20:37): 56 hold, heraf **46 brugt**.
Udeladt: 18 hold før 1/11 (ufuldstændig plan), 4 aflyste, 6 uden pladsloft
(rengøring/ungeenhed) og 229 fremtidige. Begrundelse for at udelade
fremtidige: gennemsnitlig fyldning falder med afstanden - afholdte 66,3 %,
0-7 dage frem 44,7 %, 8-14 dage 14,7 %, 15-28 dage 2,6 %, 29+ dage 0,5 %
(snit af fyldning pr. hold). Tallene bygger på 2 uger - de er en
stikprøve, ikke et gennemsnit over tid.

| Type | Hold | Pladser | Tilmeldte | Fyldning | Fuldt booket | Venteliste | Snit tilmeldte |
|---|---|---|---|---|---|---|---|
| WOD | 31 | 375 | 261 | 69,6 % | 5 | 0 | 8,4 |
| WOD uden træner | 4 | 48 | 24 | 50,0 % | 0 | 0 | 6,0 |
| Lang WOD | 2 | 28 | 21 | 75,0 % | 1 | 0 | 10,5 |
| HYROX | 3 | 40 | 29 | 72,5 % | 0 | 0 | 9,7 |
| TONS | 2 | 24 | 12 | 50,0 % | 0 | 0 | 6,0 |
| MASH | 1 | 12 | 7 | 58,3 % | 0 | 0 | 7,0 |
| Basis/teknik | 2 | 16 | 14 | 87,5 % | 1 | 0 | 7,0 |
| Børnehold | 1 | 12 | 1 | 8,3 % | 0 | 0 | 1,0 |
| **I alt** | **46** | **555** | **369** | **66,5 %** | **7** | **0** | **8,0** |

Venteliste-tallet er 0 på alle afholdte hold - også de fulde. Om det er fordi
ventelisten tømmes når holdet er afholdt, eller fordi ingen stod på den, kan
ikke afgøres.

**Pr. fast tid (afholdte hold):**

| Tid | Type | Hold | Tilm./pladser | Fyldning | Fulde | Enkelte hold |
|---|---|---|---|---|---|---|
| Man 06:00 | WOD uden træner | 2 | 11/24 | 45,8 % | 0 | 5/12, 6/12 |
| Man 08:15 | WOD | 2 | 18/24 | 75,0 % | 0 | 8/12, 10/12 |
| Man 16:00 | WOD | 2 | 19/24 | 79,2 % | 0 | 9/12, 10/12 |
| Man 17:00 | WOD | 2 | 19/24 | 79,2 % | 1 | 7/12, 12/12 |
| Man 19:45 | WOD | 1 | 5/12 | 41,7 % | 0 | 5/12 (2/11 aflyst) |
| Tir 08:15 | WOD | 2 | 14/24 | 58,3 % | 0 | 7/12, 7/12 |
| Tir 16:30 | WOD | 2 | 18/24 | 75,0 % | 0 | 8/12, 10/12 |
| Tir 17:45 | TONS | 2 | 12/24 | 50,0 % | 0 | 7/12, 5/12 |
| Tir 19:00 | WOD | 2 | 7/24 | 29,2 % | 0 | 3/12, 4/12 |
| Ons 06:00 | WOD uden træner | 2 | 13/24 | 54,2 % | 0 | 6/12, 7/12 |
| Ons 08:15 | WOD | 2 | 20/24 | 83,3 % | 1 | 12/12, 8/12 |
| Ons 16:00 | WOD | 2 | 24/24 | 100,0 % | 1 | 9/12, 15/12 |
| Ons 17:00 | HYROX | 2 | 23/28 | 82,1 % | 0 | 8/12, 15/16 |
| Tor 08:15 | WOD | 2 | 12/24 | 50,0 % | 0 | 9/12, 3/12 |
| Tor 16:30 | WOD | 2 | 24/24 | 100,0 % | 2 | 12/12, 12/12 |
| Tor 18:00 | Basis/teknik | 2 | 14/16 | 87,5 % | 1 | 8/8, 6/8 |
| Tor 19:00 | WOD | 1 | 3/12 | 25,0 % | 0 | 3/12 (12/11 aflyst) |
| Fre 08:15 | WOD | 2 | 18/24 | 75,0 % | 0 | 7/12, 11/12 |
| Fre 15:30 | WOD | 1 | 11/12 | 91,7 % | 0 | 11/12 |
| Fre 16:30 | MASH | 1 | 7/12 | 58,3 % | 0 | 7/12 |
| Lør 08:00 | WOD | 2 | 13/24 | 54,2 % | 0 | 5/12, 8/12 |
| Lør 09:00 | WOD | 2 | 13/24 | 54,2 % | 0 | 8/12, 5/12 |
| Lør 10:00 | HYROX | 1 | 6/12 | 50,0 % | 0 | 6/12 (7/11 aflyst) |
| Søn 08:00 | WOD | 2 | 23/27 | 85,2 % | 0 | 12/15, 11/12 |
| Søn 09:00 | Lang WOD | 2 | 21/28 | 75,0 % | 1 | 5/12, 16/16 |
| Søn 10:45 | Børnehold | 1 | 1/12 | 8,3 % | 0 | 1/12 (1/11 aflyst) |

Bemærk: Ons 16:00 11/11 har 15 tilmeldte på 12 pladser - "100 %" er her
summen 24/24, ikke at holdet var præcis fuldt.

Pr. ugedag: man 72/108 (66,7 %), tir 51/96 (53,1 %), ons 80/100 (80,0 %),
tor 53/76 (69,7 %), fre 36/48 (75,0 %), lør 32/60 (53,3 %), søn 45/67
(67,2 %). Pr. tid på dagen: morgen (<10) 176/271 = 64,9 % (22 hold),
formiddag (10-15) 7/24 = 29,2 % (2 hold), eftermiddag/aften (≥15) 186/260 =
71,5 % (22 hold).

Forhåndsbooking næste 7 dage (25 hold, ikke færdige): Basis/teknik 8/8
(100 %), Lang WOD 7/12, WOD 99/204 (48,5 %), WOD uden træner 10/24, HYROX
5/24, TONS 1/12, MASH 0/12.

Kontrol: hele november (alle hold med loft, inkl. aflyste og fremtidige) giver
542/1315 - samme som `RAPPORT.md`.

## 7. Trænere

16 navngivne trænere (kun hold med egen record viser navn):

| Træner | Hold | Fordeling |
|---|---|---|
| Mick Nielsen | 15 | WOD uden træner 9, WOD 4, Lang WOD 1, ukendt 1 |
| Jeppe Rasmussen | 11 | WOD 8, ukendt 2, TONS 1 |
| Silja Andersen | 10 | Basis/teknik 8, WOD 2 |
| Sebastian Meier | 10 | WOD 10 |
| Peter Alexander Schougaard | 8 | WOD 4, ukendt 2, Lang WOD 1, HYROX 1 |
| Johan Berlin Christophersen | 8 | WOD uden træner 8 |
| Thomas Ronne | 6 | WOD 3, WOD uden træner 1, MASH 1, ukendt 1 |
| Christian Gøtzsche | 5 | WOD 5 |
| Ivan Munch Petersen | 5 | WOD 5 |
| Mia Foldager | 3 | WOD 3 |
| Sussi Larsen | 2 | WOD 2 |
| Helena Levin Erting | 2 | WOD 2 |
| Christoffer Hviid | 2 | HYROX 2 |
| Maj Jeppesen | 1 | Børnehold 1 |
| Mia Bertram | 1 | Børnehold 1 |
| Mathias Wachenschwanz | 1 | WOD 1 |

**Hold uden navngiven træner: 214 af 303** (196 af 229 fremtidige). Det
betyder *ikke* at holdene mangler træner: alle 214 har præcis så mange
ansvarlige som aktivitetens standard (`responsibleUsersIds`), men navnet
vises ikke anonymt. Hvem standard-ansvarlig er, kræver login.

| Type | med navn | uden navn |
|---|---|---|
| WOD | 49 | 124 |
| WOD uden træner | 18 | 3 |
| Lang WOD | 2 | 8 |
| HYROX | 3 | 16 |
| TONS | 1 | 9 |
| MASH | 1 | 8 |
| Basis/teknik | 8 | 2 |
| Børnehold | 1 | 9 |
| Rengøring | 0 | 23 |
| Ungeenhed | 0 | 12 |
| Ukendt (sep.) | 6 | 0 |

18 hold har 2 ansvarlige (Hyrox lørdag og Børnehold, som har 2 som standard).

## 8. Problemer for frivillige - konkrete fund

1. **Én aktivitet pr. fast tid.** WOD er 17 aktive aktiviteter; i alt 39
   aktiviteter for 10 reelle typer. En ændring for "alle WOD" skal laves 17
   gange, og der er ingen samlet "WOD"-indstilling.
2. **Tre niveauer af indstillinger** (aktivitet → serie → hold). Venteliste
   afviger fra aktiviteten på 132/214 genererede hold og fremmøde på 121/214 -
   uden at nogen har rettet i det enkelte hold. Venteliste skifter fra hold
   til hold på 18 og fremmøde på 23 af 29 aktive aktiviteter. Ingen kan se
   hvad der gælder uden at åbne hvert hold.
3. **Navne siger noget andet end indholdet.** "WOD" ×6; aktiviteten "WOD"
   hedder "WOD Mandag 1600/1700" på holdene; "WOD Mandag/Onsdag 0600" hedder
   "WOD uden træner" på 16 hold, men 17 "uden træner"-hold har en navngiven
   ansvarlig. Forskellig stavemåde: Hyrox/HYROX, TONS/Tons, Mash/MASH.
4. **Søskende med forskellige indstillinger.** De to HYROX-hold: lørdag har
   ingen tags, 2 ansvarlige og ingen prisregel; onsdag har "Alle medlemmer"
   og 1 ansvarlig. WOD Tor 19:00 har farven 4caf50 på aktiviteten men 81c784 på
   alle sine hold; resten af WOD er 9ccc65. WOD uden træner har to farver
   (aed581/8bc34a). Farvekoder i blandet format (`#8bc34a` 14 hold,
   `#aed581` 8, `#9ccc65` 10, `FFD54F` …).
5. **Trænere er usynlige** på 196 af 229 kommende hold (kun standard-ansvarlig
   uden navn) - man kan ikke se en ugeplan med trænere uden at åbne holdene.
6. **Kapacitet rettet pr. hold** (14, 15, 16 i stedet for 12) og ét hold
   med 15 tilmeldte på 12 pladser (Ons 16:00 11/11).
7. **Tags gør mange ting:** medlemstyper, ugedage (kun på halvdelen af
   holdene: 154 med / 149 uden), interne påmindelser (28 status-tags med
   måneder; "Udmeld slut sep" mangler) og adgang til hold - samme liste.
   Et produkt peger på et tag der ikke er i listen.
8. **Oprydning mangler:** 9 hvilende aktiviteter (bl.a. 2 × "WOD", "Tons",
   "TONS", "Mash", "Test booking" fra 2020) og en aktivitet med hold som ikke
   findes i aktivitetslisten.
9. **Helligdage** er ikke lagt ind: 19 hold står som normalt 24/12-1/1.
10. **Tekniske uregelmæssigheder** en frontend skal tåle: eventId ≠ starttid
    (16 hold), `createdTs` uden tidszone på alle 39 aktiviteter mens
    `modifiedTs` har 'Z', `signUpDeadline` mangler på 227 hold, og den anonyme
    holdplan viser forkert prisinfo (activityHasPrice/paymentRules) i forhold
    til detaljekaldet.

## 9. Hvad en admin-frontend skal kunne ændre - og hvor i goMember

*Kun dokumentation. Integrationen må ikke skrive (se `CLAUDE.md`); intet
herunder er kaldt eller afprøvet.* Alle stier/verber er kontrolleret til at
findes i `SGSwagger.json`. `ActivityEventCommand.update` og `DELETE …?update=`
har værdierne `current` / `allFromCurrent` / `allFuture` - dvs. goMember
understøtter "kun dette hold" vs. "dette og fremtidige".

| Redigering | goMember-entitet / felter | Skrive-endpoint i swagger |
|---|---|---|
| Skift træner på ét hold | Hold: `responsible[]`, `update=current` | `PUT /api/activity/{activityId}/event/{id}` (EventApi_Put); `PUT /api/event/v3/{id}` |
| Skift fast træner for en tid fremover | Serie: `responsible[]`, `update=allFromCurrent`/`allFuture` | `PUT /api/activity/{activityId}/event/{id}` |
| Aflys ét hold (besked + evt. refusion) | Hold: `cancellationMessage`, `refund`, `updateLevel`, `media` | `POST /api/activity/{activityId}/event/{eventId}/cancelevent` |
| Slet hold / resten af serien | Hold/serie, `?update=` | `DELETE /api/activity/{activityId}/event/{id}`; `DELETE /api/event/v3/{id}`; `DELETE /api/event/{id}` |
| Ændr kapacitet / venteliste | Hold/serie: `maxAttendees`, `hasWaitingList` | `PUT /api/activity/{activityId}/event/{id}` |
| Flyt tidspunkt | Hold/serie: `startTime`, `endTime`, `meetTime`, `signUpDeadline` (om eventId ændres er uafklaret) | `PUT /api/activity/{activityId}/event/{id}`; `PUT /api/event/v3/{id}` |
| Ændr navn/beskrivelse/farve | Hold/serie: `name`, `description`, `color` | `PUT /api/activity/{activityId}/event/{id}` |
| Ændr hvem der må se/booke | Hold/serie: `tagsAssigned`; v3: `allowedToBook`, `allowedToSee` | `PUT /api/activity/{activityId}/event/{id}`; `PUT /api/event/v3/{id}` |
| Opret engangshold | Hold (EventCreateSingleCommand) | `POST /api/event/v3/single`; `POST /api/activity/{activityId}/event` |
| Opret fast ugentligt hold (serie) | Serie: `when.schedules[]` (`weekdays`, `fromTime`, `duration`, `weekInterval`, `scheduleStart/End`) | `POST /api/event/v3/recurring` |
| Forlæng serie | Serie (RecurringWhenInfo) | `POST /api/event/v3/{eventId}/recurring` |
| Opret/ændr holdtype | Aktivitet (ActivityDto: navn, farve, `maxAttendees`, `hasWaitingList`, `tagsAssigned`, `responsibleUsersIds`) | `POST /api/activity`; `PUT /api/activity/{id}` |
| Slet hvilende aktivitet | Aktivitet | `DELETE /api/activity/{id}`; `POST /api/activitydata/delete` |
| Ændr klip/udeblivelsesgebyr | Pris (`perOnlineSignup`, `noShow`) | `PUT /api/activity/{activityId}/event/{eventId}/price`; `PUT /api/price/{id}`; `PUT /api/pricedata/activity/{actType}/{id}` |
| Tilmeld/afmeld medlem (admin) | Booking | `POST /api/activity/{activityId}/event/{eventId}/adminbooking`; `DELETE /api/activity/{activityId}/event/{eventId}/bookings/{id}` |
| Registrér fremmøde | Booking | `POST /api/booking/{id}/attend`; `POST /api/activity/{activityId}/member/{memberId}` |
| Send besked til holdet | Hold | `POST /api/activity/{activityId}/event/{eventId}/v2/sendinvitation` |
| Opret/omdøb tag | Tag | `POST /api/tag`; `PUT /api/tag` |
| Masseændring/klon af aktivitet | Aktivitet (body uden schema) | `PUT /api/activitydata/batchupdate/{id}`; `PUT /api/activitydata/clone/{id}` - samme stier står i `DENIED_PATHS` som GET |

"Luk for jul" og "ændr alle WOD" findes ikke som ét kald: det er en løkke over
hold (aflys) eller aktiviteter/serier (PUT) - frontendens opgave.

## Ikke afklaret / ikke verificeret

- Om "uden træner"-holdenes navngivne ansvarlige er træner eller bare
  nøgleansvarlig.
- Hvem standard-ansvarlig er på de 214 genererede hold (kræver login).
- Om tags på holdet begrænser hvem der kan booke, og hvad "ingen tags" betyder.
- Hvad ugedags-tags, "Oprettelse", "Studerende" og det manglende
  `Tag2516349743327791001` bruges til.
- Prisregler er kun hentet for 3 af 39 aktiviteter.
- Hvorfor TONS' eventId er 60 min forskudt, og om flytning af et hold ændrer eventId.
- Aktivitet …140362 (sep.) - hvorfor den mangler i `/api/activity`.
- Om venteliste-tallet nulstilles efter holdet er afholdt.
- Belastning bygger på 2 uger; ingen historik før 1/11 i data.
- Hvordan skrive-endpoints faktisk opfører sig (felter, `update`-niveauer) er
  kun læst i swagger, ikke afprøvet.
