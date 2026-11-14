#!/usr/bin/env python3
"""
Kortlægning af holdtyper i goMember ud fra de gemte, anonyme snapshots i data/.

Kører helt offline: læser kun filer i data/, adgang.json og (skrivebeskyttet)
../SGSwagger.json. Laver ingen netværkskald og skriver kun holdtyper.json.

    python3 analyse_holdtyper.py            # skriver holdtyper.json + udskriver tal
    python3 analyse_holdtyper.py --quiet    # kun holdtyper.json

Alle tal i HOLDTYPER.md kommer fra udskriften af dette script.
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stier  # noqa: E402

DATA = stier.DATA_DIR
SWAGGER = os.path.join(HERE, "..", "SGSwagger.json")
OUT = os.path.join(stier.KORTLAEG_DIR, "holdtyper.json")

QUIET = "--quiet" in sys.argv
WD = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
WD_SHORT = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]

# Analysevinduer (begrundelse i HOLDTYPER.md afsnit 6). Beregnes ud fra
# øjebliksbilledet længere nede; FULD_PLAN_FRA er en fast dato: før flytningen
# til Industrivej (1/11 2026) var holdplanen ufuldstændig.
FULD_PLAN_FRA = dt.date(2026, 11, 1)
PREBOOK_DAYS = 7           # kommende hold op til 7 dage frem vises særskilt


def out(*a):
    if not QUIET:
        print(*a)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------- indlæsning
acts = load("activity.json")
A = {a["entityId"]: a for a in acts}
tags = load("tag.json")
T = {t["entityId"]: t for t in tags}
products = load("product.json")["products"]
with open(os.path.join(stier.KORTLAEG_DIR, "adgang.json"), encoding="utf-8") as f:
    adgang = json.load(f)
SNAPSHOT_TXT, SNAPSHOT_KILDE = stier.snapshot_tid()
SNAPSHOT = dt.datetime.fromisoformat(SNAPSHOT_TXT)  # lokal tid

events = []
for fn in sorted(glob.glob(os.path.join(DATA, "schedule_*.json"))):
    with open(fn, encoding="utf-8") as f:
        for day in json.load(f):
            events.extend(day["slots"])
assert len({e["entityId"] for e in events}) == len(events), "dubletter i holdplan"

details = {}
for fn in glob.glob(os.path.join(DATA, "event_Activity*.json")):
    with open(fn, encoding="utf-8") as f:
        d = json.load(f)
    details[d["entityId"]] = d
prices = {}
for fn in glob.glob(os.path.join(DATA, "activity_Activity*_price.json")):
    aid = os.path.basename(fn).split("_")[1]
    with open(fn, encoding="utf-8") as f:
        prices[aid] = json.load(f)
price_calls = {}
for ep in adgang["endpoints"]:
    if ep["path"] == "/api/activity/{activityId}/price":
        for c in ep.get("calls", []):
            price_calls[c["path_params"]["activityId"]] = (c["status"], c["kind"], c["item_count"])


def st(e):
    return dt.datetime.fromisoformat(e["startTime"])


def wd(e):
    return st(e).weekday()


def hhmm(e):
    return e["startTime"][11:16]


def ncolor(c):
    return (c or "").lstrip("#").lower()


def trainer_names(e):
    return [r.get("displayName") for r in e.get("responsible", []) if r.get("displayName")]


def tname(t):
    return T.get(t, {}).get("name", t)


def is_materialized(e):
    """Hold med egen gemt record (overstyring). Kendetegn: felterne
    locationName/rules findes kun på disse."""
    return "locationName" in e


for e in events:
    e["_dt"] = st(e)

# Rullende vinduer ud fra holdplanen (8 uger tilbage -> 8 uger frem):
# - grid (standarduge): hele uger fra første mandag i den fulde plan til sidste hele uge
# - belastning: afholdte hold fra den fulde plans start (dog højst holdplanens start)
_first = min(e["_dt"].date() for e in events)
_last = max(e["_dt"].date() for e in events)
_load_from = max(FULD_PLAN_FRA, _first)
_grid_from = _load_from + dt.timedelta(days=(7 - _load_from.weekday()) % 7)
_grid_to = (_last + dt.timedelta(days=1)) - dt.timedelta(days=(_last + dt.timedelta(days=1)).weekday())
if _grid_to <= _grid_from:
    _grid_to = _grid_from + dt.timedelta(days=7)
GRID_FROM, GRID_TO, LOAD_FROM = _grid_from.isoformat(), _grid_to.isoformat(), _load_from.isoformat()

# ------------------------------------------------- holdtype-forslag + mapping
TYPES = [
    # id, navn, beskrivelse
    ("wod", "WOD", "Almindelig WOD med træner (60 min)"),
    ("wod_uden_traener", "WOD uden træner", "Kl. 06-WOD hvor holdet afvikles uden fast træner"),
    ("lang_wod", "Lang WOD", "Søndagens lange WOD (90 min, workout ca. 60 min)"),
    ("hyrox", "HYROX", "HYROX-inspireret træning"),
    ("tons", "TONS", "Hold for øvede (vægtløft/skills)"),
    ("mash", "MASH", "Hold for øvede - lidt mere udfordrende end WOD"),
    ("basis", "Basis/teknik", "Introduktion til basale løft og teknik (8 pladser)"),
    ("boernehold", "Børnehold 5-12 år", "Børnehold"),
    ("rengoering", "Rengøring", "Kalenderblokering: rengøring, ingen tilmelding"),
    ("ungeenhed", "Ungeenheden (ekstern)", "Lokaleudlån til Helsingør Kommunes Ungeenhed, ingen tilmelding"),
    ("ukendt_opstart", "Ukendt engangs-aktivitet", "Aktivitet der kun findes i holdplanen, ikke i /api/activity"),
    ("test", "Test (slet)", "Ressource-testaktivitet fra 2020"),
]
TYPE_NAME = {t[0]: t[1] for t in TYPES}

# activityId -> (type, sikkerhed, note). Sikkerhed: "sikker" | "usikker".
MAPPING = {
    "Activity2516088149026514920": ("wod", "sikker", "Navn 'WOD', tirsdag 08:15"),
    "Activity2516147395982174455": ("wod", "sikker", "Navn 'WOD', torsdag 19:00"),
    "Activity2516363571799491831": ("wod", "sikker", "Aktivitetsnavn 'WOD', hold hedder 'WOD Mandag 1700'"),
    "Activity2516363572535700946": ("wod", "sikker", "Aktivitetsnavn 'WOD', hold hedder 'WOD Mandag 1600'"),
    "Activity2516659546312284291": ("wod", "sikker", ""),
    "Activity2516968090948176157": ("wod", "sikker", ""),
    "Activity2517489994278558056": ("wod", "sikker", ""),
    "Activity2517682293521157937": ("wod", "sikker", ""),
    "Activity2517743103297333604": ("wod", "sikker", ""),
    "Activity2517743104814044562": ("wod", "sikker", ""),
    "Activity2517743105127783782": ("wod", "sikker", ""),
    "Activity2517743105546903012": ("wod", "sikker", ""),
    "Activity2517743106713615054": ("wod", "sikker", ""),
    "Activity2517743114820337813": ("wod", "sikker", ""),
    "Activity2517743115769869245": ("wod", "sikker", ""),
    "Activity2517743116293951096": ("wod", "sikker", ""),
    "Activity2517743126576154536": ("wod", "sikker", ""),
    "Activity2516936776804134130": ("wod", "usikker", "Hvilende 'WOD' (mandag+klippekort, 'For de morgenfriske') - formentlig gammel kl. 06-WOD"),
    "Activity2517743119206731663": ("wod", "usikker", "Hvilende 'WOD' (mandag+klippekort), uden beskrivelse"),
    "Activity2516524686452660410": ("wod_uden_traener", "usikker", "Aktivitet 'WOD Mandag 0600', men 8/10 hold hedder 'WOD uden træner' - og har alligevel en navngiven ansvarlig"),
    "Activity2517091423358347887": ("wod_uden_traener", "usikker", "Aktivitet 'WOD Onsdag 0600', 8/10 hold hedder 'WOD uden træner', 1 'WOD med gæste træner'"),
    "Activity2516464197876025217": ("wod_uden_traener", "usikker", "'MIKKO - uden træner' (maskine-intervaller); ét hold 22/9 kaldt 'WOD uden træner'. Kan også være sin egen type"),
    "Activity2516140240740267054": ("lang_wod", "sikker", ""),
    "Activity2517743102480462084": ("lang_wod", "sikker", "Hvilende forgænger 'WOD (Laaang workout)'"),
    "Activity2516147394819805210": ("hyrox", "sikker", "'Hyrox' lørdag - samme type som 'HYROX' onsdag, men andre indstillinger"),
    "Activity2516277445812201999": ("hyrox", "sikker", ""),
    "Activity2516233711301680950": ("tons", "sikker", ""),
    "Activity2517147997087724635": ("tons", "sikker", "Hvilende 'Tons'"),
    "Activity2517743036997736134": ("tons", "sikker", "Hvilende 'TONS' fra 2021"),
    "Activity2516244060202738431": ("mash", "sikker", ""),
    "Activity2517743036073189885": ("mash", "sikker", "Hvilende 'Mash' fra 2021"),
    "Activity2516421299835599010": ("basis", "sikker", ""),
    "Activity2516270957033362421": ("boernehold", "sikker", ""),
    "Activity2516098606059431091": ("rengoering", "sikker", "Søndag"),
    "Activity2516098608171825494": ("rengoering", "sikker", "Onsdag"),
    "Activity2516450766430710625": ("rengoering", "sikker", "Hvilende 'Rengøring - begrænset træning muligt'"),
    "Activity2516450767014171449": ("rengoering", "sikker", "Hvilende 'Rengøring - Begrænset træning muligt'"),
    "Activity2516102807417331666": ("ungeenhed", "sikker", ""),
    "Activity2517989352260288292": ("test", "sikker", "activityMode 'resource', 1 plads"),
    "Activity2516351285377140362": ("ukendt_opstart", "usikker", "Findes ikke i /api/activity; 6 hold 25.-27/9 med navnene WOD/MASH/LANG WOD - ligner en opstarts-/eventweekend"),
}

# alle activityId'er (fra listen + dem der kun ses i holdplanen)
all_aids = list(A) + sorted({e["activityId"] for e in events} - set(A))
missing = [a for a in all_aids if a not in MAPPING]
# Nye aktiviteter, som mappingen ikke kender, må ikke stoppe den natlige
# opdatering: de lægges i typen "ukendt" og nævnes i opsummeringen.
UNKNOWN = []
if missing:
    TYPES.append(("ukendt", "Ukendt (ny aktivitet)", "Aktivitet som holdtype-mappingen ikke kender endnu - skal placeres manuelt i analyse_holdtyper.py"))
    TYPE_NAME["ukendt"] = TYPES[-1][1]
    for aid in missing:
        nm = (A.get(aid) or {}).get("name") or next((e["name"] for e in events if e["activityId"] == aid), None)
        MAPPING[aid] = ("ukendt", "usikker", f"Ny/ukendt aktivitet ({nm or 'uden navn'}) - ikke mappet endnu")
        UNKNOWN.append({"activityId": aid, "navn": nm})

by_act = collections.defaultdict(list)
for e in events:
    by_act[e["activityId"]].append(e)
for L in by_act.values():
    L.sort(key=lambda e: e["startTime"])

out("=" * 70)
out("GRUNDTAL")
out(f"Snapshot: {SNAPSHOT}  aktiviteter i /api/activity: {len(acts)}  tags: {len(tags)}  hold i holdplan: {len(events)}")
out(f"Holdplan-vindue: {min(e['startTime'] for e in events)} .. {max(e['startTime'] for e in events)}")
out(f"Aktiviteter med hold i vinduet: {len(by_act)} (heraf ikke i /api/activity: {len(set(by_act)-set(A))})")
out("activityMode:", dict(collections.Counter(a["activityMode"] for a in acts)))
out("Hold pr. måned:", dict(sorted(collections.Counter(e["startTime"][:7] for e in events).items())))

# ---------------------------------------------------------------- 1 datamodel
out("=" * 70)
out("1. DATAMODEL")
seq_eq = collections.Counter(("sequence" in e, e.get("sequence") == e["activityId"]) for e in events)
out("sequence (findes, == activityId):", dict(seq_eq))
out("isParent:", dict(collections.Counter(e["isParent"] for e in events)),
    "isSuperEvent(event):", dict(collections.Counter(e["isSuperEvent"] for e in events)),
    "isSuperEvent(activity):", dict(collections.Counter(a["isSuperEvent"] for a in acts)),
    "isGroup:", dict(collections.Counter(a["isGroup"] for a in acts)))
out("eventId == startTime som yyyyMMddHHmm:",
    sum(e["eventId"] == e["_dt"].strftime("%Y%m%d%H%M") for e in events), "af", len(events))
bad_id = [e for e in events if e["eventId"] != e["_dt"].strftime("%Y%m%d%H%M")]
id_kinds = collections.Counter()
for e in bad_id:
    if re.fullmatch(r"\d{12}", e["eventId"]):
        delta = (e["_dt"] - dt.datetime.strptime(e["eventId"], "%Y%m%d%H%M")).total_seconds() / 60
        id_kinds[f"{A.get(e['activityId'],{}).get('name','?')}: eventId {int(delta):+d} min fra starttid"] += 1
    else:
        id_kinds[f"{A.get(e['activityId'],{}).get('name','(ukendt aktivitet)')}: eventId med bogstav-suffiks, fx {e['eventId']}"] += 1
out("  afvigende eventId'er:", dict(id_kinds))
out("createdTs (dato) på genererede hold, top 5:", collections.Counter(e["createdTs"][:10] for e in events if not is_materialized(e)).most_common(5))
out("entityId == activityId-eventId:",
    sum(e["entityId"] == f"{e['activityId']}-{e['eventId']}" for e in events), "af", len(events))
out("inviteTags:", dict(collections.Counter(json.dumps(e["inviteTags"]) for e in events)),
    "inviteMembers:", dict(collections.Counter(json.dumps(e["inviteMembers"]) for e in events)),
    "formDefinition:", dict(collections.Counter(json.dumps(e["formDefinition"]) for e in events)))
mat = [e for e in events if is_materialized(e)]
virt = [e for e in events if not is_materialized(e)]
out(f"Hold med egen record (har locationName/rules): {len(mat)}; uden (genereret fra serien): {len(virt)}")
out("  navngiven træner blandt med egen record:", sum(bool(trainer_names(e)) for e in mat), "/", len(mat))
out("  navngiven træner blandt genererede:", sum(bool(trainer_names(e)) for e in virt), "/", len(virt))
out("  signUpDeadline blandt med egen record:", sum("signUpDeadline" in e for e in mat), "; blandt genererede:", sum("signUpDeadline" in e for e in virt))
out("  meetTime blandt med egen record:", sum("meetTime" in e for e in mat), "; blandt genererede:", sum("meetTime" in e for e in virt))
# Antal responsible-objekter på genererede hold vs aktivitetens responsibleUsersIds
cnt_match = collections.Counter()
for e in virt:
    a = A.get(e["activityId"])
    if a:
        cnt_match[len(e["responsible"]) == a["responsibleUsersIds"]["_count"]] += 1
out("  genererede hold: antal responsible == aktivitetens responsibleUsersIds._count:", dict(cnt_match))
out("  responsible-liste tom (ingen ansvarlig overhovedet):", sum(len(e["responsible"]) == 0 for e in events))

# Felter: aktivitet vs. hold
act_fields = set().union(*[set(a) for a in acts])
ev_fields = set().union(*[set(e) for e in events]) - {"_dt"}
out("Felter kun på aktivitet:", sorted(act_fields - ev_fields))
out("Felter kun på hold:", sorted(ev_fields - act_fields))
shared = sorted((act_fields & ev_fields) - {"createdTs", "modifiedTs", "entityId"})
out("Fælles felter:", shared)

# Hvilke felter varierer mellem hold af samme aktivitet?
PER_EVENT_ALWAYS = {"entityId", "eventId", "startTime", "endTime", "startTimeUtc", "endTimeUtc", "meetTime",
                    "meetTimeUtc", "signUpDeadline", "signUpDeadlineUtc", "booked", "waitingList", "createdTs",
                    "modifiedTs", "_dt", "status", "cancellationMessage"}
var_fields = collections.Counter()
var_examples = {}
for aid, L in by_act.items():
    if len(L) < 2:
        continue
    for k in ev_fields - PER_EVENT_ALWAYS:
        vals = {json.dumps(e.get(k, "<mangler>"), sort_keys=True, ensure_ascii=False) for e in L}
        if len(vals) > 1:
            var_fields[k] += 1
            var_examples.setdefault(k, (A.get(aid, {}).get("name", aid), sorted(vals)[:4]))
never_vary = sorted((ev_fields - PER_EVENT_ALWAYS) - set(var_fields))
out("Felter der varierer inden for mindst én aktivitet (antal aktiviteter):", dict(var_fields.most_common()))
for k, (n, v) in var_examples.items():
    out(f"   eks. {k}: {n}: {[x[:50] for x in v]}")
out("Felter der aldrig varierer inden for en aktivitet:", never_vary)

# Holdværdi vs. aktivitetens standard
CMP = ["name", "color", "maxAttendees", "hasWaitingList", "registerAttendance", "onlineSignup", "description",
       "tagsAssigned", "onlyLoggedIn", "allowNonMember", "attendancePrivacy", "maxGuestsPerMember", "hideFromOverview",
       "allowPartner", "allowInvite"]


def norm(k, v):
    if k == "color":
        return ncolor(v)
    if k == "maxAttendees":
        return v or 0
    if k == "tagsAssigned":
        return sorted(v)
    return v


override = {k: collections.Counter() for k in CMP}
for e in events:
    a = A.get(e["activityId"])
    if not a:
        continue
    for k in CMP:
        diff = norm(k, e.get(k)) != norm(k, a.get(k))
        override[k][("egen record" if is_materialized(e) else "genereret", diff)] += 1
out("Hold der afviger fra aktivitetens standardværdi (genereret/egen record):")
override_summary = {}
for k in CMP:
    c = override[k]
    g = c[("genereret", True)], c[("genereret", True)] + c[("genereret", False)]
    m = c[("egen record", True)], c[("egen record", True)] + c[("egen record", False)]
    override_summary[k] = {"genereret_afviger": g[0], "genereret_i_alt": g[1], "egen_record_afviger": m[0], "egen_record_i_alt": m[1]}
    out(f"   {k:20s} genereret {g[0]:3d}/{g[1]}   egen record {m[0]:3d}/{m[1]}")
# Felter der afviger allerede på de genererede hold => serie-skabelon (sequence) har egne værdier
series_level = [k for k in CMP if override_summary[k]["genereret_afviger"] > 0]
out("Felter hvor serie-skabelonen afviger fra aktiviteten (ses på genererede hold):", series_level)

# Anonym holdplan vs. detaljekald
out("Holdplan vs. detaljekald (/api/event/{id}) for de samme hold:")
sched_by_id = {e["entityId"]: e for e in events}
detail_diff = collections.Counter()
for eid, d in sorted(details.items()):
    s = sched_by_id.get(eid)
    if not s:
        out("   ", eid, "ikke i holdplanen")
        continue
    for k in ["activityHasPrice", "paymentRules", "registerAttendance", "maxAttendees", "booked", "signupOpen", "name"]:
        if s.get(k) != d.get(k):
            detail_diff[k] += 1
            out(f"    {d['name']} {eid[-12:]} {k}: holdplan={s.get(k)!r} detalje={d.get(k)!r}")
    out(f"    {d['name']}: noShowPrice={d.get('noShowPrice')!r} prices={d.get('prices')!r}")
out("Priskald pr. aktivitet:", {A.get(k, {}).get("name", k): v for k, v in price_calls.items()})
for aid, P in prices.items():
    for p in P:
        out(f"    {A.get(aid, {}).get('name', aid)}: priceType={p['priceType']} price={p['price']} currency={p.get('currency','')} tag={T.get(p['tag'],{}).get('name', p['tag'])}")

# ---------------------------------------------------------------- 2 inventar
out("=" * 70)
out(f"2. INVENTAR ({len(acts)} aktiviteter + aktiviteter kun i holdplan)")
inventory = []
for aid in all_aids:
    a = A.get(aid)
    L = by_act.get(aid, [])
    typ, sikkerhed, note = MAPPING[aid]
    slots = collections.Counter((WD[e["_dt"].weekday()], hhmm(e), e["endTime"][11:16]) for e in L)
    trainers = collections.Counter(n for e in L for n in trainer_names(e))
    row = {
        "activityId": aid,
        "navn": a["name"] if a else None,
        "i_activity_listen": bool(a),
        "holdnavne_i_planen": dict(collections.Counter(e["name"] for e in L)),
        "type": typ,
        "type_sikkerhed": sikkerhed,
        "note": note,
        "farve": ncolor(a["color"]) if a else None,
        "farver_i_planen": dict(collections.Counter(ncolor(e["color"]) for e in L)),
        "kapacitet": a["maxAttendees"] if a else None,
        "kapaciteter_i_planen": {str(k): v for k, v in collections.Counter(e.get("maxAttendees") for e in L).items()},
        "venteliste": a["hasWaitingList"] if a else None,
        "onlineSignup": a["onlineSignup"] if a else None,
        "onlyLoggedIn": a["onlyLoggedIn"] if a else None,
        "allowNonMember": a["allowNonMember"] if a else None,
        "registerAttendance": a["registerAttendance"] if a else None,
        "activityMode": a["activityMode"] if a else None,
        "tags": [T.get(t, {}).get("name", t) for t in (a["tagsAssigned"] if a else [])],
        "tags_i_planen": dict(collections.Counter(", ".join(T.get(t, {}).get("name", t) for t in e["tagsAssigned"]) or "(ingen)" for e in L)),
        "antal_standard_ansvarlige": a["responsibleUsersIds"]["_count"] if a else None,
        "status": "aktiv" if L and max(e["startTime"] for e in L) >= SNAPSHOT.isoformat() else ("kun fortid" if L else "hvilende"),
        "antal_hold": len(L),
        "foerste_hold": L[0]["startTime"] if L else None,
        "sidste_hold": L[-1]["startTime"] if L else None,
        "ugedag_tid": [f"{w} {s}-{e2} ({n})" for (w, s, e2), n in sorted(slots.items(), key=lambda x: (WD.index(x[0][0]), x[0][1]))],
        "traenere_navngivne": dict(trainers.most_common()),
        "hold_uden_navngiven_traener": sum(not trainer_names(e) for e in L),
        "statusser": dict(collections.Counter(e["status"] for e in L)),
        "oprettet": a["createdTs"][:10] if a else None,
        "sidst_aendret": a["modifiedTs"][:10] if a else None,
        "pris_klip": None,
        "udeblivelsesgebyr": None,
    }
    if aid in prices:
        for p in prices[aid]:
            if p["priceType"] == "perOnlineSignup":
                row["pris_klip"] = f"{p['price']:g} {p.get('currency','')} pr. online-tilmelding (tag: {T.get(p['tag'],{}).get('name', p['tag'])})"
            if p["priceType"] == "noShow":
                row["udeblivelsesgebyr"] = p["price"]
    elif aid in price_calls:
        row["pris_klip"] = "ingen prisregler (tomt svar)"
    # deadline: forskel startTime - signUpDeadline på de hold der har feltet
    dl = collections.Counter()
    for e in L:
        if "signUpDeadline" in e:
            ddl = dt.datetime.fromisoformat(e["signUpDeadlineUtc"].rstrip("Z")[:16])  # minutpræcision
            if ddl == dt.datetime.fromisoformat(e["endTimeUtc"].rstrip("Z")[:16]):
                dl["ved holdets slut"] += 1
            elif ddl == dt.datetime.fromisoformat(e["startTimeUtc"].rstrip("Z")[:16]):
                dl["ved holdets start"] += 1
            else:
                dl[f"{int((ddl - dt.datetime.fromisoformat(e['startTimeUtc'].rstrip('Z'))).total_seconds() // 60)} min efter start"] += 1
    row["tilmeldingsfrist"] = dict(dl)
    inventory.append(row)

for r in inventory:
    out(f"- [{r['activityId'][-6:]}] {r['navn']!r} -> {r['type']} ({r['type_sikkerhed']}) | {r['status']} | hold={r['antal_hold']} "
        f"| kap={r['kapacitet']} vl={r['venteliste']} online={r['onlineSignup']} fremmøde={r['registerAttendance']} "
        f"| farve={r['farve']} | tags={r['tags']} | {', '.join(r['ugedag_tid'])} | trænere={r['traenere_navngivne']} "
        f"| uden navn={r['hold_uden_navngiven_traener']} | ansv.std={r['antal_standard_ansvarlige']} | frist={r['tilmeldingsfrist']} "
        f"| klip={r['pris_klip']} noshow={r['udeblivelsesgebyr']} | opr={r['oprettet']} ændr={r['sidst_aendret']}")
stat_c = collections.Counter(r["status"] for r in inventory if r["i_activity_listen"])
out(f"Status for de {len(acts)} i /api/activity:", dict(stat_c))
out(f"Ens på tværs af alle {len(acts)}: ", {k: dict(collections.Counter(str(a[k]) for a in acts)) for k in
                                  ["onlyLoggedIn", "allowNonMember", "maxGuestsPerMember", "hideFromOverview", "allowSingle", "allowRecurring", "isSuperEvent", "eventsCount", "invitationMedia", "autoPromote", "minAttendees"]})
fr = collections.Counter(k for r in inventory for k, v in r["tilmeldingsfrist"].items() for _ in range(v))
out("Tilmeldingsfrist på hold med feltet (signUpDeadlineUtc):", dict(fr), "; hold uden felt:", sum("signUpDeadline" not in e for e in events))
out("registerAttendance på aktivitet:", dict(collections.Counter(a["registerAttendance"] for a in acts)),
    "på hold:", dict(collections.Counter(e["registerAttendance"] for e in events)))

# ---------------------------------------------------------------- 3 navngivning
out("=" * 70)
out("3. NAVNEMØNSTER")
pat = re.compile(r"^WOD (Mandag|Tirsdag|Onsdag|Torsdag|Fredag|Lørdag|Søndag) (\d{2})(\d{2})$")
named_slot = [a for a in acts if pat.match(a["name"])]
out(f"Aktiviteter navngivet 'WOD <Ugedag> <hhmm>': {len(named_slot)}")
mism = []
for a in named_slot:
    m = pat.match(a["name"])
    L = by_act.get(a["entityId"], [])
    ok = sum(WD[e["_dt"].weekday()] == m.group(1) and hhmm(e) == f"{m.group(2)}:{m.group(3)}" for e in L)
    if ok != len(L):
        mism.append((a["name"], ok, len(L)))
out("  heraf hvor navnet ikke passer med holdenes ugedag/tid:", mism)
ev_named_slot = {e["activityId"] for e in events if pat.match(e["name"])}
out("Aktiviteter hvis hold (i planen) bærer et 'WOD <Ugedag> <hhmm>'-navn:", len(ev_named_slot))
name_counts = collections.Counter(a["name"] for a in acts)
out("Aktivitetsnavne brugt mere end én gang:", {k: v for k, v in name_counts.items() if v > 1})
ci = collections.defaultdict(set)
for a in acts:
    ci[a["name"].lower()].add(a["name"])
out("Navne der kun adskiller sig ved store/små bogstaver:", [sorted(v) for v in ci.values() if len(v) > 1])
type_acts = collections.defaultdict(list)
for r in inventory:
    type_acts[r["type"]].append(r)
out("Aktiviteter pr. foreslået type (alle / aktive):")
for t, _, _ in TYPES:
    rs = type_acts.get(t, [])
    out(f"   {TYPE_NAME[t]:28s} {len(rs):2d} / {sum(r['status']=='aktiv' for r in rs):2d}")
active_acts = [r for r in inventory if r["status"] == "aktiv"]
out(f"Aktive aktiviteter: {len(active_acts)} -> {len({r['type'] for r in active_acts})} typer")
out("Usikre mappinger:", [(r["navn"] or r["activityId"], r["note"]) for r in inventory if r["type_sikkerhed"] == "usikker"])

# ---------------------------------------------------------------- 4 tags
out("=" * 70)
out("4. TAGS")
WEEKDAY_CAT = "TC2517985027101079731"


def tag_group(t):
    n = t["name"].lower()
    if t["category"] == WEEKDAY_CAT:
        return "ugedag"
    if n.startswith("udmeld slut") or n.startswith("bero slut") or n in ("bero gebyr", "pause", "ønsker udmelding", "rykker", "manglende fremmøde"):
        return "intern status/administration"
    if t["entityId"] in ("Tag1", "Tag2") or n in ("trænere", "bestyrelsesmedlem"):
        return "system/rolle"
    if n in ("premium medlemskab", "ung 15-24 år medlemskab", "klippekort (10 klip)", "børnemedlemsskab 7-14",
             "fordels medlemskab", "6 måneder", "12 måneder", "pt klippekort", "studerende"):
        return "medlemskab/produkt"
    return "andet"


tag_rows = []
used_on_events = collections.Counter(t for e in events for t in e["tagsAssigned"])
used_on_acts = collections.Counter(t for a in acts for t in a["tagsAssigned"])
product_ids = {p["id"] for p in products}
for t in tags:
    tag_rows.append({
        "tagId": t["entityId"], "navn": t["name"], "gruppe": tag_group(t), "kategori": t["category"] or None,
        "tagType": t["tagType"], "oprettet": t["createdTs"][:10], "er_produkt": t["entityId"] in product_ids,
        "brugt_paa_aktiviteter": used_on_acts.get(t["entityId"], 0), "brugt_paa_hold": used_on_events.get(t["entityId"], 0),
    })
grp = collections.Counter(r["gruppe"] for r in tag_rows)
out("Tag-grupper:", dict(grp))
for g in grp:
    out(f"   {g}: {[r['navn'] for r in tag_rows if r['gruppe']==g]}")
out("Kategorier:", dict(collections.Counter(t["category"] or "(ingen)" for t in tags)))
out("tagType:", dict(collections.Counter(t["tagType"] for t in tags)))
months = ["jan", "feb", "marts", "april", "maj", "juni", "juli", "august", "sep", "okt", "nov", "dec"]
for prefix in ("Udmeld slut", "Bero slut"):
    have = [t["name"][len(prefix) + 1:] for t in tags if t["name"].startswith(prefix)]
    out(f"   '{prefix} ...': {len(have)} stk, mangler måned: {[m for m in months if m not in have]}")
out("Tags brugt på hold:", {tname(t): n for t, n in used_on_events.most_common()})
out("Tags brugt på aktiviteter:", {tname(t): n for t, n in used_on_acts.most_common()})
combo = collections.Counter(tuple(tname(t) for t in e["tagsAssigned"]) for e in events)
out("Tag-kombinationer på hold:", {", ".join(k) or "(ingen)": v for k, v in combo.most_common()})
# ugedags-tag passer med holdets ugedag?
wdtag = {t["entityId"]: t["name"] for t in tags if t["category"] == WEEKDAY_CAT}
wd_ok = collections.Counter()
for e in events:
    w = [wdtag[t] for t in e["tagsAssigned"] if t in wdtag]
    if not w:
        wd_ok["ingen ugedags-tag"] += 1
    elif all(x == WD[e["_dt"].weekday()].lower() for x in w):
        wd_ok["passer"] += 1
    else:
        wd_ok["passer IKKE"] += 1
out("Ugedags-tag vs. holdets ugedag:", dict(wd_ok))
by_type_tags = collections.defaultdict(collections.Counter)
for e in events:
    by_type_tags[MAPPING[e["activityId"]][0]][", ".join(tname(t) for t in e["tagsAssigned"] if t not in wdtag) or "(ingen ud over ugedag)"] += 1
out("Ikke-ugedags-tags pr. type:", {TYPE_NAME[k]: dict(v) for k, v in by_type_tags.items()})
missing_tag_refs = sorted({p["tagRequired"] for p in products if p.get("tagRequired") and p["tagRequired"] not in T})
out("tagRequired i product.json der ikke findes i tag.json:", missing_tag_refs,
    [p["name"] for p in products if p.get("tagRequired") in missing_tag_refs])
out("Produkter (displayPrice = månedspris):", [(p["name"], p["displayPrice"], p.get("ageFrom"), p.get("ageTo")) for p in products])

# ---------------------------------------------------------------- 5 ugerytme
out("=" * 70)
out("5. UGERYTME")
grid_ev = [e for e in events if GRID_FROM <= e["startTime"][:10] < GRID_TO]
weeks = sorted({e["_dt"].isocalendar()[1] for e in grid_ev})
nweeks = len(weeks)
out(f"Grid-vindue {GRID_FROM}..{GRID_TO} (eksklusiv): {len(grid_ev)} hold, {nweeks} uger: {weeks}")
slot_c = collections.defaultdict(collections.Counter)
for e in grid_ev:
    slot_c[(e["_dt"].weekday(), hhmm(e), e["endTime"][11:16])][MAPPING[e["activityId"]][0]] += 1
standard_week = []
for (w, s, en), c in sorted(slot_c.items()):
    typ, n = c.most_common(1)[0]
    acts_in_slot = sorted({e["activityId"] for e in grid_ev if e["_dt"].weekday() == w and hhmm(e) == s})
    standard_week.append({"ugedag": WD[w], "ugedag_nr": w, "start": s, "slut": en, "type": typ, "type_navn": TYPE_NAME[typ],
                          "uger_med_hold": sum(c.values()), "uger_i_alt": nweeks,
                          "activityIds": acts_in_slot,
                          "aktivitetsnavne": [A[x]["name"] if x in A else x for x in acts_in_slot]})
out("Standarduge (slot: type, antal uger med hold / uger):")
for r in standard_week:
    out(f"   {r['ugedag']:8s} {r['start']}-{r['slut']}  {r['type_navn']:24s} {r['uger_med_hold']}/{nweeks}  {r['aktivitetsnavne']}")
out(f"Slots i standardugen: {len(standard_week)}; hold-slots pr. uge excl. rengøring/ungeenhed: "
    f"{sum(1 for r in standard_week if r['type'] not in ('rengoering','ungeenhed'))}")
per_day = collections.Counter(r["ugedag"] for r in standard_week if r["type"] not in ("rengoering", "ungeenhed"))
out("Træningshold pr. ugedag:", {d: per_day[d] for d in WD})
per_type_week = collections.Counter(r["type_navn"] for r in standard_week)
out("Slots pr. type i standardugen:", dict(per_type_week))
# grid i matrix-form (tid x ugedag)
times = sorted({r["start"] for r in standard_week})
grid_matrix = {t: {d: None for d in WD} for t in times}
for r in standard_week:
    grid_matrix[r["start"]][r["ugedag"]] = r["type_navn"]
out("Matrix:")
out("   " + "tid   " + " | ".join(f"{d[:3]:14s}" for d in WD))
for t in times:
    out("   " + t + " " + " | ".join(f"{(grid_matrix[t][d] or '-')[:14]:14s}" for d in WD))

# Afvigelser: manglende uger pr. slot (helligdage?), aflyste, engangsnavne
full_from, full_to = _load_from, _last
out(f"Manglende datoer pr. slot i hele perioden {full_from}..{full_to}:")
holes = []
for r in standard_week:
    dates = {e["_dt"].date() for e in events if e["activityId"] in r["activityIds"]
             and e["_dt"].weekday() == r["ugedag_nr"] and hhmm(e) == r["start"]}
    r["foerste_dato"], r["sidste_dato"] = min(dates).isoformat(), max(dates).isoformat()
    d = max(full_from, min(dates))
    while d <= min(full_to, max(dates)):
        if d.weekday() == r["ugedag_nr"] and d not in dates:
            holes.append({"ugedag": r["ugedag"], "start": r["start"], "type": r["type_navn"], "dato": d.isoformat()})
        d += dt.timedelta(days=1)
for h in holes:
    out(f"   mangler {h['dato']} {h['ugedag']} {h['start']} {h['type']}")
out("   (i alt", len(holes), "huller mellem første og sidste forekomst)")
_wk1 = (_load_from + dt.timedelta(days=6)).isoformat()
out(f"Slots der starter senere end {LOAD_FROM}..{_wk1}:", [(r["ugedag"], r["start"], r["type_navn"], r["foerste_dato"]) for r in standard_week if r["foerste_dato"] > _wk1])
HOLI = {f"{y}-{md}": n for y in sorted({e["startTime"][:4] for e in events})
        for md, n in (("12-24", "juleaften"), ("12-25", "1. juledag"), ("12-26", "2. juledag"),
                      ("12-31", "nytårsaften"), ("01-01", "nytårsdag"))
        if _first.isoformat() <= f"{y}-{md}" <= _last.isoformat()}
holiday_events = {f"{d} ({n})": [f"{e['startTime'][11:16]} {e['name']} [{e['status']}]" for e in events if e["startTime"][:10] == d] for d, n in HOLI.items()}
out("Hold på hellig-/højtidsdage:", {k: len(v) for k, v in holiday_events.items()})
for k, v in holiday_events.items():
    out("   ", k, v)
out(f"Status-fordeling (alle {len(events)}):", dict(collections.Counter(e["status"] for e in events)))
out("Aflyste hold:")
cancelled = []
for e in sorted(events, key=lambda e: e["startTime"]):
    if e["status"] == "cancelled":
        cancelled.append({"dato": e["startTime"], "navn": e["name"], "type": TYPE_NAME[MAPPING[e["activityId"]][0]],
                          "besked": e.get("cancellationMessage", ""), "booked": e["booked"]})
        out(f"   {e['startTime']} {e['name']!r} besked={e.get('cancellationMessage','')!r} booked={e['booked']}")
# 'booked'-status vs. tal
bk = collections.Counter()
for e in events:
    full = e.get("maxAttendees") and e["booked"] >= e["maxAttendees"]
    bk[(e["status"], bool(full))] += 1
out("status x (booked >= max):", {f"{k[0]}/{'fuld' if k[1] else 'ikke fuld'}": v for k, v in bk.items()})
over = [(e["startTime"], e["name"], e["booked"], e["maxAttendees"]) for e in events if e.get("maxAttendees") and e["booked"] > e["maxAttendees"]]
out("Hold med booked > maxAttendees:", over)
# engangs: hold uden for standard-slots, navne-overstyringer, beskrivelses-overstyringer
std_keys = {(r["ugedag_nr"], r["start"]) for r in standard_week}
oneoffs = [e for e in events if (e["_dt"].weekday(), hhmm(e)) not in std_keys]
out(f"Hold uden for standard-slots: {len(oneoffs)}")
for e in oneoffs:
    out(f"   {e['startTime']} {e['name']!r} [{e['activityId'][-6:]}] status={e['status']} booked={e['booked']}")
name_over = collections.Counter()
for e in events:
    a = A.get(e["activityId"])
    if a and e["name"] != a["name"]:
        name_over[(a["name"], e["name"])] += 1
out("Holdnavn ≠ aktivitetsnavn:", {f"{k[0]} -> {k[1]}": v for k, v in name_over.items()})
desc_over = [(e["startTime"][:10], e["name"], re.sub("<[^>]+>", "", e["description"]).strip()[:40]) for e in events
             if A.get(e["activityId"]) and e["description"] != A[e["activityId"]]["description"] and e["description"]]
out("Hold med egen beskrivelse (≠ aktivitetens):", desc_over)
cap_over = [(e["startTime"][:16], e["name"], e.get("maxAttendees"), A[e["activityId"]]["maxAttendees"]) for e in events
            if A.get(e["activityId"]) and (e.get("maxAttendees") or 0) != A[e["activityId"]]["maxAttendees"]]
out("Hold med anden kapacitet end aktiviteten:", cap_over)
# Sep-okt
early = [e for e in events if e["startTime"] < LOAD_FROM]
out(f"Hold før {LOAD_FROM}: {len(early)}; pr. type:", dict(collections.Counter(TYPE_NAME[MAPPING[e['activityId']][0]] for e in early)))

# ---------------------------------------------------------------- 6 belastning
out("=" * 70)
out("6. BELASTNING")


def load_stats(L):
    L = [e for e in L if e.get("maxAttendees")]
    cap = sum(e["maxAttendees"] for e in L)
    b = sum(e["booked"] for e in L)
    return {"hold": len(L), "kapacitet": cap, "tilmeldt": b,
            "fyldning_pct": round(100 * b / cap, 1) if cap else None,
            "venteliste_i_alt": sum(e["waitingList"] for e in L),
            "hold_med_venteliste": sum(e["waitingList"] > 0 for e in L),
            "fuldt_booket": sum(e["booked"] >= e["maxAttendees"] for e in L),
            "snit_tilmeldt": round(b / len(L), 1) if L else None}


# Begrundelse for vinduet: tilmeldinger som funktion af dage frem
lead = collections.defaultdict(list)
for e in events:
    if e.get("maxAttendees") and e["status"] != "cancelled" and e["startTime"] >= LOAD_FROM:
        days = (e["_dt"] - SNAPSHOT).total_seconds() / 86400
        b = "afholdt" if days < 0 else ("0-7 dage frem" if days <= 7 else ("8-14" if days <= 14 else ("15-28" if days <= 28 else "29+")))
        lead[b].append(e["booked"] / e["maxAttendees"])
lead_stats = {k: {"hold": len(v), "snit_fyldning_pct": round(100 * statistics.mean(v), 1)} for k, v in lead.items()}
out("Fyldning efter afstand til snapshot (ikke-aflyste hold med loft, fra 1/11):", lead_stats)
done = [e for e in events if LOAD_FROM <= e["startTime"] and e["_dt"] < SNAPSHOT]
done_ok = [e for e in done if e["status"] != "cancelled" and e.get("maxAttendees")]
excl = collections.Counter()
for e in events:
    if e["startTime"] < LOAD_FROM:
        excl["før 1/11 (ufuldstændig holdplan)"] += 1
    elif e["_dt"] >= SNAPSHOT:
        excl["fremtidige (tilmelding ikke afsluttet)"] += 1
    elif e["status"] == "cancelled":
        excl["aflyst"] += 1
    elif not e.get("maxAttendees"):
        excl["intet pladsloft (rengøring/ungeenhed)"] += 1
out(f"Belastnings-grundlag: afholdte hold {LOAD_FROM}..snapshot: {len(done)}, heraf brugt: {len(done_ok)}; udeladt:", dict(excl))
load_by_type = {}
for t, _, _ in TYPES:
    L = [e for e in done_ok if MAPPING[e["activityId"]][0] == t]
    if L:
        load_by_type[t] = load_stats(L)
        out(f"   {TYPE_NAME[t]:24s} {load_by_type[t]}")
load_total = load_stats(done_ok)
out("   I ALT", load_total)
load_by_slot = []
slot_groups = collections.defaultdict(list)
for e in done_ok:
    slot_groups[(e["_dt"].weekday(), hhmm(e))].append(e)
out("Pr. ugedag/tid (afholdte):")
for (w, s), L in sorted(slot_groups.items()):
    r = load_stats(L)
    r.update({"ugedag": WD[w], "start": s, "type": TYPE_NAME[MAPPING[L[0]["activityId"]][0]],
              "detaljer": [f"{e['startTime'][:10]}: {e['booked']}/{e['maxAttendees']}" + (f" (+{e['waitingList']} vl)" if e['waitingList'] else "") for e in L]})
    load_by_slot.append(r)
    out(f"   {WD[w]:8s} {s} {r['type']:20s} hold={r['hold']} {r['tilmeldt']}/{r['kapacitet']} = {r['fyldning_pct']}%  vl={r['venteliste_i_alt']} fuld={r['fuldt_booket']}  {r['detaljer']}")
by_wd = collections.defaultdict(list)
for e in done_ok:
    by_wd[e["_dt"].weekday()].append(e)
load_by_weekday = {WD[w]: load_stats(L) for w, L in sorted(by_wd.items())}
out("Pr. ugedag (afholdte):", {k: (v["tilmeldt"], v["kapacitet"], v["fyldning_pct"]) for k, v in load_by_weekday.items()})
by_tod = collections.defaultdict(list)
for e in done_ok:
    h = e["_dt"].hour
    by_tod["morgen (<10)" if h < 10 else ("formiddag (10-15)" if h < 15 else "eftermiddag/aften (≥15)")].append(e)
load_by_tod = {k: load_stats(v) for k, v in by_tod.items()}
out("Pr. tid på dagen (afholdte):", {k: (v["hold"], v["tilmeldt"], v["kapacitet"], v["fyldning_pct"]) for k, v in load_by_tod.items()})
pre = [e for e in events if e["_dt"] >= SNAPSHOT and (e["_dt"] - SNAPSHOT).days < PREBOOK_DAYS and e["status"] != "cancelled" and e.get("maxAttendees")]
prebook_by_type = {TYPE_NAME[t]: load_stats([e for e in pre if MAPPING[e["activityId"]][0] == t]) for t in sorted({MAPPING[e["activityId"]][0] for e in pre})}
out(f"Forhåndsbooking næste {PREBOOK_DAYS} dage ({len(pre)} hold):", {k: (v["tilmeldt"], v["kapacitet"], v["fyldning_pct"]) for k, v in prebook_by_type.items()})
nov = [e for e in events if e["startTime"][:7] == SNAPSHOT.strftime("%Y-%m") and e.get("maxAttendees")]
out(f"Kontrol (hele {SNAPSHOT:%Y-%m}, alle med loft inkl. aflyste/fremtidige):", sum(e["booked"] for e in nov), "/", sum(e["maxAttendees"] for e in nov))

# ---------------------------------------------------------------- 7 trænere
out("=" * 70)
out("7. TRÆNERE")
tr_type = collections.defaultdict(collections.Counter)
tr_total = collections.Counter()
for e in events:
    for n in trainer_names(e):
        tr_type[n][TYPE_NAME[MAPPING[e["activityId"]][0]]] += 1
        tr_total[n] += 1
trainers_out = []
for n, c in tr_total.most_common():
    trainers_out.append({"navn": n, "hold": c, "pr_type": dict(tr_type[n])})
    out(f"   {n:30s} {c:3d}  {dict(tr_type[n])}")
out(f"Navngivne trænere: {len(tr_total)}")
noname = collections.Counter()
for e in events:
    t = TYPE_NAME[MAPPING[e["activityId"]][0]]
    noname[(t, bool(trainer_names(e)))] += 1
no_trainer_by_type = {}
for t, _, _ in TYPES:
    tn = TYPE_NAME[t]
    a_, b_ = noname[(tn, True)], noname[(tn, False)]
    if a_ + b_:
        no_trainer_by_type[tn] = {"med_navn": a_, "uden_navn": b_}
out("Hold med/uden navngiven træner pr. type:", no_trainer_by_type)
out("Hold uden navngiven træner i alt:", sum(not trainer_names(e) for e in events), "af", len(events))
out("Fremtidige hold uden navngiven træner:", sum(not trainer_names(e) for e in events if e["_dt"] >= SNAPSHOT),
    "af", sum(e["_dt"] >= SNAPSHOT for e in events))
out("Hold med 2 ansvarlige:", collections.Counter(len(e["responsible"]) for e in events))
out("Aktiviteter efter antal standard-ansvarlige (responsibleUsersIds._count):",
    dict(collections.Counter(a["responsibleUsersIds"]["_count"] for a in acts)))
# 'uden træner'-hold med navngiven ansvarlig
udt = [(e["startTime"][:10], e["name"], trainer_names(e)) for e in events if "uden træner" in e["name"].lower() and trainer_names(e)]
out(f"Hold kaldt 'uden træner' men med navngiven ansvarlig: {len(udt)}")

# ---------------------------------------------------------------- 8 inkonsistenser
out("=" * 70)
out("8. INKONSISTENSER")
issues = []


def issue(kategori, tekst, eksempler):
    issues.append({"kategori": kategori, "tekst": tekst, "eksempler": eksempler})
    out(f"- [{kategori}] {tekst}: {eksempler}")


wod_active = [r for r in inventory if r["type"] == "wod" and r["status"] == "aktiv"]
issue("struktur", f"WOD er delt på {len(wod_active)} aktive aktiviteter (én pr. ugedag/tid)", [r["navn"] for r in wod_active][:5])
for t in ("wod", "hyrox", "rengoering", "wod_uden_traener"):
    rs = [r for r in inventory if r["type"] == t and r["status"] == "aktiv"]
    cols = collections.Counter(c for r in rs for c in r["farver_i_planen"])
    if len(cols) > 1:
        issue("farve", f"{TYPE_NAME[t]}: {len(cols)} forskellige farver blandt aktive søskende", dict(cols))
raw_cols = collections.Counter(e["color"] for e in events)
fmt = [c for c in raw_cols if c.startswith("#") or c != c.lower()]
issue("farve", "Farvekoder i blandet format (med '#', store bogstaver)", {c: raw_cols[c] for c in fmt})
acts_col_fmt = [a["name"] for a in acts if a["color"] != a["color"].lower() or a["color"].startswith("#")]
issue("farve", "Aktiviteter med farve i store bogstaver", acts_col_fmt)
act_vs_ev_col = [(A[aid]["name"], A[aid]["color"], sorted(r)) for aid in by_act if aid in A
                 for r in [{ncolor(e["color"]) for e in by_act[aid]}] if ncolor(A[aid]["color"]) not in r]
issue("farve", "Aktivitetens farve bruges ikke på et eneste af dens hold", act_vs_ev_col)
issue("navn", "Aktivitetsnavn brugt flere gange", {k: v for k, v in name_counts.items() if v > 1})
issue("navn", "Samme type med forskellig stavemåde", [sorted(v) for v in ci.values() if len(v) > 1] + [["Mash", "MASH - lidt mere udfordrende end WOD"], ["Lang WOD", "WOD (Laaang workout)"]])
issue("navn", "Aktivitetens navn ≠ holdenes navn", {f"{k[0]} -> {k[1]}": v for k, v in name_over.items()})
issue("kapacitet", "Hold med anden kapacitet end aktivitetens standard", cap_over)
issue("kapacitet", "Hold med flere tilmeldte end pladser", over)
for k in ("hasWaitingList", "registerAttendance"):
    mixed = [r["navn"] for r in inventory if r["status"] == "aktiv" and len({e[k] for e in by_act[r["activityId"]]}) > 1]
    issue("indstilling", f"Aktive aktiviteter hvor {k} skifter fra hold til hold", f"{len(mixed)} af {len(active_acts)}: {mixed[:4]} ...")
hy = [r for r in inventory if r["type"] == "hyrox"]
issue("indstilling", "HYROX-søskende med forskellige indstillinger",
      [{k: r[k] for k in ("navn", "farve", "tags", "registerAttendance", "pris_klip", "antal_standard_ansvarlige")} for r in hy])
issue("indstilling", "Aktive hold uden tags (alle andre har 'Alle medlemmer')", sorted({e["name"] for e in events if not e["tagsAssigned"] and MAPPING[e["activityId"]][0] not in ("rengoering", "ungeenhed")}))
issue("tags", "Ugedags-tags bruges ikke konsekvent", dict(wd_ok))
_udm_mangler = [m for m in months if m not in [t["name"][12:] for t in tags if t["name"].startswith("Udmeld slut")]]
if _udm_mangler:
    _lang = {"jan": "januar", "feb": "februar", "sep": "september", "okt": "oktober", "nov": "november", "dec": "december"}
    issue("tags", "Månedsrække 'Udmeld slut' mangler " + ", ".join(_lang.get(m, m) for m in _udm_mangler), _udm_mangler)
issue("tags", "Produkter peger på tag der ikke findes i tag-listen", missing_tag_refs)
issue("trænere", "Hold kaldt 'uden træner' har alligevel navngiven ansvarlig", f"{len(udt)} hold, fx {udt[:2]}")
issue("trænere", "Trænernavn ikke synligt på genererede hold (kun aktivitetens standard-ansvarlig, uden navn)",
      f"{sum(not trainer_names(e) for e in events if e['_dt']>=SNAPSHOT)} af {sum(e['_dt']>=SNAPSHOT for e in events)} kommende hold")
dormant = [r["navn"] for r in inventory if r["status"] == "hvilende"]
issue("oprydning", f"{len(dormant)} hvilende aktiviteter uden hold i vinduet", dormant)
issue("oprydning", "Aktivitet med hold, som ikke findes i /api/activity", sorted(set(by_act) - set(A)))
issue("tidsstempler", "createdTs på aktiviteter mangler 'Z' (lokal tid), modifiedTs har 'Z'",
      sum(not a["createdTs"].endswith("Z") for a in acts))
issue("id", "eventId svarer ikke altid til holdets lokale starttid (TONS: +60 min = UTC-tid; flyttet eller oprettet anderledes - uafklaret)", dict(id_kinds))
issue("data", "Holdplanen (anonym) viser activityHasPrice=false/paymentRules=0 på alle hold, detaljekaldet viser klip+no-show",
      dict(detail_diff))

# ---------------------------------------------------------------- 9 skrive-endpoints
out("=" * 70)
out("9. SKRIVE-ENDPOINTS I SWAGGER (kun dokumentation, intet kaldes)")
with open(SWAGGER, encoding="utf-8") as f:
    sw = json.load(f)
EDITS = [
    ("Skift træner på ét hold", "Hold (ActivityEvent)", "responsible[] + update=current", [("PUT", "/api/activity/{activityId}/event/{id}"), ("PUT", "/api/event/v3/{id}")]),
    ("Skift standardtræner for en fast tid (resten af serien)", "Hold-serie (sequence)", "responsible[] + update=allFromCurrent/allFuture", [("PUT", "/api/activity/{activityId}/event/{id}")]),
    ("Aflys ét hold (med besked til tilmeldte)", "Hold", "status=cancelled, cancellationMessage, refund, updateLevel", [("POST", "/api/activity/{activityId}/event/{eventId}/cancelevent")]),
    ("Slet hold / resten af serien", "Hold / serie", "update=current|allFromCurrent|allFuture", [("DELETE", "/api/activity/{activityId}/event/{id}"), ("DELETE", "/api/event/v3/{id}"), ("DELETE", "/api/event/{id}")]),
    ("Ændr kapacitet / venteliste på ét hold eller serien", "Hold / serie", "maxAttendees, hasWaitingList", [("PUT", "/api/activity/{activityId}/event/{id}")]),
    ("Flyt tidspunkt", "Hold / serie", "startTime, endTime, meetTime, signUpDeadline (eventId er tidsbaseret - uafklaret om id ændres)", [("PUT", "/api/activity/{activityId}/event/{id}"), ("PUT", "/api/event/v3/{id}")]),
    ("Ændr navn/beskrivelse/farve på hold", "Hold / serie", "name, description, color", [("PUT", "/api/activity/{activityId}/event/{id}")]),
    ("Ændr hvem der må se/booke (tags)", "Hold / serie", "tagsAssigned, allowedToBook/allowedToSee (v3)", [("PUT", "/api/activity/{activityId}/event/{id}"), ("PUT", "/api/event/v3/{id}")]),
    ("Opret enkelt hold (engangs-event)", "Hold", "EventCreateSingleCommand", [("POST", "/api/event/v3/single"), ("POST", "/api/activity/{activityId}/event")]),
    ("Opret fast ugentligt hold (serie)", "Serie", "EventCreateRecurringCommand.when.schedules[] (weekdays, fromTime, duration, weekInterval, scheduleStart/End)", [("POST", "/api/event/v3/recurring")]),
    ("Forlæng serie med flere datoer", "Serie", "RecurringWhenInfo", [("POST", "/api/event/v3/{eventId}/recurring")]),
    ("Opret/ændr holdtype (aktivitet)", "Aktivitet", "ActivityDto (name, color, maxAttendees, hasWaitingList, tagsAssigned, responsibleUsersIds ...)", [("POST", "/api/activity"), ("PUT", "/api/activity/{id}")]),
    ("Slet/arkivér hvilende aktivitet", "Aktivitet", "-", [("DELETE", "/api/activity/{id}"), ("POST", "/api/activitydata/delete")]),
    ("Ændr pris (klip/udeblivelsesgebyr)", "Pris", "priceType perOnlineSignup / noShow", [("PUT", "/api/activity/{activityId}/event/{eventId}/price"), ("PUT", "/api/price/{id}"), ("PUT", "/api/pricedata/activity/{actType}/{id}")]),
    ("Tilmeld/afmeld medlem (admin)", "Booking", "BookingRequestDto", [("POST", "/api/activity/{activityId}/event/{eventId}/adminbooking"), ("DELETE", "/api/activity/{activityId}/event/{eventId}/bookings/{id}")]),
    ("Registrér fremmøde", "Booking", "-", [("POST", "/api/booking/{id}/attend"), ("POST", "/api/activity/{activityId}/member/{memberId}")]),
    ("Send besked/invitation til holdet", "Hold", "SendInvitationV2Dto", [("POST", "/api/activity/{activityId}/event/{eventId}/v2/sendinvitation")]),
    ("Opret/omdøb tag", "Tag", "TagDto / TagDetailsDto", [("POST", "/api/tag"), ("PUT", "/api/tag")]),
    ("Masse-ændring af aktivitet / klon", "Aktivitet", "uklart (body uden schema) - i DENIED_PATHS som GET", [("PUT", "/api/activitydata/batchupdate/{id}"), ("PUT", "/api/activitydata/clone/{id}")]),
]
write_map = []
for name, ent, felter, eps in EDITS:
    chk = []
    for verb, path in eps:
        op = sw["paths"].get(path, {}).get(verb.lower())
        chk.append({"verb": verb, "path": path, "findes": bool(op), "operationId": op.get("operationId") if op else None,
                    "tag": (op.get("tags") or [None])[0] if op else None})
    write_map.append({"redigering": name, "entitet": ent, "felter": felter, "endpoints": chk})
    out(f"   {name}: " + "; ".join(f"{c['verb']} {c['path']} ({'OK ' + c['operationId'] if c['findes'] else 'FINDES IKKE'})" for c in chk))
upd_enum = sw["definitions"]["ClubPortal.Common.Dtos.ActivityEventCommand"]["properties"]["update"].get("enum")
out("ActivityEventCommand.update enum:", upd_enum)
del_enum = [p.get("enum") for p in sw["paths"]["/api/activity/{activityId}/event/{id}"]["delete"]["parameters"] if p["name"] == "update"]
out("DELETE event ?update enum:", del_enum)
out("Alle endpoints fundet:", all(c["findes"] for w in write_map for c in w["endpoints"]))

# ---------------------------------------------------------------- holdtyper.json
type_rows = []
for t, navn, beskr in TYPES:
    rs = [r for r in inventory if r["type"] == t]
    act_ids = [r["activityId"] for r in rs]
    L = [e for e in events if e["activityId"] in act_ids]
    col = collections.Counter(ncolor(e["color"]) for e in L) or collections.Counter(r["farve"] for r in rs if r["farve"])
    caps = collections.Counter(e.get("maxAttendees") or 0 for e in L) or collections.Counter(r["kapacitet"] for r in rs)
    type_rows.append({
        "id": t, "navn": navn, "beskrivelse": beskr,
        "farve": col.most_common(1)[0][0] if col else None,
        "farver_set": dict(col),
        "standard_kapacitet": caps.most_common(1)[0][0] if caps else None,
        "kapaciteter_set": {str(k): v for k, v in caps.items()},
        "tilmelding": any(e["onlineSignup"] for e in L) if L else None,
        "aktiviteter_i_alt": len(rs),
        "aktive_aktiviteter": sum(r["status"] == "aktiv" for r in rs),
        "hold_i_vinduet": len(L),
        "slots_i_standarduge": [f"{r['ugedag']} {r['start']}" for r in standard_week if r["type"] == t],
        "usikker_mapping": [r["activityId"] for r in rs if r["type_sikkerhed"] == "usikker"],
    })

result = {
    "_meta": {
        "genereret_af": "analyse_holdtyper.py",
        "kilde_snapshot": SNAPSHOT_TXT,
        "snapshot_kilde": SNAPSHOT_KILDE,
        "ukendte_aktiviteter": UNKNOWN,
        "holdplan_vindue": [min(e["startTime"] for e in events), max(e["startTime"] for e in events)],
        "grid_vindue": [GRID_FROM, GRID_TO],
        "belastning_vindue": [LOAD_FROM, SNAPSHOT_TXT],
        "note": "Afledt af læsekald (kun GET). Trænernavne er offentlige. Ingen medlemsdata.",
    },
    "holdtyper": type_rows,
    "mapping": {aid: {"type": MAPPING[aid][0], "sikkerhed": MAPPING[aid][1], "note": MAPPING[aid][2]} for aid in all_aids},
    "standarduge": standard_week,
    "standarduge_matrix": grid_matrix,
    "afvigelser": {"manglende_datoer": holes, "hold_paa_helligdage": holiday_events, "aflyste": cancelled,
                   "hold_uden_for_standard_slots": [{"dato": e["startTime"], "navn": e["name"], "activityId": e["activityId"], "status": e["status"]} for e in oneoffs]},
    "statusser": dict(collections.Counter(e["status"] for e in events)),
    "tags": tag_rows,
    "tag_grupper": dict(grp),
    "traenere": trainers_out,
    "traener_daekning_pr_type": no_trainer_by_type,
    "belastning": {"pr_type": {TYPE_NAME[k]: v for k, v in load_by_type.items()}, "i_alt": load_total,
                   "pr_slot": load_by_slot, "pr_ugedag": load_by_weekday, "pr_tid_paa_dagen": load_by_tod,
                   "fyldning_efter_afstand": lead_stats, "forhaandsbooking_7_dage": prebook_by_type,
                   "udeladt": dict(excl)},
    "datamodel": {"felter_kun_aktivitet": sorted(act_fields - ev_fields), "felter_kun_hold": sorted(ev_fields - act_fields),
                  "felter_der_varierer_pr_hold": dict(var_fields), "felter_der_aldrig_varierer": never_vary,
                  "afvigelse_fra_aktivitet": override_summary, "hold_med_egen_record": len(mat), "hold_genereret": len(virt)},
    "aktiviteter": inventory,
    "inkonsistenser": issues,
    "skrive_endpoints": write_map,
    "produkter": [{"id": p["id"], "navn": p["name"], "maanedspris": p["displayPrice"]} for p in products],
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
out("=" * 70)
out("Skrev", OUT)
for r in type_rows:
    out(f"   {r['id']:16s} {r['navn']:26s} farve={r['farve']} kap={r['standard_kapacitet']} akt={r['aktiviteter_i_alt']}/{r['aktive_aktiviteter']} hold={r['hold_i_vinduet']} slots={r['slots_i_standarduge']}")
