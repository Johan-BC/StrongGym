# Strong Gym – Setup / Infrastruktur

## Middleman (proxy til holdplan-data)

Hjemmesidens holdplan henter **live data** fra stronggym.dk's offentlige
kalender-API. Browseren kan ikke kalde det API direkte (CORS – stronggym.dk
sender ikke de nødvendige headers), så vi bruger en lille mellem-service
("middleman") der henter data server-til-server og videresender det til siden
med korrekte CORS-headers.

- **Provider:** Cloudflare Workers (gratis tier)
- **URL:** https://stronggym.jbchristophersen.workers.dev/
- **Kildekode:** [`worker.js`](worker.js) i dette projekt
- **Login/credentials:** Ingen. Data er offentligt tilgængeligt (synligt for
  ikke-indloggede besøgende), så middleman'en bruger hverken login eller nøgler.

### Sådan kaldes den
```
https://stronggym.jbchristophersen.workers.dev/?from=2026-06-01&to=2026-06-30
```
- `from` / `to` er valgfrie (format `YYYY-MM-DD`). Uden dem bruges
  indeværende måned.
- Returnerer JSON: array af `{ date, slots: [...] }`, hvor hver slot er en
  holdinstans med bl.a. `name`, `startTime`, `endTime`, `maxAttendees`,
  `booked`, `waitingList`, `status`, `responsible[].displayName` (coach).

### Bagvedliggende API (upstream)
```
<portal-adresse>/api/activity/event/days?eventsToShow=300&fromOffset=<ISO>&toTime=<ISO>
```

API'et findes kun på det domæne goMember serverer. Derfor har worker'en en
**liste** af adresser i `UPSTREAM_HOSTS` ([`worker.js`](worker.js)) og bruger
den første der svarer med rigtige holdplan-data:

1. `https://medlem.stronggym.dk` — portalen efter domæneskiftet
2. `https://www.stronggym.dk` — portalen i dag

Det gør domæneskiftet ufarligt: samme worker virker både før og efter, uden
et tidsvindue der skal rammes. Når skiftet er gennemført, kan www-linjen
slettes fra listen. Se afsnittet om domæneskiftet i
[`Stronggym.md`](Stronggym.md).

Et svar tæller kun som gyldigt, hvis det er et **array af dage** — ikke blot
HTTP 200. Det er med vilje: når `www.stronggym.dk` bliver vores eget statiske
site, vil `/api/...` på den adresse sandsynligvis svare 200 med HTML, og en
rå status-tjek ville tro at det var data.

Svaret bærer headeren `X-Upstream-Host` med den adresse der leverede data —
brug den til at se hvad worker'en faktisk henter fra:

```
curl -sI "https://stronggym.jbchristophersen.workers.dev/?from=2026-11-10&to=2026-11-16" | findstr /i upstream
```

Fejler alle adresser, svarer worker'en 502 med en liste over hvad der blev
forsøgt, og siden falder selv tilbage til sin faste ugeplan.

### Vedligehold / noter
- Hvis Cloudflare-kontoen eller worker'en fjernes, holder holdplanen op med at
  vise live data.
- Hvis stronggym.dk (Memberlink) ændrer deres API-format, skal `worker.js`
  og/eller render-koden i siden opdateres.
- Worker'en husker den adresse der sidst virkede i 10 minutter (`HOST_MEMO_MS`)
  og prøver hele listen forfra derefter. Et domæneskifte bliver altså fanget
  af sig selv senest 10 minutter efter, uden deploy.
- CORS er sat til `*` (alle origins). Kan låses til kun sidens eget domæne ved
  at ændre `ALLOW_ORIGIN` i [`worker.js`](worker.js) og re-deploye.

## Facebook (seneste opslag)

