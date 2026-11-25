# Styring: forslag til en ny admin-skærm for Strong Gym

*Status: fungerende prototype. Intet er sendt til goMember, og intet i
goMember er ændret eller slettet.*

Filer: `styring.html` (siden), `styring-data.json` (data),
`gomember-mcp/kortlaegning/byg_styringsdata.py` (bygger data),
`styring-statistik.json` (deltagelsesstatistik, bygget af
`gomember-mcp/kortlaegning/byg_statistikdata.py`).

---

## Til bestyrelsen: kort fortalt

**Hvad er det?** En ny skærm, der viser vores hold, som vi selv tænker
på dem: **10 holdtyper** og en **ugeplan**. I goMember er de samme hold
spredt ud på 39 "aktiviteter", fordi hvert fast tidspunkt er oprettet for
sig (WOD alene 17 gange). Det gør det svært at få overblik og nemt at
glemme noget.

**Hvad kan man i dag?**

- **Overblik** (åbner som standard): det, bestyrelsen skal bruge på
  bestyrelsesmødet, på én side der kan udskrives. Medlemmer pr. medlemskab, nye
  medlemmer og udmeldinger pr. måned de seneste 12 måneder, fyldning pr.
  holdtype og pr. måned, og en liste over faste hold, hvor under 50 % af
  pladserne bliver brugt. Fyldning er tilmeldte i forhold til pladser, ikke
  fremmøde. Økonomien har en tom plads, indtil den kobles på fra
  bestyrelsens egen side (`/bestyrelse/` på branchen `bestyrelse-okonomi`).
- **Bestyrelse**: næste bestyrelsesmøde og møder pr. dato med dagsorden og
  referat, der kan hentes som Word eller PDF. Opgavelisten (afkrydsning) er
  bygget, men skjult indtil videre: `VIS_OPGAVER = false` i `styring.html`.
  Opgaverne ligger stadig i databasen og bruges til opfølgningen (punkt 3)
  på næste dagsorden.
  Fanen findes KUN på bestyrelsessiden på Cloudflare (bag login); på
  claude.ai-udgaven er den skjult, og dens database er slået fra. Data ligger
  i Cloudflare D1 (tabellerne `meetings` og `tasks`), aldrig i repoet:
  referater kan rumme personsager.
  Nye dagsordener og referater laves med bestyrelses-skabelonen og lægges ind
  af Claude; opgaverne fra referatets handlingsliste oprettes med samme ID.
- **Drift**: ugens nøgletal (antal hold, tilmeldte i forhold til pladser,
  fuldt bookede, hold uden synlig træner, aflyste) og en liste over det,
  der kræver opmærksomhed. Det kan være juleaften og nytårsdag, hvor alle hold
  stadig står som normalt, overbookede hold, faste tider med meget få
  tilmeldte, og holdtyper hvor indstillingerne ikke er ens.
- **Uge**-fanen (ugeplanen) er fjernet 15. nov. 2026 – bestyrelsen brugte
  den ikke, og holdplanen findes allerede på hjemmesiden. Enkelte hold kan
  stadig åbnes og rettes fra Drift.
- **Holdtyper:** de 10 typer, deres faste tider, hvor mange
  goMember-aktiviteter der ligger bag, og hvor indstillingerne er forskellige.
  Med én knap kan man rette noget for alle hold af en type.
- **Statistik:** hvor mange der har været tilmeldt, på hvilke hold og på
  hvilke dage de sidste 6 måneder (14. maj – 14. nov. 2026): nøgletal,
  pr. ugedag, et varmekort over ugedag × tidspunkt, pr. holdtype, holdtype ×
  dag, udvikling pr. måned og uge, og de mest og mindst fyldte faste hold.
  Tallene er **tilmeldte, ikke fremmødte**, fordi fremmøde næsten ikke er
  registreret siden flytningen i oktober. Kun samlede antal - ingen navne
  og ingen tal pr. træner.
