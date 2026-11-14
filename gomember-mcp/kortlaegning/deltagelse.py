#!/usr/bin/env python3
"""
Deltagelse pr. hold over de seneste 6 måneder (14/5 - 14/11 2026).

Bruger KUN GoMemberClient.get() (se ../CLAUDE.md) og kun disse GET-stier:
  /api/activity
  /api/activity/event/days
  /api/activity/{activityId}/event/{eventId}
  /api/activity/{activityId}/event/{eventId}/bookings

    python3 deltagelse.py            # henter det der mangler (cache) + skriver deltagelse.json
    python3 deltagelse.py --offline  # ingen netkald, kun cache -> deltagelse.json

Persondata: booking-listerne indeholder navne/medlems-id'er. De reduceres til
antal i hukommelsen med det samme (`_count_bookings`), og kun antallene gemmes
i cachen. Rå svar gemmes aldrig.

Cache: deltagelse_cache.json (kun afledte, ikke-personlige felter). Et hold der
gav 404 ("Event not found") gemmes som {"nf": 1}, så det ikke spørges igen.
"""
import collections
import datetime as dt
import json
import os
import sys
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

CACHE = os.path.join(HERE, "deltagelse_cache.json")
OUT = os.path.join(HERE, "deltagelse.json")
HOLDTYPER = os.path.join(HERE, "holdtyper.json")

TZ = ZoneInfo("Europe/Copenhagen")
WIN_FROM = dt.date(2026, 5, 14)
WIN_TO = dt.date(2026, 11, 14)          # inklusiv
NOW = dt.datetime(2026, 11, 14, 22, 0)  # lokal; alle hold 14/11 er afholdt

MIN_INTERVAL = 0.5    # maks 2 kald pr. sekund
HARD_CAP = 2500       # loft pr. kørsel
GAP_BUDGET = 500      # maks kald til at lede efter ukendte tidspunkter

OFFLINE = "--offline" in sys.argv
WD = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
WD_TAG = {"mandag": 0, "tirsdag": 1, "onsdag": 2, "torsdag": 3, "fredag": 4, "lørdag": 5, "søndag": 6}

# Aktiviteter der ikke findes i /api/activity, men har hold i holdplanen.
EXTRA_TYPES = {
    "Activity2516286959559794057": "ungeenhed",   # ældre "Ungeenheden Helsingør Kommune"
}
# Den ukendte aktivitet …140362 bruges til engangshold med forskellige navne.
UNKNOWN_ACT = "Activity2516351285377140362"


def name_to_type(name):
    n = (name or "").lower()
    if "fodbold" in n:
        return "andet"
    if "hyrox" in n:
        return "hyrox"
    if "mash" in n:
        return "mash"
    if "tons" in n:
        return "tons"
    if "lang" in n or "laaang" in n:
        return "lang_wod"
    if "uden træner" in n:
        return "wod_uden_traener"
    return "wod"


# ---------------------------------------------------------------- cache
def load_cache():
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    return {"activities": {}, "days": {}, "events": {}, "bookings": {}, "requests": []}


cache = load_cache()


def save_cache():
    tmp = CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, CACHE)


# ---------------------------------------------------------------- netværk
_client = None
_last = 0.0
n_requests = 0
status_count = collections.Counter()


class CapReached(RuntimeError):
    pass


def get(path, query=None):
    """Ét GET-kald via GoMemberClient med rate limit og loft. Returnerer (status, data)."""
    global _client, _last, n_requests
    if OFFLINE:
        raise CapReached("offline")
    if n_requests >= HARD_CAP:
        raise CapReached("loft nået")
    if _client is None:
        from gomember_client import GoMemberClient
        _client = GoMemberClient()
    wait = MIN_INTERVAL - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)
    _last = time.time()
    n_requests += 1
    try:
        data = _client.get(path, query_params=query)
        status = 200
    except Exception:
        r = _client.last_response
        status = getattr(r, "status_code", None) or -1
        data = None
    status_count[status] += 1
    return status, data


EVENT_FIELDS = ["status", "booked", "maxAttendees", "waitingList", "reservations", "startTime",
                "endTime", "name", "registerAttendance", "hasWaitingList", "cancellationMessage",
                "createdTs", "modifiedTs", "sequence"]