Forsiden ("Vores Fællesskab") og nyhedssiden viser opslag fra
[facebook.com/stronggym3000](https://www.facebook.com/stronggym3000/) med
**Metas Page Plugin** — som en almindelig iframe, uden Facebooks
JavaScript-SDK.

### Den ene parameter der afgør det hele

Målt i browseren 10. november 2026, tre varianter af `plugins/page.php` for
den samme side:

| Variant | Resultat |
|---|---|
| `tabs=timeline` — **det Meta anbefaler** | ingen opslag, kun logo og navn |
| `show_posts=true` — markeret *deprecated* | opslag vises |
| `show_posts=true` med sidens numeriske URL | opslag vises |

Altså: brug `show_posts=true`. Den anbefalede afløser viser ingenting, og det
kan man ikke læse sig til nogen steder — Metas dokumentation siger det
modsatte. Det var `tabs=timeline`, siden brugte før, og derfor stod boksen på
nyhedssiden tom.

goMember-sitet på stronggym.dk bruger samme plugin med `show_posts=true`, og
det er sådan vi opdagede det.

### Sådan er det sat ind

```html
<iframe src="https://www.facebook.com/plugins/page.php?href=...%2Fstronggym3000
             &show_posts=true&adapt_container_width=true&width=300&height=560"
        width="300" height="560" scrolling="no" loading="lazy"></iframe>
```

Facebooks **SDK er fjernet** (`connect.facebook.net/.../sdk.js` og
`fb-root`). En direkte iframe kan præcis det samme, så der er ét
tredjepartsscript mindre på hver eneste sideindlæsning. Der er hverken app,
token eller noget at vedligeholde.

### Vedligehold / noter (Facebook)
- **Cookies.** Den besøgendes browser henter fra facebook.com og får cookies
  derfra. Skal sitet have en samtykkeløsning, hører Facebook-boksen med i
  den. Alternativt kan iframen lægges bag et klik ("Vis opslag fra
  Facebook"), så der først hentes noget, når den besøgende beder om det.
- **`show_posts` er udfaset af Meta.** Den virker i dag, men afløseren virker
  allerede ikke — så den dag `show_posts` også holder op, er der ingen
  plugin-vej videre. Det sker tavst: boksen bliver bare ~70 px høj med logo
  og navn. Det er værd at kigge efter en gang imellem.
- **Bredde.** Plugin'et kan maks. 500 px og er én kolonne. Derfor ligger det
  som sidekolonne ved siden af billedgitteret og ikke som kort i fuld bredde.
  Ændrer du bredden, skal **både** `width=` i URL'en og `width`-attributten
  på iframen rettes — plugin'et renderer efter URL'en, ikke efter CSS. CSS
  kan kun klemme iframen sammen, og så bliver indholdet klippet i højre side.
  Bredderne er valgt til at passe i den smalleste visning: **300 px** på
  forsiden (en 375 px-telefon giver 327 px minus kortets padding) og
  **250 px** på nyhedssiden (300 px-kolonnen minus dens padding).
- Siden bruger vanity-URL'en (`/stronggym3000`). goMember bruger stadig den
  gamle numeriske (`/Strong-Gym-1374851259482820`). Begge virker.

### Hvis plugin'et en dag holder op

Alternativet er Graph API'et: `GET /{page-id}/feed` med tilladelserne
`pages_show_list`, `pages_read_engagement` og `pages_read_user_content`,
kaldt server-side fra worker'en med en side-token lagt som Cloudflare-secret.

Det blev bygget og testet 10. november 2026 og lagt væk igen, fordi
plugin'et løste opgaven uden en Meta-app. Hovedpointerne, hvis det skal frem
igen:

- Side-tokenen hentes af en **administrator på Facebook-siden**: kort
  brugertoken i Graph API Explorer → lang brugertoken → side-token via
  `/me/accounts`. Side-tokenen udløber ikke, men bliver ugyldig ved
  adgangskodeskift, tabt rolle på siden, eller hvis appen fjernes.
- Tokenen hører hjemme som Cloudflare-secret, aldrig i git, og sendes som
  `Authorization`-header — ikke som `?access_token=`, så den ikke ender i en
  URL-log.
- Billederne ligger på Facebooks CDN. Vil man undgå at den besøgende
  kontakter Meta, skal de også proxes gennem worker'en — og den proxy skal
  være snæver (kun `https`, kun værter der **ender** på `fbcdn.net` eller
  `facebook.com`, kun `image/*`-svar), ellers er det en åben videresendelse.
- `/feed` returnerer også planlagte og ikke-offentliggjorte opslag; de
  frasorteres på `is_published`.
- Graph API er versioneret, og en version lever ca. to år.
- Det er uafklaret, om `pages_read_user_content` kræver App Review for ens
  egen side. Dokumentationen siger kun, at *Page Public Content Access* er
  nødvendig når man **ikke** ejer siden.

## Trænere

Trænerne står i `coaches`-arrayet i [`index.html`](index.html). Felterne er
`name`, `specialty`, `bio` og `photo`.

**Billeder.** De otte oprindelige trænere har deres billede fra goMember
(`image.gomember.com/azure/sitesite.../ProfilePicture/...`). Det er den
foretrukne kilde: oprettes træneren i goMember, følger billedet med samme
mønster, og der er kun ét sted at vedligeholde.

Er `photo` tomt, viser kortet et personikon i stedet. Det er med vilje —
bedre end et brudt billede, og det gør det synligt at billedet mangler.

**Link aldrig direkte til Facebook.** URL'erne fra `fbcdn.net` er signerede
og udløber, så billedet ville forsvinde fra sitet efter et stykke tid.
Billeder fra Facebook skal gemmes som filer i `billeder/traenere/`.

De fire nyeste trænere peger på `billeder/traenere/<fornavn>.jpg`. Filerne
er 400×400 JPEG, beskåret kvadratisk om midten. Mangler filen, falder
kortet tilbage til personikonet — den advarsel er med vilje synlig.

**Beskær om ansigtet, ikke om midten.** Kortet viser billedet i en cirkel,
og CSS'ens `object-fit:cover` beskærer om billedets midte. På et stående
portræt rammer det trøjen i stedet for ansigtet. Filerne er derfor beskåret
på forhånd med ansigtet ca. 38 % nede i rammen. Det kræver `Pillow`
(`python -m pip install Pillow`).

**Hvordan de fire blev hentet.** `mathias.jpg` blev trukket direkte fra
Facebook-opslaget: fbcdn sender CORS-headers, så siden selv må læse
billeddataene, og de kan beskæres på et canvas og gemmes som fil fra
browserkonsollen. **Det virker kun én gang pr. sideindlæsning** — derefter
blokerer Chrome flere automatiske downloads fra samme side, og den
blokering var ikke til at få ophævet. De øvrige veje er også lukkede:
udklipsholderen afvises, billeddata som tekst filtreres fra undervejs, og
Facebooks egen CSP blokerer upload til en lokal modtager. Chrome-udvidelsens
screenshot-funktion virkede heller ikke.

De tre andre blev derfor gemt manuelt fra opslagene og lagt ind som filer.
Det er i praksis den hurtigste vej.
## Hvor bio'erne kommer fra

Facebook-serien **"Mød vores træner"** rummer otte opslag, hvor trænerne
præsenterer sig selv. De er alle hentet ind, og de oprindelige tekster på
sitet er erstattet, fordi de var generiske og flere steder direkte
misvisende — Silja stod fx som "yoga- og mobility-instruktør", men har
dyrket crossfit i tolv år, de sidste otte på eliteniveau.

Bio'erne er omskrevet til samme korte form som resten af kortene, men
indholdet stammer fra trænerne selv.

**Tre trænere har intet opslag:** Mika Zillo, Sebastian Meier og Katja
Kliem. De står stadig med den oprindelige, generiske tekst, markeret med
`// TODO` i [`index.html`](index.html). Den tekst er ikke bekræftet af
nogen kilde og bør få samme behandling, når der er noget at bygge på.

## Forsidens design

Forsiden blev tegnet om 10. november 2026 på branchen `nyt-design`, med
butcherslab.dk som pejlemærke. Palet og logo er uændrede — det er rytme,
skala og bevægelse der er lavet om.

Siden er bygget af `band`-afsnit med fælles lodret rytme. Fælles klasser:
`.wrap` (bredde), `.eyebrow` (lille overskrift), `.display` (stor
overskrift), `.lede` (manchet), `.pillar` (kort), `.quote` (udtalelse),
`.mood` (billedgitter), `.finale` (afsluttende kald).

**Indtoning ved scroll** styres af `setupReveal()`, som kaldes fra
`render()`. Alt med klassen `.reveal` toner ind, når det kommer i
synsfeltet. Kan browseren ikke `IntersectionObserver`, vises alt med det
samme — der mangler aldrig indhold. `prefers-reduced-motion` slår både
indtoning og baggrundsbevægelse fra.

### To ting der skal på plads, før siden går live

**Udtalelserne er opdigtede.** `udtalelser` i [`index.html`](index.html)
indeholder tre citater fra Line, Thomas og Mette. De findes ikke. De er
skrevet for at vise, hvordan afsnittet virker, og **skal** erstattes med
rigtige citater fra rigtige medlemmer — ellers står der opdigtede
mennesker på en offentlig side. Konstanten
`UDTALELSER_ER_PLACEHOLDER` står lige over listen som påmindelse. Sæt
listen til `[]` for at skjule afsnittet helt.

**Stemningsbillederne mangler.** `stemning`-listen har fem tomme felter,
der tegnes som grafik. Se
[`billeder/stemning/LÆS_MIG.md`](billeder/stemning/L%C3%86S_MIG.md).

Nøgletallene i heroen (`12 trænere`, `7 dage med hold`, `0 ejere med
udbytte`) er valgt, fordi de kan efterprøves. Undgå at sætte medlemstal
eller årstal ind, som ingen har bekræftet.