- **Rettelser (kladde):** alle rettelser samles i en liste: skift træner,
  aflys, ændr pladser, flyt tid, venteliste til/fra, fremmøde til/fra og
  omdøb. Gælder for ét hold, for dette og de fremtidige hold på samme tid
  eller for alle hold af typen. Listen kan hentes som fil eller kopieres som
  **tjekliste**, så en frivillig kan udføre rettelserne i goMember i dag.

**Hvad kan den ikke endnu?**

- Den **sender ikke noget til goMember.** Hver rettelse er en kladde.
  Øverst på siden står hele tiden "Kladde — intet er sendt til goMember".
- Medlemmer viser kun **samlede tal** (antal pr. etiket, nye pr. måned,
  bero/udmeld-etiketter og udmeldinger efter udmeldingsdato). Ingen navne,
  numre eller data om enkeltpersoner. No-shows vises ikke.
- Dataene er et **øjebliksbillede** fra det tidspunkt, de sidst blev hentet
  (står øverst på siden). Siden regner den dato som "i dag". De kan opdateres
  automatisk hver nat med én kommando (se "Automatisk opdatering").
- Kladden ligger kun i den browser, den er lavet i. Den deles ikke mellem
  personer.
- Det er ikke muligt at slette hold eller aktiviteter. Det skal heller ikke
  være muligt foreløbig.

**Det skal bestyrelsen beslutte**

1. Skal vi bruge prototypen som den er: frivillige laver rettelser i
   kladden og udfører dem manuelt i goMember ud fra tjeklisten?
2. Skal vi sætte det skrivebeskyttede login op, så siden kan vise
   medlemstal? I så fald: hvem må se dem, og hvordan beskytter vi siden?
   (Se "Adgangskontrol" nedenfor.)
3. Skal vi, på et senere tidspunkt, lade skærmen **sende** rettelser til
   goMember? Det er en bevidst og separat beslutning med egne krav (se
   afsnit 4). Det sker ikke af sig selv.
4. Oprydning i goMember: skal de 9 hvilende aktiviteter fjernes, og skal
   ugedags-etiketterne bruges konsekvent eller droppes? Det udføres i
   goMember af en administrator, ikke af denne skærm.
5. Hvem er "uden træner"-holdene kl. 06 ansvarlige for: en træner eller en
   nøgleansvarlig?

---

## 1. Sådan kører man den

```
python3 gomember-mcp/kortlaegning/byg_styringsdata.py   # bygger styring-data.json (offline)
python3 gomember-mcp/kortlaegning/byg_statistikdata.py   # bygger styring-statistik.json (offline)
python3 -m http.server 8000                               # i repo-roden
# åbn http://localhost:8000/styring.html
```

Siden er én fil uden byggetrin og uden eksterne JavaScript-biblioteker.
Skrifttyperne hentes fra Google Fonts som på hjemmesiden. Siden har
`noindex`, og der er ingen link til den fra `index.html`.

**Netværk:** siden laver præcis tre datakald: `GET styring-data.json`,
`GET styring-medlemmer.json` (samlede medlemstal, bygget af
`gomember-mcp/kortlaegning/byg_medlemsstatistik.py`; mangler filen, viser
Medlemmer "afventer login") og `GET styring-statistik.json` (mangler filen,
viser Statistik "Statistikken er ikke bygget endnu"; resten af siden
virker).
Den indeholder ingen anden `fetch`, `XMLHttpRequest`, `sendBeacon` eller
formular-afsendelse. Rettelser gemmes i `localStorage` (siden virker også
uden). Eksport som JSON sker med en lokal download i browseren.

**Aktive og udmeldte:** Udmeldte medlemmer slettes ikke i goMember. De står
som "ikke aktive" (25 pr. 19. nov. 2026). Medlemstal og antal pr. medlemskab
tæller derfor kun **aktive** medlemmer; nye pr. måned tæller alle, også dem
der er udmeldt siden.

