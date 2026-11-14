#!/usr/bin/env python3
"""
Bygger ../../styring-statistik.json til fanen "Statistik" i styring.html.

    python3 deltagelse.py --offline   # (eller uden --offline) -> deltagelse.json
    python3 byg_statistikdata.py      # -> styring-statistik.json

Kører helt offline: læser kun deltagelse.json (+ holdtyper.json for navne og
farver). Ingen kald til goMember, ingen persondata - kun antal pr. holdtype,
ugedag, tidspunkt, måned og uge. Ingen tal pr. træner.

Alle tal regnes forfra ud fra rækkerne i deltagelse.json -> "hold" og
kontrolleres mod de summer deltagelse.py selv har skrevet (i_alt, pr_type,
pr_maaned, pr_uge, pr_fast_tid, top/bund). Stemmer noget ikke, stopper
scriptet med en fejl, og der skrives ingen fil.

Regler (samme som DELTAGELSE.md):
- Kun hold med klassifikation "afholdt" (mindst 1 tilmeldt) indgår i snit,
  pladser og fyldning.
- Aflyste, udeladte (taget ud af serien) og hold med 0 tilmeldte tælles for sig.
- Rengøring, Ungeenheden og andet der ikke er træning er helt udeladt.
- Fyldning = tilmeldte / pladser, kun for hold med et pladsloft.
"""
import collections
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(HERE, "deltagelse.json")
HOLDTYPER = os.path.join(HERE, "holdtyper.json")
OUT = os.path.join(ROOT, "styring-statistik.json")

WD = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
FAST_MIN = 8        # en "fast tid" har mindst 8 afholdte hold i perioden (som deltagelse.py)
FAA_HOLD = 4        # færre afholdte hold end dette = "få hold" (nedtonet i varmekortet)
EXPECT = {"afholdt": 560, "tilmeldte": 4526}

errors = []


def check(label, got, want):
    if got != want:
        errors.append(f"{label}: beregnet {got!r}, deltagelse.json siger {want!r}")


def r1(x):
    return None if x is None else round(x, 1)


def agg(rs):
    held = [r for r in rs if r["klassifikation"] == "afholdt"]
    capd = [r for r in held if r["capacity"]]
    cap = sum(r["capacity"] for r in capd)
    bk = sum(r["booked"] for r in held)
    return {
        "afholdt": len(held),
        "tilmeldte": bk,
        "snit": round(bk / len(held), 2) if held else None,
        "pladser": cap,
        "fyldning": r1(100 * sum(r["booked"] for r in capd) / cap) if cap else None,
        "fuldt": sum(1 for r in capd if r["booked"] >= r["capacity"]),
        "aflyst": sum(1 for r in rs if r["klassifikation"] == "aflyst"),
        "udeladt": sum(1 for r in rs if r["klassifikation"] == "udeladt"),
        "nul": sum(1 for r in rs if r["klassifikation"] == "nul"),
    }


# Felter vi sammenligner med deltagelse.py's egne summer (deres navn -> vores)
CMP = {"afholdt": "afholdt", "tilmeldte": "tilmeldte", "snit_pr_hold": "snit", "pladser": "pladser",
       "fyldning_pct": "fyldning", "fuldt_booket": "fuldt", "aflyst": "aflyst",
       "udeladt_af_serien": "udeladt", "nul_tilmeldte": "nul"}


def cross(label, ours, theirs):
    for k_their, k_our in CMP.items():
        if k_their in theirs:
            check(f"{label}.{k_their}", ours[k_our], theirs[k_their])