def cancel_reason(msg):
    """Aflysningstekst -> kategori. Fritekst gemmes ikke (kan nævne trænere og hvor de er)."""
    m = (msg or "").lower()
    if not m.strip():
        return None
    if any(w in m for w in ("flyt", "ny sg", "nyt sg", "sg ikke", "gymmet", "på plads")):
        return "flytning/nyt gym ikke klar"
    if any(w in m for w in ("tilmeld", "deltager")):
        return "for få tilmeldte"
    if any(w in m for w in ("træner", "ferie", "konkurrence", "throwdown", "tyskland", "aflyse dette hold")):
        return "træner forhindret"
    return "andet/ukendt"


def _slim(d):
    rec = {k: d.get(k) for k in EVENT_FIELDS if k != "cancellationMessage"}
    rec["cancelReason"] = cancel_reason(d.get("cancellationMessage"))
    return rec


def event_detail(aid, eid):
    key = f"{aid}|{eid}"
    if key in cache["events"]:
        return cache["events"][key]
    status, d = get(f"/api/activity/{aid}/event/{eid}")
    if status == 200 and isinstance(d, dict):
        rec = _slim(d)
    elif status == 404:
        rec = {"nf": 1}
    else:
        rec = {"err": status}
    cache["events"][key] = rec
    return rec


def _count_bookings(rows):
    """Reducér booking-rækker til antal. Ingen personværdier forlader funktionen."""
    c = {"rows": 0, "waiting": 0, "confirmed": 0, "attended": 0, "participants": 0, "attended_participants": 0}
    for r in rows:
        c["rows"] += 1
        p = r.get("participantsCount") or 1
        if r.get("isOnWaitingList"):
            c["waiting"] += 1
            continue
        c["confirmed"] += 1
        c["participants"] += p
        if r.get("attendedTs"):
            c["attended"] += 1
            c["attended_participants"] += p
    return c


def bookings(aid, eid):
    key = f"{aid}|{eid}"
    if key in cache["bookings"]:
        return cache["bookings"][key]
    status, d = get(f"/api/activity/{aid}/event/{eid}/bookings", {"filter.pageSize": 200})
    if status == 200:
        rows = d if isinstance(d, list) else (d or {}).get("items", []) if isinstance(d, dict) else []
        rec = _count_bookings(rows)
        rec["truncated"] = len(rows) >= 200
        del rows
    else:
        rec = {"err": status}
    del d
    cache["bookings"][key] = rec
    return rec


# ---------------------------------------------------------------- hjælpere
def parse_local(s):
    return dt.datetime.fromisoformat(s[:19]) if s else None


def weeks(weekday, start, end):
    d = start + dt.timedelta(days=(weekday - start.weekday()) % 7)
    while d <= end:
        yield d
        d += dt.timedelta(days=7)


def hhmm_shift(hhmm, minutes):
    t = dt.datetime(2000, 1, 1, int(hhmm[:2]), int(hhmm[2:])) + dt.timedelta(minutes=minutes)
    return t.strftime("%H%M")