**Udmeldinger efter udmeldingsdato** (Medlemmer → Opfølgning): for alle
udmeldte (ikke aktive) og for aktive med etiketten "Ønsker udmelding" hentes
feltet "Udmeldingsdato" (og indmeldingsdatoen) fra deres medlemskort i
goMember, `GET /api/memberdata/{id}` – ét kald pr. medlem, ca. 27. Svaret er medlemmets
fulde stamkort (navn, adresse, e-mail, telefon …). Scriptet læser **kun**
felterne `LeftDate` og `JoinedDate` og smider resten væk med det samme. Intet
id, ingen dato og intet andet fra svaret gemmes eller skrives ud – kun:
antal udmeldte og aktive med etiketten, med/uden dato, allerede passeret/kommende, antal pr.
måned og medlemstid i grove grupper. Antal pr. måned vises præcist, også 1
og 2 (klubben har godkendt samlede tal uden navne; ellers ville grafen være
tom), men kun som måned, aldrig som dato. Medlemstid vises kun for hele
gruppen, med "<3" for 1-2.

**Statistik opdateres** i to trin i `gomember-mcp/kortlaegning`:

1. `python3 deltagelse.py` henter deltagelsen fra goMember (kun læsekald,
   med cache) og skriver `deltagelse.json`. `--offline` bruger kun cachen.
   Perioden er de seneste 6 måneder til i dag (`--dato ÅÅÅÅ-MM-DD` for en
   anden dato, `--plan` tæller kun hvor mange kald en kørsel ville bruge).
2. `python3 byg_statistikdata.py` regner tallene forfra ud fra holdene i
   `deltagelse.json`, kontrollerer dem mod summerne i samme fil og skriver
   `styring-statistik.json` (ca. 19 KB). Stemmer noget ikke, eller har tallene
   flyttet sig mere end 30 % siden forrige fil, stopper den med en fejl og
   skriver ingen fil (`--force` tillader et stort spring).

Regler og forbehold for tallene står i `gomember-mcp/kortlaegning/DELTAGELSE.md`
og i fanen under "Sådan er tallene lavet".

### Automatisk opdatering

Alle tre datafiler opdateres med én kommando, der er lavet til at køre af sig
selv hver nat (fx fra cron på en maskine med login-oplysningerne sat):

```
python3 gomember-mcp/kortlaegning/opdater.py          # "i dag" = dags dato (dansk tid)
python3 gomember-mcp/kortlaegning/opdater.py --dato 2026-11-15   # kun til test
```

**Hvad den henter** (kun læsning, alt gennem `GoMemberClient.get()`):

1. Holdplanen 8 uger tilbage og 8 uger frem, aktivitetslisten, etiketterne og
   medlemskaberne (ca. 8 kald, `holdplan.py`). Den store kortlægning
   (`kortlaeg.py`, ca. 100 adresser i goMember) køres ikke om natten.
2. Medlemslisten, talt op til antal med det samme (alle, aktive og ikke
   aktive: 3 kald + etiketterne), og udmeldingsdatoen for udmeldte og aktive
   med "Ønsker udmelding" (ca. 27 kald til `/api/memberdata/{id}`, hvor kun
   udmeldings- og indmeldingsdato læses; se "Udmeldinger" ovenfor).
3. Deltagelsen de seneste 6 måneder. Gamle hold ligger gemt i en cache og
   hentes aldrig igen. Kun hold fra de seneste 14 dage, nye hold og hold der
   lå i fremtiden sidst, hentes igen. En normal nat er ca. 50-60 kald; i alt
   ca. 85 kald og omkring et minut.

Derefter regnes `styring-data.json`, `styring-medlemmer.json` og
`styring-statistik.json` ud uden at kontakte goMember.

**Sikkerhed og kontroller:**