def main():
    d = json.load(open(SRC, encoding="utf-8"))
    ht = json.load(open(HOLDTYPER, encoding="utf-8"))
    tnavn = {t["id"]: t["navn"] for t in ht["holdtyper"]}
    tfarve = {t["id"]: t["farve"] for t in ht["holdtyper"]}

    alle = d["hold"]
    rows = [r for r in alle if r["klassifikation"] != "ikke_traening"]
    fra, til = d["_meta"]["vindue"]
    for r in rows:
        if r["ugedag"] not in WD:
            errors.append(f"ukendt ugedag {r['ugedag']!r}")
        wd = dt.date.fromisoformat(r["dato"]).weekday()
        if WD[wd] != r["ugedag"]:
            errors.append(f"ugedag passer ikke med dato: {r['dato']} {r['ugedag']}")
        if not (fra <= r["dato"] <= til):
            errors.append(f"hold uden for perioden: {r['dato']}")
    if errors:
        fail()

    # ---------------- i alt
    tot = agg(rows)
    cross("i_alt", tot, d["i_alt"])
    for k, v in EXPECT.items():
        check(f"forventet {k}", tot[k], v)
    held = [r for r in rows if r["klassifikation"] == "afholdt"]
    tot["venteliste"] = sum(r["waitingList"] for r in held)
    tot["hold_med_venteliste"] = sum(1 for r in held if r["waitingList"] > 0)
    check("i_alt.venteliste_i_alt", tot["venteliste"], d["i_alt"]["venteliste_i_alt"])
    check("i_alt.hold_med_venteliste", tot["hold_med_venteliste"], d["i_alt"]["hold_med_venteliste"])
    tot["nul_tilmeldte_snit_hvis_med"] = round(tot["tilmeldte"] / (tot["afholdt"] + tot["nul"]), 2)
    aarsag = collections.Counter(r["aflysningsaarsag"] or "andet/ukendt" for r in rows if r["klassifikation"] == "aflyst")
    tot["aflyst_aarsag"] = [{"aarsag": k, "antal": n} for k, n in aarsag.most_common()]
    check("aflyst_aarsag sum", sum(aarsag.values()), tot["aflyst"])
    # Ikke-træning (kun antal, så man kan se hvad der er udeladt)
    ikke = collections.Counter(tnavn.get(r["typeId"], r["typeId"]) for r in alle if r["klassifikation"] == "ikke_traening")

    # ---------------- pr. holdtype
    by_type = collections.defaultdict(list)
    for r in rows:
        by_type[r["typeId"]].append(r)
    if set(by_type) != set(d["pr_type"]):
        errors.append(f"holdtyper: {sorted(by_type)} != {sorted(d['pr_type'])}")
    typer = []
    for tid, rs in by_type.items():
        a = agg(rs)
        cross(f"pr_type[{tid}]", a, d["pr_type"].get(tid, {}))
        typer.append(dict(id=tid, navn=tnavn.get(tid, d["pr_type"].get(tid, {}).get("navn", tid)),
                          farve=tfarve.get(tid, "888888"), **a))
    typer.sort(key=lambda t: (-t["afholdt"], -t["tilmeldte"]))
    for f in ("afholdt", "tilmeldte", "aflyst", "fuldt", "udeladt", "nul", "pladser"):
        check(f"sum pr. type {f}", sum(t[f] for t in typer), tot[f])

    # ---------------- pr. ugedag
    by_wd = collections.defaultdict(list)
    for r in rows:
        by_wd[WD.index(r["ugedag"])].append(r)
    ugedage = [dict(i=i, navn=WD[i], **agg(by_wd[i])) for i in range(7)]
    for f in ("afholdt", "tilmeldte", "aflyst", "fuldt", "udeladt", "nul", "pladser"):
        check(f"sum pr. ugedag {f}", sum(u[f] for u in ugedage), tot[f])

    # ---------------- pr. ugedag x tidspunkt x holdtype (tidspunkt = holdets faktiske starttid)
    by_slot = collections.defaultdict(list)
    for r in rows:
        by_slot[(WD.index(r["ugedag"]), r["start"], r["typeId"])].append(r)
    tider = []
    for (wi, st, tid), rs in by_slot.items():
        a = agg(rs)
        key = f"{WD[wi]} {st} {tnavn.get(tid, tid)}"
        if key not in d["pr_fast_tid"]:
            errors.append(f"tid {key!r} findes ikke i deltagelse.json pr_fast_tid")
        else:
            cross(f"pr_fast_tid[{key}]", a, d["pr_fast_tid"][key])
        tider.append(dict(d=wi, t=st, type=tid, foerste=min(r["dato"] for r in rs),
                          sidste=max(r["dato"] for r in rs), fast=a["afholdt"] >= FAST_MIN, **a))
    if len(tider) != len(d["pr_fast_tid"]):
        errors.append(f"antal tider {len(tider)} != {len(d['pr_fast_tid'])}")
    tider.sort(key=lambda s: (s["d"], s["t"], s["type"]))
    for f in ("afholdt", "tilmeldte", "aflyst"):
        check(f"sum pr. tid {f}", sum(s[f] for s in tider), tot[f])

    # Top / bund blandt faste tider (samme sortering som deltagelse.py)
    fixed = [s for s in tider if s["fast"]]
    fixed.sort(key=lambda s: (-s["snit"], -s["afholdt"]))
    name = lambda s: f"{WD[s['d']]} {s['t']} {tnavn.get(s['type'], s['type'])}"
    for lst, ref, lab in ((fixed[:10], d["top_10_faste_tider"], "top"), (fixed[::-1][:10], d["bund_10_faste_tider"], "bund")):
        check(f"{lab} 10", [name(s) for s in lst], [x["tid"] for x in ref])
    pick = lambda s: {k: s[k] for k in ("d", "t", "type", "afholdt", "tilmeldte", "snit", "fyldning", "fuldt")}
    top = [pick(s) for s in fixed[:5]]
    bund = [pick(s) for s in fixed[::-1][:5]]

    # ---------------- holdtype x ugedag
    matrix = []
    for t in typer:
        cells = []
        for i in range(7):
            a = agg([r for r in by_type[t["id"]] if WD.index(r["ugedag"]) == i])
            cells.append({"afholdt": a["afholdt"], "snit": a["snit"], "fyldning": a["fyldning"]} if a["afholdt"] else None)
        matrix.append({"type": t["id"], "celler": cells})
    check("matrix sum afholdt", sum(c["afholdt"] for m in matrix for c in m["celler"] if c), tot["afholdt"])

    # ---------------- pr. måned
    by_m = collections.defaultdict(list)
    for r in rows:
        by_m[r["dato"][:7]].append(r)
    if sorted(by_m) != sorted(d["pr_maaned"]):
        errors.append("måneder passer ikke")
    maaneder = []
    for m in sorted(by_m):
        a = agg(by_m[m])
        cross(f"pr_maaned[{m}]", a, d["pr_maaned"][m])
        dage = sorted({r["dato"] for r in by_m[m]})
        first = max(fra, m + "-01")
        last_of_month = (dt.date(int(m[:4]), int(m[5:]), 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        last = min(til, last_of_month.isoformat())
        partial = first != m + "-01" or last != last_of_month.isoformat()
        src = d["pr_maaned"][m]
        maaneder.append(dict(m=m, fra=first, til=last, delvis=partial,
                             fremmoede_hold=src["hold_med_fremmoede_registrering"],
                             fremmoede_pct=src["fremmoede_pct_af_tilmeldte"], **a))
    for f in ("afholdt", "tilmeldte", "aflyst"):
        check(f"sum pr. måned {f}", sum(m[f] for m in maaneder), tot[f])

    # ---------------- pr. uge (ISO)
    by_w = collections.defaultdict(list)
    for r in rows:
        by_w[dt.date.fromisoformat(r["dato"]).strftime("%G-U%V")].append(r)
    if sorted(by_w) != sorted(d["pr_uge"]):
        errors.append("uger passer ikke")
    uger = []
    d_fra, d_til = dt.date.fromisoformat(fra), dt.date.fromisoformat(til)
    for w in sorted(by_w):
        a = agg(by_w[w])
        cross(f"pr_uge[{w}]", a, d["pr_uge"][w])
        y, n = int(w[:4]), int(w[6:])
        mon = dt.date.fromisocalendar(y, n, 1)
        sun = mon + dt.timedelta(days=6)
        uger.append({"uge": n, "mandag": mon.isoformat(), "delvis": mon < d_fra or sun > d_til,
                     "afholdt": a["afholdt"], "tilmeldte": a["tilmeldte"], "snit": a["snit"],
                     "fyldning": a["fyldning"], "aflyst": a["aflyst"]})
    check("sum pr. uge afholdt", sum(u["afholdt"] for u in uger), tot["afholdt"])

    # ---------------- fremmøde (kun som forklaring på hvorfor vi tæller tilmeldte)
    ia = d["i_alt"]
    fremmoede = {
        "hold_med_registrering": ia["hold_med_fremmoede_registrering"],
        "afholdt": ia["afholdt"],
        "fremmoedte": ia["fremmoede_registreret"],
        "pct_af_tilmeldte": ia["fremmoede_pct_af_tilmeldte"],
        "nov_hold_med_registrering": d["pr_maaned"].get("2026-11", {}).get("hold_med_fremmoede_registrering"),
        "nov_afholdt": d["pr_maaned"].get("2026-11", {}).get("afholdt"),
        "tekst": "Fra maj til midt i oktober blev fremmøde registreret på de fleste hold, og ca. 9 ud af 10 "
                 "tilmeldte mødte op. Efter flytningen til Industrivej er det næsten holdt op. Derfor tæller "
                 "statistikken tilmeldte, ikke fremmødte.",
    }

    if errors:
        fail()

    out = {
        "_om": "Samlede tal om deltagelse på hold, bygget offline af gomember-mcp/kortlaegning/byg_statistikdata.py "
               "ud fra deltagelse.json. Kun antal - ingen navne, medlems-id'er eller tal pr. træner.",
        "bygget": dt.datetime.now().isoformat(timespec="minutes"),
        "periode": {"fra": fra, "til": til},
        "regler": {"fast_tid_min_afholdt": FAST_MIN, "faa_hold_under": FAA_HOLD},
        "i_alt": tot,
        "ikke_traening_udeladt": [{"navn": k, "antal": n} for k, n in ikke.most_common()],
        "typer": typer,
        "ugedage": ugedage,
        "tider": tider,
        "type_x_ugedag": matrix,
        "maaneder": maaneder,
        "uger": uger,
        "top5": top,
        "bund5": bund,
        "fremmoede": fremmoede,
        "definitioner": [
            {"term": "Afholdt hold", "tekst": "Et træningshold, der ikke var aflyst eller taget ud af serien, og som havde mindst 1 tilmeldt."},
            {"term": "Tilmeldte", "tekst": "Antal tilmeldte på holdet, efter det var afholdt (goMembers \"booked\"). Afmeldinger før holdet er ikke med. Det er ikke det samme som fremmødte."},
            {"term": "Snit pr. hold", "tekst": "Tilmeldte delt med antal afholdte hold."},
            {"term": "Pladser brugt", "tekst": "Tilmeldte delt med pladser i alt på de afholdte hold (fx 12 på WOD, 8 på Basis/teknik)."},
            {"term": "Fuldt booket", "tekst": "Afholdt hold hvor tilmeldte nåede pladsloftet."},
            {"term": "Aflyst", "tekst": "Holdet stod som aflyst i goMember. Tælles for sig og er ikke med i snittet."},
            {"term": "Taget ud af serien", "tekst": "Datoen var fjernet fra det faste hold i goMember, fx på helligdage eller ved flytningen. Tælles for sig."},
            {"term": "0 tilmeldte", "tekst": "Holdet fandtes, men ingen var tilmeldt. Tælles for sig og er ikke med i snittet."},
            {"term": "Fast tid", "tekst": f"Ugedag, starttid og holdtype med mindst {FAST_MIN} afholdte hold i perioden."},
        ],
    }
    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(s + "\n")
    print(f"Skrev {OUT} ({len(s.encode('utf-8')) / 1024:.1f} KB). "
          f"{tot['afholdt']} hold afholdt, {tot['tilmeldte']} tilmeldte, snit {tot['snit']}, fyldning {tot['fyldning']} %. "
          "Alle kontroller mod deltagelse.json stemmer.")


def fail():
    print("FEJL: tallene stemmer ikke med deltagelse.json - der er ikke skrevet nogen fil.", file=sys.stderr)
    for e in errors:
        print("  -", e, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