# ---------------------------------------------------------------- indsamling
def collect():
    ht = json.load(open(HOLDTYPER, encoding="utf-8"))
    mapping = {k: v["type"] for k, v in ht["mapping"].items()}

    # 1. aktivitetsliste
    if not cache["activities"]:
        st, acts = get("/api/activity")
        for a in acts or []:
            wd_tags = sorted({WD_TAG[t["name"].lower()] for t in a.get("assignedTags", []) or []
                              if (t.get("name") or "").lower() in WD_TAG})
            cache["activities"][a["entityId"]] = {
                "name": a.get("name"), "createdTs": a.get("createdTs"), "modifiedTs": a.get("modifiedTs"),
                "registerAttendance": a.get("registerAttendance"), "maxAttendees": a.get("maxAttendees"),
                "activityMode": a.get("activityMode"), "weekdayTags": wd_tags,
            }
        save_cache()

    # 2. holdplan for vinduet (månedsbidder)
    months = [WIN_FROM, dt.date(2026, 6, 1), dt.date(2026, 7, 1), dt.date(2026, 8, 1), dt.date(2026, 9, 1),
              dt.date(2026, 10, 1), dt.date(2026, 11, 1), WIN_TO + dt.timedelta(days=1)]
    for a, b in zip(months, months[1:]):
        k = f"{a}_{b}"
        if k in cache["days"]:
            continue
        st, d = get("/api/activity/event/days", {"eventsToShow": 300, "fromOffset": f"{a}T00:00:00",
                                                 "toTime": f"{b}T00:00:00"})
        evs = []
        for day in d or []:
            for s in day.get("slots", []) or []:
                evs.append(dict(_slim(s), activityId=s.get("activityId"), eventId=s.get("eventId")))
        cache["days"][k] = evs
        save_cache()
    days_events = {}
    for evs in cache["days"].values():
        for e in evs:
            st = parse_local(e["startTime"])
            if st and WIN_FROM <= st.date() <= WIN_TO:
                days_events[f"{e['activityId']}|{e['eventId']}"] = e

    # 3. faste tider pr. aktivitet: fra holdtyper.json (nuværende plan) + holdplanen i vinduet
    slots = collections.defaultdict(set)   # aid -> {(weekday, "HHMM" lokal)}
    offsets = collections.defaultdict(set)  # aid -> {minutter eventId afviger fra lokal tid}
    for a in ht["aktiviteter"]:
        for s in a.get("ugedag_tid") or []:
            wd = WD.index(s.split()[0])
            hhmm = s.split()[1][:5].replace(":", "")
            slots[a["activityId"]].add((wd, hhmm))
    for key, e in days_events.items():
        aid, eid = key.split("|")
        st = parse_local(e["startTime"])
        if eid[8:].isdigit() and len(eid) == 12:      # rene serie-id'er (ikke …XR-suffiks)
            slots[aid].add((st.weekday(), st.strftime("%H%M")))
            diff = (dt.datetime.strptime(eid, "%Y%m%d%H%M") - st).total_seconds() / 60
            if diff:
                offsets[aid].add(int(diff))
    # TONS (…680950): eventId 60 min før lokal tid i nov. (UTC-tid). Om sommeren (UTC+2) kan det være 120.
    offsets["Activity2516233711301680950"].update({-60, -120})

    # 4. ugentlige kandidater pr. fast tid
    acts = cache["activities"]
    probe_log = cache.setdefault("probe_log", {})

    def probe(aid, d, hhmm):
        """Prøv eventId = dato+lokal tid, derefter kendte forskydninger. Returnér eid ved fund."""
        variants = [hhmm] + [hhmm_shift(hhmm, o) for o in sorted(offsets.get(aid, ()), key=abs)]
        for v in variants:
            eid = d.strftime("%Y%m%d") + v
            rec = event_detail(aid, eid)
            if "nf" not in rec and "err" not in rec:
                return eid
        return None

    all_aids = set(acts) | set(slots)
    for aid in sorted(all_aids):
        a = acts.get(aid, {})
        if a.get("activityMode") == "resource":
            continue
        created = parse_local(a.get("createdTs")).date() if a.get("createdTs") else WIN_FROM
        start = max(WIN_FROM, created)
        for (wd, hhmm) in sorted(slots.get(aid, ())):
            for d in weeks(wd, start, WIN_TO):
                if dt.datetime.combine(d, dt.time(int(hhmm[:2]), int(hhmm[2:]))) > NOW:
                    continue
                probe(aid, d, hhmm)
            save_cache()

    # 5. huller: måneder hvor en aktivitet fandtes, men ingen hold blev fundet på kendte tider.
    #    Prøv én dato pr. måned med de tider holdet har haft samme ugedag i hele huset.
    found_months = collections.defaultdict(set)
    for key, rec in cache["events"].items():
        if "nf" in rec or "err" in rec:
            continue
        aid = key.split("|")[0]
        st = parse_local(rec["startTime"])
        found_months[aid].add((st.year, st.month))
    for key, e in days_events.items():
        st = parse_local(e["startTime"])
        found_months[key.split("|")[0]].add((st.year, st.month))
    day_times = collections.defaultdict(set)   # weekday -> lokale tider brugt i huset
    for aid, ss in slots.items():
        for wd, hhmm in ss:
            day_times[wd].add(hhmm)
    gap_used = 0
    gap_found = cache.setdefault("gap_found", {})
    for aid in sorted(all_aids):
        a = acts.get(aid, {})
        if a.get("activityMode") == "resource" or aid in (UNKNOWN_ACT,):
            continue
        typ = mapping.get(aid) or EXTRA_TYPES.get(aid)
        if typ in ("rengoering", "ungeenhed", "test"):
            continue
        wds = {wd for wd, _ in slots.get(aid, ())} or set(a.get("weekdayTags") or [])
        if not wds:
            continue
        created = parse_local(a.get("createdTs")).date() if a.get("createdTs") else WIN_FROM
        m = dt.date(WIN_FROM.year, WIN_FROM.month, 1)
        while m <= WIN_TO:
            ym = (m.year, m.month)
            nxt = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
            # Kun huller FØR sidste fund (en serie der er stoppet og afløst skal ikke afsøges),
            # medmindre aktiviteten slet ingen hold har (hvilende).
            last = max(found_months[aid]) if found_months[aid] else (9999, 12)
            if ym not in found_months[aid] and nxt > created and ym < last:
                for wd in sorted(wds):
                    cands = [d for d in weeks(wd, max(m, WIN_FROM, created), min(nxt - dt.timedelta(days=1), WIN_TO))]
                    if not cands:
                        continue
                    d = cands[len(cands) // 2]
                    for hhmm in sorted(day_times[wd]):
                        if gap_used >= GAP_BUDGET:
                            break
                        for off in (0, -60, -120):
                            eid = d.strftime("%Y%m%d") + hhmm_shift(hhmm, off)
                            fresh = f"{aid}|{eid}" not in cache["events"]
                            rec = event_detail(aid, eid)
                            gap_used += fresh
                            if "nf" not in rec and "err" not in rec:
                                st = parse_local(rec["startTime"])
                                gap_found[f"{aid}|{eid}"] = [st.weekday(), st.strftime("%H%M"), off]
                                break
            m = nxt
        save_cache()
    # nye tider fundet i hullerne -> kør ugentlig afsøgning for dem også
    for key, (wd, hhmm, off) in gap_found.items():
        aid = key.split("|")[0]
        if off:
            offsets[aid].add(off)
        if (wd, hhmm) not in slots[aid]:
            slots[aid].add((wd, hhmm))
            created = parse_local(acts[aid]["createdTs"]).date() if acts.get(aid, {}).get("createdTs") else WIN_FROM
            for d in weeks(wd, max(WIN_FROM, created), WIN_TO):
                probe(aid, d, hhmm)
            save_cache()

    # 6. bookinger for alle afholdte hold med tilmeldte
    for key, rec in list(cache["events"].items()) + [(k, v) for k, v in days_events.items()]:
        if "nf" in rec or "err" in rec:
            continue
        st = parse_local(rec["startTime"])
        if not (WIN_FROM <= st.date() <= WIN_TO) or st > NOW:
            continue
        if (rec.get("booked") or 0) > 0 or (rec.get("waitingList") or 0) > 0:
            aid, eid = key.split("|")
            bookings(aid, eid)
    save_cache()
    return ht, mapping, days_events, slots


# ---------------------------------------------------------------- analyse
def classify(rec, bk, act_created, typ):
    """Returnér (klasse, begrundelse). Se DELTAGELSE.md afsnit 'Fantom-regel'."""
    st = parse_local(rec["startTime"])
    if typ in ("rengoering", "ungeenhed", "andet", "test"):
        return "ikke_traening", "ingen tilmelding / ikke træningshold"
    if rec.get("status") == "cancelled":
        return "aflyst", "status cancelled"
    if rec.get("status") == "excluded":
        # Datoen er taget ud af serien i goMember (fx pinse, sommerpause, opstartsweekend).
        return "udeladt", "status excluded (dato taget ud af serien)"
    booked = rec.get("booked") or 0
    if booked > 0 or (bk and bk.get("confirmed", 0) > 0):
        return "afholdt", "tilmeldte > 0"
    created = parse_local(rec.get("createdTs"))
    if created and created > st:
        return "fantom", "serien oprettet efter holdets dato"
    if act_created and act_created > st:
        return "fantom", "aktiviteten oprettet efter holdets dato"
    return "nul", "0 tilmeldte"


def analyse(ht, mapping, days_events, slots):
    acts = cache["activities"]
    typ_name = {h["id"]: h["navn"] for h in ht["holdtyper"]}
    typ_name.update({"andet": "Andet (fx fodbold)"})
    occ = {}
    for key, rec in cache["events"].items():
        if "nf" in rec or "err" in rec:
            continue
        occ[key] = rec
    for key, e in days_events.items():
        occ.setdefault(key, e)
    rows = []
    for key, rec in occ.items():
        aid, eid = key.split("|")
        st = parse_local(rec["startTime"])
        if not (WIN_FROM <= st.date() <= WIN_TO) or st > NOW:
            continue
        typ = mapping.get(aid) or EXTRA_TYPES.get(aid)
        if aid == UNKNOWN_ACT or typ in (None, "ukendt_opstart"):
            typ = name_to_type(rec.get("name"))
        a = acts.get(aid, {})
        act_created = parse_local(a.get("createdTs"))
        bk = cache["bookings"].get(key)
        cls, why = classify(rec, bk, act_created, typ)
        cap = rec.get("maxAttendees") or 0
        rows.append({
            "dato": st.date().isoformat(), "start": st.strftime("%H:%M"), "ugedag": WD[st.weekday()],
            "activityId": aid, "eventId": eid, "aktivitet": a.get("name") or "(ikke i aktivitetslisten)",
            "holdnavn": rec.get("name"), "typeId": typ, "status": rec.get("status"),
            "booked": rec.get("booked") or 0, "capacity": cap, "waitingList": rec.get("waitingList") or 0,
            "registerAttendance": rec.get("registerAttendance"),
            "attended": (bk or {}).get("attended") if bk and "err" not in bk else None,
            "bookingRows": (bk or {}).get("confirmed") if bk and "err" not in bk else None,
            "waitingRows": (bk or {}).get("waiting") if bk and "err" not in bk else None,
            "aflysningsaarsag": rec.get("cancelReason"),
            "seriesCreated": (rec.get("createdTs") or "")[:10],
            "kilde": "holdplan" if key in days_events else "detaljekald",
            "klassifikation": cls, "begrundelse": why,
        })
    rows.sort(key=lambda r: (r["dato"], r["start"], r["activityId"]))

    def agg(rs):
        held = [r for r in rs if r["klassifikation"] == "afholdt"]
        nul = [r for r in rs if r["klassifikation"] == "nul"]
        reg = [r for r in held if r["registerAttendance"] and r["attended"] is not None]
        cap = sum(r["capacity"] for r in held if r["capacity"])
        bk_cap = sum(r["booked"] for r in held if r["capacity"])
        return {
            "afholdt": len(held),
            "tilmeldte": sum(r["booked"] for r in held),
            "snit_pr_hold": round(sum(r["booked"] for r in held) / len(held), 2) if held else None,
            "pladser": cap,
            "fyldning_pct": round(100 * bk_cap / cap, 1) if cap else None,
            "fuldt_booket": sum(1 for r in held if r["capacity"] and r["booked"] >= r["capacity"]),
            "venteliste_i_alt": sum(r["waitingList"] for r in held),
            "hold_med_venteliste": sum(1 for r in held if r["waitingList"] > 0),
            "nul_tilmeldte": len(nul),
            "aflyst": sum(1 for r in rs if r["klassifikation"] == "aflyst"),
            "udeladt_af_serien": sum(1 for r in rs if r["klassifikation"] == "udeladt"),
            "fantom": sum(1 for r in rs if r["klassifikation"] == "fantom"),
            "hold_med_fremmoede_registrering": len(reg),
            "fremmoede_registreret": sum(r["attended"] for r in reg),
            "fremmoede_pct_af_tilmeldte": (round(100 * sum(r["attended"] for r in reg) /
                                                 sum(r["booked"] for r in reg), 1)
                                           if reg and sum(r["booked"] for r in reg) else None),
            "hold_med_mindst_et_fremmoede": sum(1 for r in held if (r["attended"] or 0) > 0),
        }

    def group(keyf):
        g = collections.defaultdict(list)
        for r in rows:
            if r["klassifikation"] == "ikke_traening":
                continue
            g[keyf(r)].append(r)
        return g

    per_type = {k: dict(navn=typ_name.get(k, k), **agg(v)) for k, v in group(lambda r: r["typeId"]).items()}
    per_act = {}
    for k, v in group(lambda r: r["activityId"]).items():
        per_act[k] = dict(navn=acts.get(k, {}).get("name") or "(ikke i aktivitetslisten)",
                          typeId=v[0]["typeId"], aktivitet_registerAttendance=acts.get(k, {}).get("registerAttendance"),
                          aktivitet_oprettet=(acts.get(k, {}).get("createdTs") or "")[:10],
                          foerste=min(r["dato"] for r in v), sidste=max(r["dato"] for r in v), **agg(v))
    per_slot = {}
    for k, v in group(lambda r: f"{r['ugedag']} {r['start']} {typ_name.get(r['typeId'], r['typeId'])}").items():
        per_slot[k] = dict(foerste=min(r["dato"] for r in v), sidste=max(r["dato"] for r in v), **agg(v))
    per_month = {k: agg(v) for k, v in sorted(group(lambda r: r["dato"][:7]).items())}
    per_week = {k: agg(v) for k, v in sorted(group(
        lambda r: dt.date.fromisoformat(r["dato"]).strftime("%G-U%V")).items())}
    nov = [r for r in rows if "2026-11-01" <= r["dato"] <= "2026-11-14" and r["capacity"]
           and r["klassifikation"] != "ikke_traening"]
    nov_check = agg(nov)
    total = agg([r for r in rows if r["klassifikation"] != "ikke_traening"])
    cls_count = collections.Counter((r["klassifikation"], r["begrundelse"]) for r in rows)
    return rows, dict(per_type=per_type, per_act=per_act, per_slot=per_slot, per_month=per_month,
                      per_week=per_week, nov_check=nov_check, total=total,
                      klassifikation=[{"klasse": k[0], "begrundelse": k[1], "antal": n}
                                      for k, n in sorted(cls_count.items())])


def main():
    # Ældre cache-versioner gemte aflysningsteksten - erstat med kategori.
    for rec in list(cache["events"].values()) + [e for evs in cache["days"].values() for e in evs]:
        if "cancellationMessage" in rec:
            rec["cancelReason"] = cancel_reason(rec.pop("cancellationMessage"))
    try:
        ht, mapping, days_events, slots = collect()
    except CapReached as e:
        print("Stoppet:", e)
        save_cache()
        if not OFFLINE:
            raise
        ht = json.load(open(HOLDTYPER, encoding="utf-8"))
        mapping = {k: v["type"] for k, v in ht["mapping"].items()}
        days_events = {}
        for evs in cache["days"].values():
            for e in evs:
                days_events[f"{e['activityId']}|{e['eventId']}"] = e
        slots = {}
    if n_requests:
        cache["requests"].append({"run": dt.datetime.now().isoformat(timespec="seconds"),
                                  "kald": n_requests, "status": dict(status_count)})
        save_cache()
    rows, ag = analyse(ht, mapping, days_events, slots)
    # Faste tider = mindst 8 afholdte hold i vinduet (engangshold/flyttede hold tæller ikke som fast tid)
    fixed = [dict(tid=k, **v) for k, v in ag["per_slot"].items() if v["afholdt"] >= 8]
    fixed.sort(key=lambda v: (-v["snit_pr_hold"], -v["afholdt"]))
    top10 = [{k: v[k] for k in ("tid", "afholdt", "tilmeldte", "snit_pr_hold", "fyldning_pct", "fuldt_booket")} for v in fixed[:10]]
    bund10 = [{k: v[k] for k in ("tid", "afholdt", "tilmeldte", "snit_pr_hold", "fyldning_pct", "fuldt_booket")} for v in fixed[::-1][:10]]
    probes = [k for k in cache["events"]]
    nf = sum(1 for v in cache["events"].values() if "nf" in v)
    out = {
        "_meta": {
            "vindue": [WIN_FROM.isoformat(), WIN_TO.isoformat()],
            "genereret_af": "deltagelse.py",
            "kald_i_alt_alle_koersler": sum(r["kald"] for r in cache["requests"]),
            "koersler": cache["requests"],
            "detaljekald_i_cache": len(probes), "heraf_404": nf,
            "note": "Kun antal - ingen navne, medlems-id'er eller andre personværdier.",
        },
        "klassifikation": ag["klassifikation"],
        "i_alt": ag["total"],
        "pr_type": ag["per_type"],
        "pr_aktivitet": ag["per_act"],
        "pr_fast_tid": ag["per_slot"],
        "pr_maaned": ag["per_month"],
        "pr_uge": ag["per_week"],
        "kontrol_nov_1_14": ag["nov_check"],
        "top_10_faste_tider": top10,
        "bund_10_faste_tider": bund10,
        "hold": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"kald denne kørsel: {n_requests} {dict(status_count)}; hold i vinduet: {len(rows)}")
    print("klassifikation:", ag["klassifikation"])


if __name__ == "__main__":
    main()