- Alt bygges først i en midlertidig mappe. Filerne skiftes kun ud, hvis
  **alle** trin og kontroller er gået igennem. Ellers røres intet, der skrives
  en kort dansk forklaring, og kommandoen slutter med fejlkode 1.
- Højst 2 kald i sekundet, 30 sekunders ventetid, højst 2 nye forsøg ved
  fejl hos goMember, og et loft på 600 kald pr. kørsel. Et login, der fejler,
  prøves ikke igen (så kontoen ikke bliver låst).
- Kontroller: der skal være hold de næste 7 dage; antal medlemmer må højst
  ændre sig 25 % og antal afholdte hold/tilmeldinger højst 30 % i forhold til
  forrige fil (`--force` tillader det); alle summer i statistikken skal passe
  sammen; tal på 1-2 vises stadig som "<3". Udmeldingsdato: trinnet fejler,
  hvis ingen har etiketten, hvis filteret på etiketten ikke giver præcis
  lige så mange som medlemslisten, hvis over 20 % af medlemskortene ikke kan
  hentes, eller hvis feltet `LeftDate` er forsvundet fra kortet.
- En ny aktivitet, som holdtype-opdelingen ikke kender, stopper ikke
  kørslen. Den vises som "Ukendt (ny aktivitet)" og nævnes i opsummeringen,
  så nogen kan placere den i `analyse_holdtyper.py`.
- Ingen navne, medlemsnumre, tokens eller adgangskoder skrives ud.
  Trænernavne på holdene er offentlige og gemmes kun som navn.

## 2. Fra 39 aktiviteter til 10 holdtyper

Mappingen kommer fra kortlægningen (`HOLDTYPER.md`, `holdtyper.json` →
`mapping`) og ændres ikke af prototypen.

| Holdtype | Aktiviteter (aktive / i alt) | Faste tider pr. uge |
|---|---|---|
| WOD | 17 / 19 | 17 |
| WOD uden træner | 2 / 3 | 2 (man. og ons. kl. 06) |
| Lang WOD | 1 / 2 | 1 |
| HYROX | 2 / 2 | 2 |
| TONS | 1 / 3 | 1 |
| MASH | 1 / 2 | 1 |
| Basis/teknik | 1 / 1 | 1 |
| Børnehold 5-12 år | 1 / 1 | 1 |
| Rengøring | 2 / 4 | 2 |
| Ungeenheden (ekstern) | 1 / 1 | 1 |

Derudover findes to typer, som ikke vises: "ukendt opstart" (6 hold i
september fra en aktivitet, der ikke findes i aktivitetslisten) og "test".
5 mappinger er markeret **usikre**. Det gælder især kl. 06-holdene, som
hedder "WOD Mandag/Onsdag 0600" i goMember, men "WOD uden træner" på
holdene. De vises med mærket "usikker" under Holdtyper.

For hver type beregner `byg_styringsdata.py` forskellene mellem
"søskende" på de kommende hold: max. pladser, farve, holdnavn uden ugedag
og tid, venteliste og fremmøderegistrering. Eksempler: WOD-holdene har
venteliste slået til på 57 og fra på 77 kommende hold. Fremmøde er til på
86 og fra på 48. Én WOD-tid har farven 81c784 i stedet for 9ccc65. HYROX
staves to måder.

**Træner:** På 171 kommende træningshold er der ingen synlig træner.
goMember viser kun navnet, når det er sat på det enkelte hold. Holdene har
en standard-ansvarlig, men den er ikke offentlig. Prototypen skriver derfor
"Ingen træner synlig" og ikke "ingen træner". Det er ikke sikkert, at
holdet mangler en træner.

## 3. Rettelsesmodellen

En rettelse er en post i en lokal kladde:

