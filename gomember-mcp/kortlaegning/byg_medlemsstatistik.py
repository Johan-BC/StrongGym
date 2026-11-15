#!/usr/bin/env python3
"""
Bygger ../../styring-medlemmer.json: anonyme medlemstal til Medlemmer-visningen
i styring.html.

    python3 byg_medlemsstatistik.py            # henter fra goMember (ca. 23 GET-kald + login)
    python3 byg_medlemsstatistik.py --struktur # viser kun svarets form (nøgler/typer), skriver intet
    python3 byg_medlemsstatistik.py --force    # skriv selv om fornuftskontrollen fejler

Fornuftskontrol: ændrer det samlede antal medlemmer sig mere end 25 % i forhold
til den forrige styring-medlemmer.json, eller er listen afskåret af
sidestørrelsen, stopper scriptet uden at skrive (medmindre --force).

Regler (se CLAUDE.md):
- Alle kald går gennem GoMemberClient.get(). Ingen rå HTTP, ingen skrivekald.
- Fra medlemslisten bruges KUN createdTs og tagsAssigned. Navne, numre og
  id'er læses aldrig ind i egne variabler, printes, logges eller gemmes.
  Rækkerne kasseres straks efter optællingen.
- Udmeldingsdato: for medlemmer med etiketten "Ønsker udmelding" (og kun dem)
  hentes GET /api/memberdata/{id}, og KUN felterne LeftDate/JoinedDate læses ud.
  Svaret er medlemmets fulde stamkort og kasseres straks; id'er og datoer gemmes
  ikke - kun antal pr. måned og grove medlemstids-grupper.
- Outputtet indeholder kun optællinger. Tal for kombinationer (fx "uden
  medlemskab", nye pr. måned) vises som "<3", når de er 1 eller 2.
  Tal pr. enkelt etiket vises som de er.
- styring-medlemmer.json committes og kan ligge på hjemmesiden: ejeren har
  godkendt, at samlede (aggregerede) medlemstal er offentlige. Filen må
  aldrig indeholde data om enkeltpersoner.
"""
import collections
import datetime as dt
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stier  # noqa: E402
from netlag import Hentning, NetFejl  # noqa: E402  (GoMemberClient.get() - kun GET)

OUT = os.path.join(stier.STYRING_UD, "styring-medlemmer.json")
TZ = ZoneInfo("Europe/Copenhagen")
MIN_CELLE = 3  # tal under dette vises som "<3" for kombinationer
SIDE = 1000    # sidestørrelse for medlemslisten
MAKS_AENDRING = 0.25  # fornuftskontrol mod forrige fil

# Etiketter hvis tal lægges sammen til "betalende medlemskaber"
BETALENDE = ["Premium medlemskab", "Ung 15-24 år medlemskab", "Klippekort (10 klip)", "Fordels medlemskab", "12 måneder"]
# "12 måneder" = årsabonnement (5.500 kr. pr. år), oplyst af klubben 15. november 2026.
MAANED_NAVN = ["jan", "feb", "marts", "april", "maj", "juni", "juli", "august", "sep", "okt", "nov", "dec"]
MAANED_LANG = ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august",
               "september", "oktober", "november", "december"]
