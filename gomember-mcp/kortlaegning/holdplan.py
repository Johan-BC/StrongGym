#!/usr/bin/env python3
"""
Let opdatering af holdplanen til styring-data.json (bruges hver nat af opdater.py).

Henter KUN det, byg_styringsdata.py/analyse_holdtyper.py skal bruge:
  /api/activity/event/days   holdplanen 8 uger tilbage -> 8 uger frem (i månedsbidder)
  /api/activity              aktivitetslisten
  /api/tag                   etiketter
  /api/product               medlemskaber/priser
i alt ca. 8 GET-kald. Ingen medlems-kald, ingen booking-kald. Den fulde
kortlægning (kortlaeg.py, ca. 100 endpoints) er uændret og køres kun manuelt.

Bruger login, hvis GOMEMBER_USERNAME/GOMEMBER_PASSWORD er sat, ellers anonymt.
Alt gemmes gennem kortlaeg.sanitize(): trænere (responsible) reduceres til
navnet; medlemsnumre og -id'er fjernes.

Skriver i data/: schedule_<fra>_<til>.json (gamle schedule-filer fjernes),
activity.json, tag.json, product.json og holdplan_meta.json (tidspunkt for
øjebliksbilledet, som analyse_holdtyper.py og byg_styringsdata.py bruger).

    python3 holdplan.py                    # i dag (Europe/Copenhagen)
    python3 holdplan.py --dato 2026-11-14  # vindue omkring en anden dato
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kortlaeg import sanitize  # noqa: E402  (samme persondatafilter som den fulde kortlægning)
from netlag import Hentning, NetFejl  # noqa: E402

TZ = ZoneInfo("Europe/Copenhagen")
EVENTS_CAP = 300
UGER = 8


def iso(d):
    return dt.datetime.combine(d, dt.time()).isoformat()


def _gem(mappe, navn, body):
    with open(os.path.join(mappe, navn), "w", encoding="utf-8") as f:
        json.dump(sanitize(body), f, ensure_ascii=False, indent=1)


def hent_holdplan(hent, data_dir, idag, nu):
    """Henter holdplan + lister til data_dir. Returnerer metadata. Rejser NetFejl ved fejl."""
    os.makedirs(data_dir, exist_ok=True)
    win_from, win_to = idag - dt.timedelta(weeks=UGER), idag + dt.timedelta(weeks=UGER)
    chunks, d = [], win_from
    while d < win_to:
        e = min(dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1), win_to)
        chunks.append((d, e))
        d = e
    n0 = hent.n
    hentet = []          # (navn, body)
    meta_chunks = []
    slots = []
    while chunks:
        a, b = chunks.pop(0)
        st, body = hent.get("/api/activity/event/days",
                            {"eventsToShow": EVENTS_CAP, "fromOffset": iso(a), "toTime": iso(b)}, tilladt=())
        if not isinstance(body, list):
            raise NetFejl("Holdplanen fra goMember havde et uventet format.")
        n = sum(len(x.get("slots", []) or []) for x in body)
        if n >= EVENTS_CAP:
            if (b - a).days <= 1:
                raise NetFejl(f"Holdplanen har {n} hold på én dag ({a}) - mere end loftet; stopper.")
            mid = a + (b - a) / 2
            chunks[:0] = [(a, mid), (mid, b)]
            continue
        meta_chunks.append({"from": iso(a), "to": iso(b), "days": len(body), "events": n})
        hentet.append((f"schedule_{a}_{b}.json", body))
        for day in body:
            slots.extend(day.get("slots", []) or [])

    _, acts = hent.get("/api/activity", {"filter.pageSize": 200, "filter.currentPage": 1}, tilladt=())
    _, tags = hent.get("/api/tag", {"filter.pageSize": 500, "filter.currentPage": 1}, tilladt=())
    _, prod = hent.get("/api/product", {}, tilladt=())
    if not isinstance(acts, list) or not acts:
        raise NetFejl("Aktivitetslisten fra goMember var tom eller havde et uventet format.")
    if len(acts) >= 200:
        raise NetFejl("Aktivitetslisten ramte sidestørrelsen (200) - ville blive afskåret; stopper.")
    if not isinstance(tags, list) or not tags:
        raise NetFejl("Etiketlisten fra goMember var tom eller havde et uventet format.")
    if not isinstance(prod, dict) or not isinstance(prod.get("products"), list):
        raise NetFejl("Produktlisten fra goMember havde et uventet format.")
    ids = [s.get("entityId") for s in slots]
    if len(set(ids)) != len(ids):
        raise NetFejl("Holdplanen indeholdt dubletter (samme hold to gange).")
    if not slots:
        raise NetFejl("Holdplanen fra goMember var tom for hele vinduet.")

    # Først nu, hvor alt er hentet og kontrolleret, skrives filerne (i arbejdsmappen).
    for old in glob.glob(os.path.join(data_dir, "schedule_*.json")):
        os.remove(old)
    for navn, body in hentet:
        _gem(data_dir, navn, body)
    _gem(data_dir, "activity.json", acts)
    _gem(data_dir, "tag.json", tags)
    _gem(data_dir, "product.json", prod)
    named = sum(1 for s in slots if any((r or {}).get("displayName") for r in (s.get("responsible") or [])))
    meta = {
        "generated": nu.strftime("%Y-%m-%dT%H:%M:%S"),  # lokal tid (Europe/Copenhagen)
        "genereret_af": "holdplan.py",
        "mode": hent.tilstand,
        "requests_made": hent.n - n0,
        "schedule_window": {"from": iso(win_from), "to": iso(win_to), "chunks": meta_chunks,
                            "events_total": len(slots)},
        "events_with_named_trainer": named,
        "activities": len(acts), "tags": len(tags), "products": len(prod["products"]),
    }
    with open(os.path.join(data_dir, "holdplan_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    return meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dato", help="beregn vinduet ud fra denne dato (YYYY-MM-DD) i stedet for i dag")
    ap.add_argument("--anonym", action="store_true", help="hent uden login")
    a = ap.parse_args()
    nu = dt.datetime.now(TZ).replace(tzinfo=None)
    idag = dt.date.fromisoformat(a.dato) if a.dato else nu.date()
    nu = dt.datetime.combine(idag, nu.time()).replace(microsecond=0)
    hent = Hentning(loft=50, anonym=True if a.anonym else None)
    try:
        meta = hent_holdplan(hent, os.path.join(HERE, "data"), idag, nu)
    except NetFejl as e:
        print("FEJL:", e, file=sys.stderr)
        sys.exit(1)
    print(f"Holdplan hentet ({meta['mode']}): {meta['schedule_window']['events_total']} hold, "
          f"{meta['activities']} aktiviteter, {hent.n} kald.")


if __name__ == "__main__":
    main()