```json
{
  "kind": "kapacitet",            // traener | aflys | kapacitet | tid | venteliste | fremmoede | navn | farve
  "scope": "type",                // hold | fremtidige | type
  "activityId": "Activity2516277445812201999",
  "eventEntityId": null,          // sat når scope = hold
  "from": "2026-11-18T00:00",     // gælder hold fra og med (fremtidige/type)
  "after": 16,
  "before": "12", "afterText": "16",
  "group": "g…",                  // "alle af typen" = én gruppe, én post pr. aktivitet
  "affectedCount": 8,
  "target": {                     // til et senere sync-lag – kaldes ikke
    "entity": "Hold / serie", "field": "maxAttendees", "level": "serie",
    "update": "allFromCurrent", "activityId": "…", "eventId": "202611181700",
    "intendedEndpoints": [{"verb": "PUT", "path": "/api/activity/{activityId}/event/{id}", "operationId": "EventApi_Put"}],
    "alsoActivityDefault": { "...": "PUT /api/activity/{id}" },
    "status": "kladde - ikke sendt"
  }
}
```

- **Omfang:** "kun dette hold" svarer til `update=current`. "Dette og
  fremtidige" og "alle af typen" svarer til `update=allFromCurrent` fra det
  første berørte hold. Ved "alle af typen" laves der én post pr. berørt
  goMember-aktivitet, og posterne vises som én gruppe. Ved typer med flere
  aktiviteter skal der også tages stilling til aktivitetens egen
  standardværdi (`alsoActivityDefault`), fordi goMember har tre niveauer:
  aktivitet → serie → hold.
- **Aflys** og **flyt tid** kan ikke bruges for "alle af typen". Det giver
  ikke mening at give alle WOD-tider samme klokkeslæt. Aflys er altid en
  aflysning med besked og aldrig en sletning. "Luk for jul" laves fra
  Drift som én aflysningskladde pr. hold den dag.
- Nøgletallene på Drift viser bevidst goMembers egne tal, ikke kladderne.
- Rettelser kan ikke laves på hold, der allerede er afholdt.
- **Træner** er fritekst for nu. Et sync-lag skal slå navnet op til et
  medlems-id. Det kræver login.
- Eksport: JSON-fil (format `strong-gym-styring-kladde`, version 1) og
  tekst-tjekliste med `[ ]` pr. rettelse og før → efter på dansk.

## 4. Forslag: et senere "send til goMember"-lag

`CLAUDE.md` fastslår, at integrationen kun læser, og at skrivning er en
**bevidst, separat beslutning**. Klienten i `gomember_client.py` må ikke
udvides med skrivemetoder. Forslaget respekterer det.

1. **Separat komponent.** En lille server-side tjeneste i sit eget
   repo/mappe med sin egen, snævert afgrænsede skriveklient. Den må ikke
   genbruge eller udvide `gomember_client.py` og ikke køre i browseren. Den
   kender kun de få endpoints, der skal bruges (fx `EventApi_Put`,
   `EventApi_CancelEvent`, `ActivityApi_Put`), via en eksplicit
   tilladelsesliste. `DELETE` og de fire `DENIED_PATHS`
   (batchupdate/clone) er udelukket.
2. **Egen konto.** Et separat goMember-login med de mindst mulige
   rettigheder til skrivning. Det må ikke være det skrivebeskyttede
   læselogin. Hemmeligheder ligger kun på serveren.
3. **Godkendelse pr. rettelse.** Kladden importeres (JSON-formatet ovenfor).
   En navngiven person godkender hver enkelt post, og grupper kan ikke
   godkendes samlet uden at hver post vises.
4. **Dry-run først.** For hver post: hent holdet/serien frisk (GET), vis den
   præcise request, der ville blive sendt, og sammenlign `before` med den
   aktuelle værdi. Afvis, hvis goMember har ændret sig siden kladden.
5. **Revisionslog.** Hver afsendelse logges: hvem godkendte, hvornår, den
   præcise request, goMembers svar og værdien før og efter. Loggen må kun
   kunne tilføjes til. Hver rettelse skal kunne rulles tilbage med en ny,
   godkendt rettelse, ikke automatisk.