UDMELD_RE = re.compile(r"^Udmeld slut (\w+)$", re.I)
BERO_RE = re.compile(r"^Bero slut (\w+)$", re.I)
GRUPPE_NAVN = {
    "medlemskab/produkt": "medlemskab",
    "intern status/administration": "status",
    "system/rolle": "rolle",
    "andet": "andet",
    "ugedag": "ugedag",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def skjul(n):
    """Kombinationstal: 1-2 vises som '<3'. 0 og >=3 vises som tal."""
    return "<3" if 0 < n < MIN_CELLE else n


def parse_ts(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return dt.datetime.fromtimestamp(v / 1000 if v > 1e11 else v, tz=dt.timezone.utc).astimezone(TZ)
    s = str(v)
    m = re.match(r"/Date\((-?\d+)", s)
    if m:
        return dt.datetime.fromtimestamp(int(m.group(1)) / 1000, tz=dt.timezone.utc).astimezone(TZ)
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)  # antag lokal tid, hvis goMember ikke angiver zone
    return d.astimezone(TZ)


def rows_of(resp):
    """Find listen af medlemsrækker i svaret uden at kende formen på forhånd."""
    if isinstance(resp, list):
        return resp, None
    if isinstance(resp, dict):
        total = None
        for k in ("totalCount", "total", "totalItems", "count", "totalRecords", "records"):
            if isinstance(resp.get(k), int):
                total = resp[k]
                break
        for k in ("members", "items", "data", "rows", "results", "list", "entities"):
            if isinstance(resp.get(k), list):
                return resp[k], total
        for v in resp.values():
            if isinstance(v, list) and v and isinstance(v[0], dict) and "tagsAssigned" in v[0]:
                return v, total
    raise NetFejl("Kunne ikke finde medlemslisten i svaret fra goMember (kør byg_medlemsstatistik.py --struktur).")


# ---------------------------------------------------------------- udmeldingsdato
UDMELD_ETIKET = "Ønsker udmelding"
MAKS_FEJL_ANDEL = 0.20        # flere mislykkede medlemskald end dette -> trinnet fejler
LAENGDE_GRUPPER = ["under 6 mdr", "6-12 mdr", "1-2 år", "over 2 år", "ukendt"]


def _dato(v):
    """'YYYY-MM-DDTHH:MM:SS' -> date, ellers None."""
    if not isinstance(v, str) or len(v) < 10:
        return None
    try:
        return dt.date.fromisoformat(v[:10])
    except ValueError:
        return None


def _formdatoer(data):
    """Find KUN felterne LeftDate og JoinedDate i medlemsformularen.
    Returnerer (har_leftdate_felt, leftdate, joineddate). Intet andet læses ud."""
    fundet = {}

    def walk(x):
        if isinstance(x, dict):
            fn = x.get("fieldName")
            if fn in ("LeftDate", "JoinedDate") and fn not in fundet:
                v = x.get("value")
                if v in (None, ""):
                    v = x.get("_value")
                fundet[fn] = _dato(v)
            for v in x.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(data)
    return "LeftDate" in fundet, fundet.get("LeftDate"), fundet.get("JoinedDate")


def _laengde(ind, ud):
    if not ind or not ud or ud < ind:
        return "ukendt"
    mdr = (ud.year - ind.year) * 12 + (ud.month - ind.month) - (ud.day < ind.day)
    if mdr < 6:
        return "under 6 mdr"
    if mdr < 12:
        return "6-12 mdr"
    if mdr < 24:
        return "1-2 år"
    return "over 2 år"


def hent_udmeldinger(hent, tag_id, forventet, idag, kald):
    """Udmeldingsdato for medlemmer med etiketten 'Ønsker udmelding'.

    Kun to kald-typer: GET /api/members?filter.tags=<etiket> (kun entityId bruges) og
    GET /api/memberdata/{id}, hvor KUN felterne LeftDate/JoinedDate læses. Svarene
    kasseres straks; der gemmes kun måned og en grov længde-gruppe pr. medlem - uden id.
    Fejlbeskeder nævner aldrig id'er eller indhold."""
    if not tag_id:
        raise NetFejl(f"Etiketten '{UDMELD_ETIKET}' findes ikke længere i goMember.")
    _, resp = hent.get("/api/members", {"filter.tags": tag_id, "filter.pageSize": SIDE, "filter.currentPage": 1},
                       tilladt=(), vis="/api/members?filter.tags=…")
    kald.append("GET /api/members?filter.tags=<Ønsker udmelding>&filter.pageSize=1000")
    rows, _ = rows_of(resp)
    ids = [r.get("entityId") for r in rows if isinstance(r, dict) and r.get("entityId")]
    del rows, resp
    if not ids:
        raise NetFejl(f"Ingen medlemmer med etiketten '{UDMELD_ETIKET}' - det ligner en fejl; stopper.")
    if len(ids) != forventet:
        raise NetFejl(f"Filteret på etiketten gav {len(ids)} medlemmer, men {forventet} har etiketten i "
                      "medlemslisten - filteret virker ikke som forventet; stopper.")
    n_ids = len(ids)
    datoer = []          # (leftdate, joineddate) - uden id, kun i hukommelsen
    fejl = 0
    har_felt = 0
    for mid in ids:
        try:
            st, data = hent.get(f"/api/memberdata/{mid}", None, tilladt=(404,), vis="/api/memberdata/{id}")
        except NetFejl as e:
            if "Login" in str(e) or "Loftet" in str(e) or "login" in str(e):
                raise
            fejl += 1
            continue
        if st != 200 or not isinstance(data, dict):
            fejl += 1
            del data
            continue
        try:
            felt, ud, ind = _formdatoer(data)
        except Exception:  # noqa: BLE001 - aldrig indholdet i en fejlbesked
            felt, ud, ind = False, None, None
        del data
        har_felt += felt
        datoer.append((ud, ind))
    ids = None
    kald.append(f"GET /api/memberdata/{{id}} x {len(datoer) + fejl}")
    if fejl > MAKS_FEJL_ANDEL * (len(datoer) + fejl):
        raise NetFejl(f"Udmeldingsdato kunne ikke hentes for {fejl} af {len(datoer) + fejl} medlemmer "
                      f"(mere end {MAKS_FEJL_ANDEL:.0%}); stopper.")
    if datoer and har_felt == 0:
        raise NetFejl("Medlemsformularen i goMember har ikke længere feltet 'LeftDate' (udmeldingsdato) - "
                      "statistikken kan ikke laves; stopper.")

    med = [(u, i) for u, i in datoer if u]
    pr_m = collections.defaultdict(lambda: {"passeret": 0, "kommende": 0})
    for u, _ in med:
        pr_m[u.strftime("%Y-%m")]["passeret" if u < idag else "kommende"] += 1
    maaneder = []
    if pr_m:
        keys = sorted(pr_m)
        y, m = int(keys[0][:4]), int(keys[0][5:])
        alle = []
        while f"{y:04d}-{m:02d}" <= keys[-1]:
            alle.append(f"{y:04d}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if len(alle) > 36:          # meget spredte datoer: kun måneder med udmeldinger
            alle = keys
        for k in alle:
            c = pr_m.get(k, {"passeret": 0, "kommende": 0})
            maaneder.append({"maaned": k, "antal": c["passeret"] + c["kommende"],
                             "passeret": c["passeret"], "kommende": c["kommende"]})
    lg = collections.Counter(_laengde(i, u) for u, i in datoer)
    grupper = [{"gruppe": g, "antal": skjul(lg.get(g, 0))} for g in LAENGDE_GRUPPER]
    # Sekundær skjulning: er præcis én gruppe skjult, kunne den regnes ud fra totalen.
    skjulte = [x for x in grupper if x["antal"] == "<3"]
    if len(skjulte) == 1:
        rest = [x for x in grupper if isinstance(x["antal"], int) and x["antal"] > 0]
        if rest:
            min(rest, key=lambda x: x["antal"])["antal"] = None
    del datoer, med
    return {
        "etiket": UDMELD_ETIKET,
        "medEtiket": n_ids,
        "hentet": sum(lg.values()),
        "kunneIkkeHentes": fejl,
        "medDato": sum(c["passeret"] + c["kommende"] for c in pr_m.values()),
        "udenDato": sum(lg.values()) - sum(c["passeret"] + c["kommende"] for c in pr_m.values()),
        "passeret": sum(c["passeret"] for c in pr_m.values()),
        "kommende": sum(c["kommende"] for c in pr_m.values()),
        "denneMaaned": idag.strftime("%Y-%m"),
        "prMaaned": maaneder,
        "medlemstid": grupper,
    }


def tag_ref(x):
    """tagsAssigned kan være id-strenge eller små objekter. Returnér tag-id/navn-reference."""
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for k in ("entityId", "id", "tagId", "name", "displayName"):
            if x.get(k):
                return str(x[k])
    return None


def struktur(resp):
    """Vis kun formen: nøgler og typer. Ingen værdier."""
    def mask(s):
        return re.sub(r"[A-Za-zÆØÅæøå]", "a", re.sub(r"\d", "9", str(s)))[:40]
    print("top:", type(resp).__name__, sorted(resp.keys()) if isinstance(resp, dict) else "")
    rows, total = rows_of(resp)
    print("rækker:", len(rows), "total-felt:", total)
    keys = collections.Counter(k for r in rows for k in r.keys())
    print("nøgler pr. række:", dict(keys))
    ta = [type(x).__name__ for r in rows for x in (r.get("tagsAssigned") or [])]
    print("tagsAssigned-elementtyper:", collections.Counter(ta))
    sample = next((x for r in rows for x in (r.get("tagsAssigned") or [])), None)
    if isinstance(sample, dict):
        print("tagsAssigned-objektnøgler:", sorted(sample.keys()))
    elif sample is not None:
        print("tagsAssigned-mønster:", mask(sample))
    print("createdTs-mønstre:", collections.Counter(mask(r.get("createdTs")) for r in rows).most_common(3))


def byg(hent, now=None, ud=OUT, force=False, only_struktur=False):
    """Hent medlemslisten via hent (netlag.Hentning) og skriv optællingerne til ud.
    Returnerer en kort opsummering. Rejser NetFejl ved fejl eller fejlet fornuftskontrol."""
    kald = []

    _, resp = hent.get("/api/members", {"filter.pageSize": SIDE, "filter.currentPage": 1}, tilladt=())
    kald.append(f"GET /api/members?filter.pageSize={SIDE}&filter.currentPage=1")
    if only_struktur:
        struktur(resp)
        return None

    rows, total_felt = rows_of(resp)
    # Behold KUN createdTs og tagsAssigned. Alt andet kasseres her.
    slim = [{"c": r.get("createdTs"), "t": [tag_ref(x) for x in (r.get("tagsAssigned") or [])]} for r in rows]
    n_rows = len(rows)
    del rows, resp
    if n_rows >= SIDE or (isinstance(total_felt, int) and total_felt > n_rows):
        raise NetFejl(f"Medlemslisten er afskåret ({n_rows} rækker, goMember siger {total_felt}); "
                      "tallene ville være forkerte.")
    if n_rows == 0:
        raise NetFejl("Medlemslisten fra goMember var tom.")
    prev = stier.forrige("styring-medlemmer.json")
    gl = (prev or {}).get("total")
    if isinstance(gl, int) and gl > 0 and abs(n_rows - gl) / gl > MAKS_AENDRING:
        msg = (f"Antal medlemmer ændrer sig fra {gl} til {n_rows} ({100 * (n_rows - gl) / gl:+.0f} %) - "
               f"mere end {MAKS_AENDRING:.0%} i forhold til forrige fil")
        if not force:
            raise NetFejl(msg + " (brug --force, hvis det er rigtigt).")
        print("ADVARSEL (--force):", msg, file=sys.stderr)

    # Etiketnavne: live, ellers det gemte snapshot
    try:
        _, tags_live = hent.get("/api/tag", None, tilladt=())
        kald.append("GET /api/tag")
        tag_kilde = "live (GET /api/tag)"
    except NetFejl as e:
        if "Login" in str(e) or "Loftet" in str(e):
            raise
        tags_live = load(os.path.join(stier.DATA_DIR, "tag.json"))
        tag_kilde = "snapshot data/tag.json"
    if isinstance(tags_live, dict):
        tags_live = next((v for v in tags_live.values() if isinstance(v, list)), [])

    ht = load(os.path.join(stier.KORTLAEG_DIR, "holdtyper.json"))
    gruppe_af = {t["tagId"]: t["gruppe"] for t in ht["tags"]}
    navn_af = {}
    for t in tags_live:
        tid = t.get("entityId") or t.get("id")
        navn = t.get("name") or t.get("displayName")
        if tid and navn:
            navn_af[tid] = navn
    for t in ht["tags"]:
        navn_af.setdefault(t["tagId"], t["navn"])
    id_af_navn = {v: k for k, v in navn_af.items()}

    def to_id(ref):
        if ref in navn_af:
            return ref
        return id_af_navn.get(ref, ref)

    now = now or dt.datetime.now(TZ)
    pr_tag = collections.Counter()  # antal pr. etiket (ingen personer)
    uden_tags = 0
    uden_medlemskab = 0
    uden_betalende = 0
    betalende_personer = 0
    nye_30 = 0
    pr_maaned = collections.Counter()
    uden_dato = 0
    foer_periode = 0

    # 12 hele/igangværende kalendermåneder bagud, inkl. denne
    maaneder = []
    y, m = now.year, now.month
    for _ in range(12):
        maaneder.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    maaneder.reverse()

    for r in slim:
        ids = {to_id(x) for x in r["t"] if x}
        for tid in ids:
            pr_tag[tid] += 1
        if not ids:
            uden_tags += 1
        grupper = {gruppe_af.get(t, "ukendt") for t in ids}
        if "medlemskab/produkt" not in grupper:
            uden_medlemskab += 1
        navne = {navn_af.get(t, t) for t in ids}
        if navne & set(BETALENDE):
            betalende_personer += 1
        else:
            uden_betalende += 1
        c = parse_ts(r["c"])
        if c is None:
            uden_dato += 1
            continue
        if (now - c).days < 30 and c <= now:
            nye_30 += 1
        key = c.strftime("%Y-%m")
        if key in maaneder:
            pr_maaned[key] += 1
        elif key < maaneder[0]:
            foer_periode += 1
    del slim

    def tag_row(tid):
        return {"tagId": tid, "navn": navn_af.get(tid, tid), "antal": pr_tag.get(tid, 0)}

    # Etiketter pr. gruppe (alle kendte etiketter i grupperne, også dem med 0)
    def gruppe(g):
        ids = [t["tagId"] for t in ht["tags"] if t["gruppe"] == g]
        ids += [t for t in pr_tag if gruppe_af.get(t) is None and g == "ukendt"]
        rows_ = [tag_row(t) for t in ids]
        return sorted(rows_, key=lambda x: (-x["antal"], x["navn"]))

    ukendte = [tag_row(t) for t in pr_tag if t not in gruppe_af]

    def maaned_tags(rx):
        """'Udmeld slut <måned>' / 'Bero slut <måned>' → liste fra denne måned og 12 frem."""
        by_m = {}
        for t in ht["tags"]:
            mm = rx.match(t["navn"])
            if not mm:
                continue
            word = mm.group(1).lower()
            idx = next((i for i, w in enumerate(MAANED_NAVN) if word.startswith(w[:3])), None)
            if idx is not None:
                by_m[idx] = t["tagId"]
        out = []
        for k in range(12):
            idx = (now.month - 1 + k) % 12
            tid = by_m.get(idx)
            out.append({
                "maaned": MAANED_LANG[idx],
                "etiket": navn_af.get(tid) if tid else None,
                "antal": pr_tag.get(tid, 0) if tid else None,
            })
        return out

    def antal(navn):
        return pr_tag.get(id_af_navn.get(navn, ""), 0)

    betalende_sum = sum(antal(n) for n in BETALENDE)

    def mod_sum(personer, tag_sum):
        """Sekundær skjulning: hvis forskellen mellem summen af etiketter og antal
        personer er 1-2, afslører tallet en lille gruppe (medlemmer med to
        etiketter). Så udelades tallet (None)."""
        overlap = tag_sum - personer
        return None if 0 < overlap < MIN_CELLE else skjul(personer)

    medlemskab_sum = sum(pr_tag.get(t["tagId"], 0) for t in ht["tags"] if t["gruppe"] == "medlemskab/produkt")
    med_medlemskab = n_rows - uden_medlemskab
    uden_medlemskab_ud = None if mod_sum(med_medlemskab, medlemskab_sum) is None else skjul(uden_medlemskab)
    betalende_personer_ud = mod_sum(betalende_personer, betalende_sum)
    uden_betalende_ud = None if betalende_personer_ud is None else skjul(uden_betalende)
    # Hvis en måned er skjult, ville "før perioden" + total afsløre den. Udelad så.
    maaned_skjult = any(0 < pr_maaned.get(k, 0) < MIN_CELLE for k in maaneder)
    foer_ud = None if maaned_skjult else skjul(foer_periode)
    udmeld = maaned_tags(UDMELD_RE)
    udm = hent_udmeldinger(hent, id_af_navn.get(UDMELD_ETIKET), antal(UDMELD_ETIKET), now.date(), kald)
    bero = maaned_tags(BERO_RE)

    out = {
        "_om": ("Anonyme optællinger fra goMember (kun GET via GoMemberClient). Ingen navne, numre eller id'er "
                "på medlemmer. Tal for kombinationer vises som \"<3\", når de er 1 eller 2. "
                "Samlede tal er godkendt til offentliggørelse; filen må aldrig indeholde data om enkeltpersoner."),
        "hentet": now.strftime("%Y-%m-%dT%H:%M"),
        "tidszone": "Europe/Copenhagen",
        "kilde": {"kald": kald, "etiketnavne": tag_kilde},
        "total": n_rows,
        "totalFraGoMember": total_felt,
        "noegletal": {
            "medlemmerIAlt": n_rows,
            "betalendeMedlemskaber": {
                "antal": betalende_sum,
                "summeret": BETALENDE,
                "personerMedMindstEn": betalende_personer_ud,
            },
            "oenskerUdmelding": antal("Ønsker udmelding"),
            "pause": antal("Pause"),
            "nyeSeneste30Dage": skjul(nye_30),
        },
        "medlemskaber": gruppe("medlemskab/produkt"),
        "roller": gruppe("system/rolle"),
        "andet": gruppe("andet"),
        "status": [r for r in gruppe("intern status/administration")
                   if not UDMELD_RE.match(r["navn"]) and not BERO_RE.match(r["navn"])],
        "ukendteEtiketter": ukendte,
        "udenEtiketter": skjul(uden_tags),
        "udenMedlemskabsEtiket": uden_medlemskab_ud,
        "udenBetalendeMedlemskab": uden_betalende_ud,
        "nyePrMaaned": [{"maaned": k, "antal": skjul(pr_maaned.get(k, 0))} for k in maaneder],
        "nyeFoerPerioden": foer_ud,
        "udenOprettelsesdato": skjul(uden_dato),
        "udmeldinger": udm,
        "opfoelgning": {
            "oenskerUdmelding": antal("Ønsker udmelding"),
            "pause": antal("Pause"),
            "rykker": antal("Rykker"),
            "manglendeFremmoede": antal("Manglende fremmøde"),
            "beroGebyr": antal("Bero gebyr"),
            "udmeldSlut": udmeld,
            "udmeldSlutIAlt": sum(x["antal"] or 0 for x in udmeld),
            "beroSlut": bero,
            "beroSlutIAlt": sum(x["antal"] or 0 for x in bero),
        },
        "definitioner": [
            {"term": "Udmeldingsdato",
             "tekst": "Feltet \"Udmeldingsdato\" (LeftDate) på medlemmer med etiketten \"Ønsker udmelding\", hentet ét "
                      "medlem ad gangen (GET /api/memberdata/{id}). Kun udmeldings- og indmeldingsdato læses; resten af "
                      "svaret kasseres straks. Siden viser kun måned, aldrig den præcise dato. \"Allerede passeret\" = "
                      "datoen ligger før hentedagen; \"kommende\" = hentedagen eller senere."},
            {"term": "Udmeldinger pr. måned",
             "tekst": "Antal pr. måned vises præcist, også når det er 1 eller 2 – klubben har godkendt samlede tal uden "
                      "navne, og ellers ville grafen være tom. Derfor vises der aldrig andet om de samme personer pr. "
                      "måned (fx medlemstid)."},
            {"term": "Medlemstid ved udmelding",
             "tekst": "Fra indmeldingsdato (JoinedDate) til udmeldingsdato, i grove grupper og kun for hele gruppen. "
                      "Grupper med 1 eller 2 vises som \"<3\"; er kun én gruppe skjult, udelades også den mindste anden "
                      "gruppe, så tallet ikke kan regnes ud. \"Ukendt\" = en af datoerne mangler."},
            {"term": "Medlemmer i alt",
             "tekst": "Antal rækker i goMembers medlemsliste (GET /api/members) på hentetidspunktet. Kan indeholde "
                      "trænere, bestyrelse, udmeldte der stadig står i listen, testkonti og den fiktive "
                      "læse-konto, som denne side selv bruger. Det er ikke det samme som betalende medlemmer."},
            {"term": "Betalende medlemskaber",
             "tekst": "Summen af antal pr. etiket for " + ", ".join(BETALENDE) + ". Et medlem med to af "
                      "etiketterne tælles to gange i summen; \"personer med mindst én\" tæller hvert medlem én gang. "
                      "Om etiketten betyder, at medlemmet betaler lige nu, ved vi ikke – den kan stå tilbage efter "
                      "udmelding eller under pause."},
            {"term": "Antal pr. etiket",
             "tekst": "Hvor mange medlemmer der har etiketten i goMember. Etiketterne er klubbens egne og bruges til "
                      "flere ting på én gang. Et medlem kan have flere etiketter."},
            {"term": "Nye pr. måned / nye seneste 30 dage",
             "tekst": "Baseret på hvornår medlemmet blev oprettet i goMember (createdTs), ikke hvornår medlemskabet "
                      "startede eller blev betalt. Medlemmer flyttet ind fra et andet system kan have importdatoen. "
                      "Måneder med 1 eller 2 vises som \"<3\" af hensyn til anonymitet. Antal oprettet før perioden "
                      "udelades, når en måned er skjult, fordi det ellers kunne regnes ud."},
            {"term": "Udeladte tal",
             "tekst": "Et tal står som \"udeladt\", når det sammen med de andre tal på siden ville afsløre en gruppe "
                      "på 1 eller 2 medlemmer (fx hvor mange der har to medlemskabs-etiketter på én gang)."},
            {"term": "Uden medlemskabs-etiket",
             "tekst": "Medlemmer uden nogen etiket fra gruppen medlemskab/produkt (Premium, Ung, Klippekort, Børn, "
                      "Studerende, PT klippekort, Fordels, 6/12 måneder)."},
            {"term": "Udmeld slut <måned> / Bero slut <måned>",
             "tekst": "Antal med etiketten. Etiketten har intet årstal, så vi ved ikke, om den gælder i år eller er "
                      "glemt fra sidste år. En etiket for en måned, der allerede er gået, kan være forældet."},
            {"term": "Uklare etiketter",
             "tekst": "Vi gætter ikke på betydningen af \"Oprettelse\", \"Alle medlemmer\", \"6 måneder\" "
                      "og \"Bero gebyr\". (\"12 måneder\" er årsabonnementet.) \"Oprettelse\" kan være et oprettelsesgebyr eller en "
                      "markering af nye medlemmer; \"Alle medlemmer\" er ikke sat på alle. Det skal klubben selv afklare."},
        ],
    }
    with open(ud, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return {"medlemmer": n_rows, "kald": kald, "forrige": gl, "udmeldinger": udm}


def main():
    only_struktur = "--struktur" in sys.argv
    hent = Hentning(loft=10, anonym=False)
    try:
        res = byg(hent, ud=OUT, force="--force" in sys.argv, only_struktur=only_struktur)
    except NetFejl as e:
        sys.exit(f"FEJL: {e} Ingen fil skrevet.")
    if res:
        print(f"Skrev {OUT}: {res['medlemmer']} medlemmer, {len(res['kald'])} GET-kald ({', '.join(res['kald'])}).")


if __name__ == "__main__":
    main()
