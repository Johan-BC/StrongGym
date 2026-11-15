#!/usr/bin/env python3
"""
Bygger ../../styring-data.json til prototypen styring.html.

Kører helt offline: læser kun de gemte snapshots i data/ (fra kortlaeg.py eller
den lette holdplan.py), adgang.json og holdtyper.json (fra analyse_holdtyper.py).
Laver ingen netværkskald og skriver kun styring-data.json i repo-roden.

    python3 byg_styringsdata.py           # stopper med fejl, hvis der ingen hold er de næste 7 dage
    python3 byg_styringsdata.py --force   # skriv alligevel

Skrive-endpoints i outputtet er inaktive tekststrenge (dokumentation til et
senere, separat sync-lag). Prototypen kalder dem ikke - se CLAUDE.md.
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stier  # noqa: E402

DATA = stier.DATA_DIR
OUT = os.path.join(stier.STYRING_UD, "styring-data.json")
FORCE = "--force" in sys.argv

WD = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
# Typer der ikke er træningshold (ingen træner/tilmelding forventet)
NON_TRAINING = {"rengoering", "ungeenhed"}
# Typer der ikke vises som "rigtige" holdtyper i frontenden
NOT_REAL = {"ukendt_opstart", "test"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


WD_RE = re.compile(r"\s+(Mandag|Tirsdag|Onsdag|Torsdag|Fredag|Lørdag|Søndag)\s+\d{4}$")


def base_name(n):
    """'WOD Mandag 0815' -> 'WOD': ugedag+tid i navnet er ikke en afvigelse."""
    return WD_RE.sub("", n.strip())


def ncolor(c):
    return (c or "").lstrip("#").lower() or None


ht = load(os.path.join(stier.KORTLAEG_DIR, "holdtyper.json"))
acts_raw = {a["entityId"]: a for a in load(os.path.join(DATA, "activity.json"))}
tags_raw = load(os.path.join(DATA, "tag.json"))
products = load(os.path.join(DATA, "product.json"))["products"]
snapshot, snapshot_kilde = stier.snapshot_tid()  # lokal tid (Europe/Copenhagen)
if snapshot != ht["_meta"]["kilde_snapshot"]:
    sys.exit("FEJL: holdtyper.json er bygget af et andet øjebliksbillede - kør analyse_holdtyper.py først.")
mode = "anonym"
if snapshot_kilde == "holdplan_meta.json":
    mode = load(os.path.join(DATA, "holdplan_meta.json")).get("mode", "anonym")

mapping = ht["mapping"]
type_name = {t["id"]: t["navn"] for t in ht["holdtyper"]}
tag_name = {t["entityId"]: t["name"] for t in tags_raw}

# ------------------------------------------------------------------ hold
raw_events = []
for fn in sorted(glob.glob(os.path.join(DATA, "schedule_*.json"))):
    for day in load(fn):
        raw_events.extend(day["slots"])
assert len({e["entityId"] for e in raw_events}) == len(raw_events), "dubletter i holdplan"

events = []
for e in sorted(raw_events, key=lambda e: (e["startTime"], e["name"])):
    names = [r["displayName"] for r in e.get("responsible", []) if r.get("displayName")]
    events.append({
        "id": e["entityId"],
        "activityId": e["activityId"],
        "eventId": e["eventId"],
        "typeId": mapping.get(e["activityId"], {}).get("type", "ukendt"),
        "name": e["name"],
        "start": e["startTime"][:16],
        "end": e["endTime"][:16],
        "status": e["status"],
        "cancellationMessage": (e.get("cancellationMessage") or "").strip() or None,
        "capacity": e.get("maxAttendees") or 0,
        "booked": e.get("booked", 0),
        "waitingList": e.get("waitingList", 0),
        "trainers": names,
        # antal ansvarlige i goMember; navnet er skjult anonymt hvis trainers er tom
        "responsibleCount": len(e.get("responsible", [])),
        "hasWaitingList": bool(e.get("hasWaitingList")),
        "registerAttendance": bool(e.get("registerAttendance")),
        "colour": ncolor(e.get("color")),
        "tags": [tag_name.get(t, t) for t in e.get("tagsAssigned", [])],
        # egen gemt record i goMember (overstyring) - kun de har trænernavn
        "ownRecord": "locationName" in e,
    })

# ------------------------------------------------------------------ aktiviteter
activities = []
for a in ht["aktiviteter"]:
    raw = acts_raw.get(a["activityId"], {})
    activities.append({
        "id": a["activityId"],
        "name": a["navn"],
        "typeId": a["type"],
        "mappingCertainty": a["type_sikkerhed"],
        "mappingNote": a["note"] or None,
        "status": a["status"],
        "inActivityList": a["i_activity_listen"],
        "colour": ncolor(a.get("farve")),
        "capacity": a.get("kapacitet"),
        "hasWaitingList": a.get("venteliste"),
        "registerAttendance": a.get("registerAttendance"),
        "onlineSignup": a.get("onlineSignup"),
        "tags": a.get("tags", []),
        "slots": a.get("ugedag_tid", []),
        "eventNames": a.get("holdnavne_i_planen", {}),
        "eventsInWindow": a.get("antal_hold", 0),
        "defaultResponsibleCount": raw.get("responsibleUsersIds", {}).get("_count"),
    })

# ------------------------------------------------------------------ søskende-afvigelser
# Pr. holdtype: felter der har mere end én værdi blandt kommende hold på de
# aktive aktiviteter. Bruges i "Holdtyper" og "Kræver opmærksomhed".
future = [e for e in events if e["start"] >= snapshot[:16]]
sibling_diffs = {}
for t in ht["holdtyper"]:
    tid = t["id"]
    if tid in NOT_REAL:
        continue
    fe = [e for e in future if e["typeId"] == tid and e["status"] != "cancelled"]
    diffs = []
    for field, label in [("capacity", "Max. pladser"), ("colour", "Farve"),
                         ("name", "Holdnavn (uden ugedag/tid)"), ("hasWaitingList", "Venteliste"),
                         ("registerAttendance", "Fremmøderegistrering")]:
        by_val = collections.defaultdict(lambda: collections.Counter())
        for e in fe:
            v = base_name(e[field]) if field == "name" else e[field]
            by_val[json.dumps(v, ensure_ascii=False)][e["activityId"]] += 1
        if len(by_val) > 1:
            diffs.append({
                "field": field,
                "label": label,
                "values": [{"value": json.loads(v), "events": sum(c.values()),
                            "activities": sorted(c)} for v, c in
                           sorted(by_val.items(), key=lambda kv: -sum(kv[1].values()))],
            })
    # forskellig standardværdi på selve aktiviteterne (aktive)
    act_defaults = {}
    for field in ("capacity", "colour", "hasWaitingList", "registerAttendance"):
        vals = collections.Counter(
            json.dumps(a[field]) for a in activities if a["typeId"] == tid and a["status"] == "aktiv")
        if len(vals) > 1:
            act_defaults[field] = {json.loads(k): n for k, n in vals.items()}
    sibling_diffs[tid] = {"futureEvents": len(fe), "fields": diffs, "activityDefaults": act_defaults}

# ------------------------------------------------------------------ holdtyper
types = []
for t in ht["holdtyper"]:
    types.append({
        "id": t["id"],
        "name": t["navn"],
        "description": t["beskrivelse"],
        "colour": ncolor(t["farve"]),
        "defaultCapacity": t["standard_kapacitet"],
        "signup": t["tilmelding"],
        "training": t["id"] not in NON_TRAINING,
        "real": t["id"] not in NOT_REAL,
        "activitiesTotal": t["aktiviteter_i_alt"],
        "activitiesActive": t["aktive_aktiviteter"],
        "eventsInWindow": t["hold_i_vinduet"],
        "slots": t["slots_i_standarduge"],
        "uncertainMapping": t["usikker_mapping"],
        "siblingDiffs": sibling_diffs.get(t["id"]),
    })

# ------------------------------------------------------------------ standarduge
standard_week = [{
    "weekday": s["ugedag_nr"], "weekdayName": s["ugedag"], "start": s["start"], "end": s["slut"],
    "typeId": s["type"], "activityIds": s["activityIds"], "weeks": s["uger_med_hold"],
    "weeksTotal": s["uger_i_alt"],
} for s in ht["standarduge"]]

# ------------------------------------------------------------------ tags
groups = collections.OrderedDict()
for t in ht["tags"]:
    groups.setdefault(t["gruppe"], []).append(t["navn"])
tag_groups = [{"group": g, "count": len(n), "names": n} for g, n in groups.items()]

# ------------------------------------------------------------------ medlemskaber
memberships = []
for p in sorted(products, key=lambda p: p.get("viewOrder", 0)):
    klip = "klip" in p["name"].lower()
    memberships.append({
        "id": p["id"],
        "name": p["name"],
        "price": p["displayPrice"],
        # displayPrice er månedspris for abonnementer; klippekortet er en engangspris
        "priceUnit": "pr. kort" if klip else "pr. md.",
        "ageFrom": p.get("ageFrom"),
        "ageTo": p.get("ageTo"),
    })

# Medlemskaber uden offentligt produkt i goMember. Priserne er oplyst af klubben
# (Johan) 15. november 2026 og skal rettes her, hvis de ændres.
KENDTE_PRISER = [
    {"id": "Tag2518007440748131293", "name": "12 måneder (årsabonnement)", "price": 5500.0, "priceUnit": "pr. år"},
    {"id": "Tag2518007439372993219", "name": "Fordels medlemskab", "price": 199.0, "priceUnit": "pr. md."},
]
_kendte_id = {m["id"] for m in memberships}
for k in KENDTE_PRISER:
    if k["id"] not in _kendte_id:
        memberships.append(dict(k, ageFrom=None, ageTo=None, kilde="oplyst af klubben 15. nov. 2026"))

# ------------------------------------------------------------------ belastning pr. fast tid
load_slots = [{
    "weekdayName": s["ugedag"], "start": s["start"], "typeName": s["type"],
    "events": s["hold"], "capacity": s["kapacitet"], "booked": s["tilmeldt"],
    "fillPct": s["fyldning_pct"], "full": s["fuldt_booket"],
} for s in ht["belastning"]["pr_slot"]]

# ------------------------------------------------------------------ inkonsistenser
def flat(x):
    if isinstance(x, dict):
        return [f"{k}: {v}" for k, v in x.items()]
    if isinstance(x, list):
        return [", ".join(map(str, i)) if isinstance(i, (list, tuple)) else
                (json.dumps(i, ensure_ascii=False) if isinstance(i, dict) else str(i)) for i in x]
    return [str(x)]


inconsistencies = [{"category": i["kategori"], "text": i["tekst"], "examples": flat(i["eksempler"])[:8]}
                   for i in ht["inkonsistenser"]]

# ------------------------------------------------------------------ rettelsestyper -> goMember-mål
W = {w["redigering"]: w for w in ht["skrive_endpoints"]}


def ep(redigering):
    w = W[redigering]
    return {"redigering": redigering, "entity": w["entitet"], "fields": w["felter"],
            "endpoints": [{"verb": x["verb"], "path": x["path"], "operationId": x["operationId"]}
                          for x in w["endpoints"]]}


# update-parameter pr. omfang (ActivityEventCommand.update i swagger; adfærd ikke afprøvet)
scope_update = {"hold": "current", "fremtidige": "allFromCurrent", "type": "allFromCurrent"}
edit_targets = {
    "traener": {"label": "Skift træner", "field": "responsible",
                "hold": ep("Skift træner på ét hold"),
                "serie": ep("Skift standardtræner for en fast tid (resten af serien)"),
                "note": "Trænere er medlemmer i goMember; fritekst-navnet skal slås op til et medlems-id før afsendelse."},
    "aflys": {"label": "Aflys hold", "field": "status/cancellationMessage",
              "hold": ep("Aflys ét hold (med besked til tilmeldte)"),
              "serie": ep("Aflys ét hold (med besked til tilmeldte)"),
              "note": "cancelevent har feltet updateLevel; om det aflyser resten af serien er ikke afprøvet. Aflys ikke ved at slette."},
    "kapacitet": {"label": "Ændr max. pladser", "field": "maxAttendees",
                  "hold": ep("Ændr kapacitet / venteliste på ét hold eller serien"),
                  "serie": ep("Ændr kapacitet / venteliste på ét hold eller serien"),
                  "aktivitet": ep("Opret/ændr holdtype (aktivitet)")},
    "tid": {"label": "Flyt tidspunkt", "field": "startTime/endTime",
            "hold": ep("Flyt tidspunkt"), "serie": ep("Flyt tidspunkt"),
            "note": "eventId er tidsbaseret; om flytning ændrer eventId er uafklaret."},
    "venteliste": {"label": "Venteliste til/fra", "field": "hasWaitingList",
                   "hold": ep("Ændr kapacitet / venteliste på ét hold eller serien"),
                   "serie": ep("Ændr kapacitet / venteliste på ét hold eller serien"),
                   "aktivitet": ep("Opret/ændr holdtype (aktivitet)")},
    "fremmoede": {"label": "Fremmøderegistrering til/fra", "field": "registerAttendance",
                  "hold": ep("Ændr navn/beskrivelse/farve på hold"),
                  "serie": ep("Ændr navn/beskrivelse/farve på hold"),
                  "aktivitet": ep("Opret/ændr holdtype (aktivitet)"),
                  "note": "registerAttendance er et felt på holdet (EventApi_Put); ikke listet særskilt i kortlægningen."},
    "navn": {"label": "Omdøb hold", "field": "name",
             "hold": ep("Ændr navn/beskrivelse/farve på hold"),
             "serie": ep("Ændr navn/beskrivelse/farve på hold")},
    "farve": {"label": "Ensret farve", "field": "color",
              "hold": ep("Ændr navn/beskrivelse/farve på hold"),
              "serie": ep("Ændr navn/beskrivelse/farve på hold"),
              "aktivitet": ep("Opret/ændr holdtype (aktivitet)")},
}

# ------------------------------------------------------------------ helligdage i vinduet
years = sorted({e["start"][:4] for e in events})
holidays = []
for y in years:
    for md, name in [("12-24", "Juleaften"), ("12-25", "1. juledag"), ("12-26", "2. juledag"),
                     ("12-31", "Nytårsaften"), ("01-01", "Nytårsdag")]:
        holidays.append({"date": f"{y}-{md}", "name": name})

# ------------------------------------------------------------------ fornuftskontrol
snap_dt = dt.datetime.fromisoformat(snapshot)
uge_frem = [e for e in events if snapshot[:16] <= e["start"] < (snap_dt + dt.timedelta(days=7)).isoformat()[:16]
            and e["status"] != "cancelled"]
if not uge_frem and not FORCE:
    sys.exit("FEJL: holdplanen har 0 hold de næste 7 dage - det ligner en fejl hos goMember eller i "
             "hentningen. Ingen fil skrevet (brug --force for at skrive alligevel).")

out = {
    "_om": ("Afledt af læsekald mod goMember (kun GET, " + ("med det skrivebeskyttede login" if mode == "login" else "uden login")
            + "). Trænernavne er offentlige; medlemsnumre/-id'er er fjernet. "
            "Ingen medlemsdata. Skrive-endpoints herunder er inaktiv dokumentation til et senere, "
            "separat sync-lag og kaldes ikke af styring.html."),
    "snapshot": snapshot,
    "timezone": "Europe/Copenhagen",
    "window": {"from": events[0]["start"][:10], "to": events[-1]["start"][:10]},
    "nonTrainingTypes": sorted(NON_TRAINING),
    "types": types,
    "activities": activities,
    "events": events,
    "standardWeek": standard_week,
    "loadPerSlot": load_slots,
    "loadWindow": ht["_meta"]["belastning_vindue"],
    "tagGroups": tag_groups,
    "memberships": memberships,
    "inconsistencies": inconsistencies,
    "holidays": holidays,
    "scopeUpdate": scope_update,
    "editTargets": edit_targets,
}

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

print(f"Skrev {OUT}: {os.path.getsize(OUT)} bytes, {len(events)} hold, "
      f"{len(activities)} aktiviteter, {sum(t['real'] for t in types)} holdtyper, snapshot {snapshot}, "
      f"{len(uge_frem)} hold de næste 7 dage")