6. **Verificér før brug.** Før noget sendes rigtigt, skal goMember support
   bekræfte, eller en testklub/testaktivitet vise, hvad hvert endpoint gør.
   Det gælder især `update`-værdierne `current` / `allFromCurrent` /
   `allFuture`: rammer de serien eller kun genererede hold? Overskriver de
   hold med egen record? Gælder det også `cancelevent.updateLevel`? Desuden:
   ændres `eventId` ved flytning, og hvilket format forventes for
   `responsible`?
7. **Én slags ad gangen.** Start med den mindst risikable rettelse (fx
   fremmøde til/fra på ét hold) og udvid derefter én type ad gangen.

## 5. Risici

- **Forkert omfang i goMember:** en "allFromCurrent"-rettelse kan ramme
  flere hold end forventet eller overskrive manuelle tilpasninger
  (vikarer, makker-WOD). Derfor: dry-run og godkendelse.
- **Forældede data:** kladden bygger på et øjebliksbillede. Andre kan have
  rettet i goMember siden. Sync-laget skal sammenligne før-værdien.
- **Usikker mapping:** kl. 06-holdene, MIKKO og hvilende WOD-aktiviteter kan
  være sat på en forkert type. "Alle af typen" rammer så de forkerte hold.
- **Tabt kladde:** `localStorage` kan blive ryddet. Eksportér som JSON før
  større ændringer.
- **Persondata:** så snart siden viser medlemsdata, bliver den et
  persondatasystem (GDPR). Det er ikke tilfældet i dag.
- **Offentlig adgang:** siden har kun `noindex`. Det er ikke beskyttelse.

## 6. Åbne spørgsmål

- **Login er ikke afprøvet.** `check_auth.py` er ikke kørt, og formen på
  token-requesten er antaget ud fra swagger.
- **Historik mangler:** holdplanen bagud er næsten tom (18 hold før 1/11).
  Belægningstal bygger på 2 uger. Om historik kan hentes med login, vides
  ikke. Alternativt kan et dagligt øjebliksbillede af `booked` opbygge den.
- **Hvad gater etiketterne?** Det er uklart, om tags på et hold begrænser,
  hvem der kan booke, og hvad "ingen tags" betyder.
- **Hvem er standard-ansvarlig** på de genererede hold?
- **Adgangskontrol til siden:** før medlemsdata vises, skal siden ligge bag
  et rigtigt login, fx Cloudflare Access foran siden eller et login i
  worker'en, og dataene skal hentes server-side. De må ikke ligge som en
  statisk JSON-fil.
- Skal kladden kunne deles mellem flere frivillige (fælles lager i stedet
  for `localStorage`)?

## 7. Foreslået vej frem

1. **Nu:** brug prototypen internt (lokalt eller på en ikke-linket,
   beskyttet adresse) til overblik og tjeklister. Lav juleaflysningerne
   manuelt ud fra tjeklisten.
2. **Opdatér data jævnligt:** kør `opdater.py` hver nat (se "Automatisk
   opdatering"). Det giver også en belægningshistorik.
3. **Login:** kør `check_auth.py` med den skrivebeskyttede testkonto og
   bekræft, hvad den kan læse.
4. **Adgangskontrol:** læg siden bag login, før der kommer medlemsdata på.
   Hent derefter medlemstal server-side og udfyld Medlemmer-visningen.
5. **Oprydning i goMember** (manuelt, efter beslutning): ensret farver,
   venteliste og fremmøde pr. type, og fjern hvilende aktiviteter.
6. **Først derefter**, og kun hvis bestyrelsen beslutter det, byg
   sync-laget fra afsnit 4. Afklar først endpoint-adfærden med goMember,
   start med dry-run og én rettelsestype.
