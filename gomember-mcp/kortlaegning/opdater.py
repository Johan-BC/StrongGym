#!/usr/bin/env python3
"""
Natlig opdatering af de tre datafiler til styring.html - én kommando:

    python3 gomember-mcp/kortlaegning/opdater.py                 # i dag (Europe/Copenhagen)
    python3 gomember-mcp/kortlaegning/opdater.py --dato 2026-11-15   # test: regn "i dag" som en anden dato
    python3 gomember-mcp/kortlaegning/opdater.py --force         # tillad store spring i tallene

Trin (alle kald er GET gennem GoMemberClient.get(); se ../CLAUDE.md):
  1. Holdplan    holdplan.py: holdplan 8 uger tilbage -> 8 uger frem, aktiviteter,
                 etiketter, produkter (ca. 8 kald). Ingen medlems-kald.
  2. Holdtyper   analyse_holdtyper.py (offline)
  3. Ugeplan     byg_styringsdata.py (offline) -> styring-data.json
  4. Medlemstal  byg_medlemsstatistik.py (ca. 23 kald: liste, etiketter, udmeldingsdato) -> styring-medlemmer.json
  5. Deltagelse  deltagelse.py med cache (typisk 50-100 kald) -> deltagelse.json
  6. Statistik   byg_statistikdata.py (offline) -> styring-statistik.json

Alt bygges i en midlertidig mappe. Først når ALLE trin og kontroller er gået
igennem, erstattes styring-*.json og mellemfilerne. Fejler noget, røres ingen
filer, der skrives en kort dansk forklaring, og exit-koden er 1.

Sikkerhed: maks 2 kald/s, timeout 30 s, højst 2 genforsøg pr. fejlet kald,
aldrig genforsøg af et fejlet login, loft på 600 kald pr. kørsel. Ingen
persondata, tokens eller adgangskoder i udskriften.
"""
import argparse
import datetime as dt
import fcntl
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
TZ = ZoneInfo("Europe/Copenhagen")
LOFT = 600
STYRING_FILER = ("styring-data.json", "styring-medlemmer.json", "styring-statistik.json")
MELLEM_FILER = ("holdtyper.json", "deltagelse.json", "deltagelse_cache.json")
HOLDPLAN_DATA = ("activity.json", "tag.json", "product.json", "holdplan_meta.json")
TIDSFELTER = {"snapshot", "hentet", "bygget", "generated"}
WD = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]


class TrinFejl(RuntimeError):
    pass


def maskér(tekst):
    """Fjern eventuelle login-værdier fra en tekst, før den udskrives."""
    tekst = str(tekst)
    for k in ("GOMEMBER_PASSWORD", "GOMEMBER_USERNAME", "GOMEMBER_CLIENT_ID", "GOMEMBER_CLIENT_BASIC"):
        v = os.environ.get(k)
        if v and len(v) >= 3:
            tekst = tekst.replace(v, "***")
    return tekst[:300]


def koer_script(navn, *args):
    """Kør et offline byggescript i arbejdsmappen (miljøvariablerne peger derhen)."""
    r = subprocess.run([sys.executable, os.path.join(HERE, navn), *args], capture_output=True, text=True,
                       env=os.environ.copy(), timeout=600)
    if r.returncode != 0:
        linjer = [x.strip() for x in (r.stderr or r.stdout or "").splitlines() if x.strip()]
        fejl = [x for x in linjer if x.startswith(("FEJL", "- ", "ADVARSEL"))] or linjer[-1:]
        raise TrinFejl(f"{navn} stoppede: " + maskér(" ".join(fejl[:6]) or f"exit {r.returncode}"))
    return r.stdout


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _tider(x, ud):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in TIDSFELTER and isinstance(v, str):
                ud.add(v)
            _tider(v, ud)
    elif isinstance(x, list):
        for v in x:
            _tider(v, ud)
    return ud


def uden_tid(x):
    """JSON som tekst uden tidsstempler (felterne i TIDSFELTER og samme værdier andre steder)."""
    s = json.dumps(x, sort_keys=True, ensure_ascii=False)
    for t in sorted(_tider(x, set()), key=len, reverse=True):
        s = s.replace(json.dumps(t, ensure_ascii=False), '""')
    return s


def sammenlign(ny, gammel):
    """'ny' / 'ændret' / 'kun tidsstempel' / 'uændret'."""
    if not os.path.exists(gammel):
        return "ny"
    with open(ny, "rb") as a, open(gammel, "rb") as b:
        if a.read() == b.read():
            return "uændret"
    try:
        return "kun tidsstempel" if uden_tid(load(ny)) == uden_tid(load(gammel)) else "ændret"
    except ValueError:
        return "ændret"


def erstat(ny, maal):
    """Kopiér ny -> maal atomisk (via midlertidig fil i samme mappe)."""
    os.makedirs(os.path.dirname(maal), exist_ok=True)
    tmp = maal + ".opdater-ny"
    shutil.copyfile(ny, tmp)
    os.replace(tmp, maal)


def ugetal(sd):
    """Træningshold (ikke aflyste) i snapshot-ugen, som Overblik tæller dem."""
    snap = dt.datetime.fromisoformat(sd["snapshot"])
    man = (snap - dt.timedelta(days=snap.weekday())).date()
    fra, til = man.isoformat(), (man + dt.timedelta(days=7)).isoformat()
    training = {t["id"] for t in sd["types"] if t.get("training")}
    uge = [e for e in sd["events"] if fra <= e["start"][:10] < til and e["typeId"] in training
           and e["status"] != "cancelled"]
    naeste7 = [e for e in sd["events"] if sd["snapshot"][:16] <= e["start"]
               < (snap + dt.timedelta(days=7)).isoformat()[:16] and e["status"] != "cancelled"]
    return len(uge), len(naeste7), int(man.strftime("%V"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dato", help="regn denne dato (YYYY-MM-DD) som 'i dag' - til test")
    ap.add_argument("--force", action="store_true", help="tillad store spring i forhold til forrige filer")
    ap.add_argument("--loft", type=int, default=LOFT, help=f"maks kald pr. kørsel (standard {LOFT})")
    a = ap.parse_args(argv)

    t0 = time.time()
    nu = dt.datetime.now(TZ).replace(tzinfo=None, microsecond=0)
    idag = nu.date()
    if a.dato:
        try:
            idag = dt.date.fromisoformat(a.dato)
        except ValueError:
            print("FEJL: --dato skal være på formen ÅÅÅÅ-MM-DD.", file=sys.stderr)
            return 2
        nu = dt.datetime.combine(idag, nu.time())

    # Kun én kørsel ad gangen
    laas = open(os.path.join(tempfile.gettempdir(), "strong-gym-styring-opdater.lock"), "w")
    try:
        fcntl.flock(laas, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("FEJL: en anden opdatering kører allerede. Intet er ændret.", file=sys.stderr)
        return 1

    arbejd = tempfile.mkdtemp(prefix="styring-opdater-")
    W = os.path.join(arbejd, "kortlaegning")
    UD = os.path.join(arbejd, "ud")
    os.makedirs(UD)
    shutil.copytree(os.path.join(HERE, "data"), os.path.join(W, "data"))
    for f in ("adgang.json",) + MELLEM_FILER:
        if os.path.exists(os.path.join(HERE, f)):
            shutil.copy2(os.path.join(HERE, f), os.path.join(W, f))
    os.environ["KORTLAEG_DIR"] = W
    os.environ["STYRING_UD"] = UD
    os.environ["STYRING_FORRIGE"] = REPO

    # Importeres først nu, så stier.py peger på arbejdsmappen
    sys.path.insert(0, HERE)
    import netlag
    import holdplan
    import byg_medlemsstatistik
    import deltagelse

    hent = netlag.Hentning(loft=a.loft)
    force = ["--force"] if a.force else []
    res = {}
    noter = []
    trin = "Start"
    try:
        trin = "1/6 Holdplan"
        res["holdplan"] = holdplan.hent_holdplan(hent, os.path.join(W, "data"), idag, nu)

        trin = "2/6 Holdtyper"
        koer_script("analyse_holdtyper.py", "--quiet")
        ukendte = load(os.path.join(W, "holdtyper.json"))["_meta"].get("ukendte_aktiviteter") or []
        for u in ukendte:
            noter.append(f"Ny aktivitet uden holdtype: '{u.get('navn') or u['activityId']}' -> vist som "
                         "'Ukendt (ny aktivitet)'. Placér den i MAPPING i analyse_holdtyper.py.")

        trin = "3/6 Ugeplan"
        koer_script("byg_styringsdata.py", *force)

        if hent.anonym:
            noter.append("Intet login sat (GOMEMBER_USERNAME/PASSWORD): medlemstal og statistik er IKKE "
                         "opdateret - de gamle filer er beholdt.")
        else:
            trin = "4/6 Medlemstal"
            n_foer = hent.n
            res["medlemmer"] = byg_medlemsstatistik.byg(
                hent, now=dt.datetime.combine(idag, nu.time(), tzinfo=TZ),
                ud=os.path.join(UD, "styring-medlemmer.json"), force=a.force)
            res["medlemmer"]["http"] = hent.n - n_foer

            trin = "5/6 Deltagelse"
            n_foer = hent.n
            deltagelse.configure(idag, nu, hent=hent, mappe=W)
            res["deltagelse"] = deltagelse.koer()
            res["deltagelse"]["http"] = hent.n - n_foer

            trin = "6/6 Statistik"
            koer_script("byg_statistikdata.py", *force)
    except (netlag.NetFejl, deltagelse.CapReached, TrinFejl) as e:
        return fejl(trin, maskér(e), hent, arbejd)
    except subprocess.TimeoutExpired:
        return fejl(trin, "et byggetrin tog over 10 minutter.", hent, arbejd)
    except Exception as e:  # noqa: BLE001 - uventet: kort besked, ingen data
        return fejl(trin, f"uventet fejl ({type(e).__name__}: {maskér(e)[:150]})", hent, arbejd)

    # ------------------------------------------------ alt gik godt: erstat filerne
    par = [(os.path.join(UD, f), os.path.join(REPO, f)) for f in STYRING_FILER
           if os.path.exists(os.path.join(UD, f))]
    par += [(os.path.join(W, f), os.path.join(HERE, f)) for f in MELLEM_FILER
            if os.path.exists(os.path.join(W, f)) and not (hent.anonym and f.startswith("deltagelse"))]
    nye_sched = sorted(glob.glob(os.path.join(W, "data", "schedule_*.json")))
    par += [(p, os.path.join(HERE, "data", os.path.basename(p))) for p in nye_sched]
    par += [(os.path.join(W, "data", f), os.path.join(HERE, "data", f)) for f in HOLDPLAN_DATA]
    status = [(os.path.relpath(m, REPO), sammenlign(n, m)) for n, m in par]
    for n, m in par:
        erstat(n, m)
    behold = {os.path.basename(p) for p in nye_sched}
    fjernet = []
    for p in glob.glob(os.path.join(HERE, "data", "schedule_*.json")):
        if os.path.basename(p) not in behold:
            os.remove(p)
            fjernet.append(os.path.relpath(p, REPO))
    shutil.rmtree(arbejd, ignore_errors=True)

    # ------------------------------------------------ opsummering
    sd = load(os.path.join(REPO, "styring-data.json"))
    uge, naeste7, ugenr = ugetal(sd)
    print(f"Opdatering gennemført {nu:%d-%m-%Y kl. %H:%M} ({time.time() - t0:.0f} s, "
          f"{hent.n} kald til goMember, {hent.logins} login, {hent.genforsoeg} genforsøg, tilstand: {hent.tilstand}).")
    hp = res["holdplan"]
    print(f"- Ugeplan: {uge} træningshold i uge {ugenr}, {naeste7} hold de næste 7 dage; "
          f"{hp['schedule_window']['events_total']} hold i vinduet, {hp['events_with_named_trainer']} med synlig træner "
          f"({hp['requests_made']} kald).")
    if "medlemmer" in res:
        m = res["medlemmer"]
        print(f"- Medlemmer: {m['medlemmer']} i alt" + (f" (før: {m['forrige']})" if m.get("forrige") else "")
              + f" ({m['http']} kald).")
        u = m.get("udmeldinger") or {}
        if u:
            print(f"- Udmeldingsdato ('{u['etiket']}'): {u['medEtiket']} med etiketten, {u['medDato']} med dato "
                  f"({u['passeret']} allerede passeret, {u['kommende']} kommende), {u['udenDato']} uden dato"
                  + (f", {u['kunneIkkeHentes']} kunne ikke hentes" if u['kunneIkkeHentes'] else "") + ".")
    if "deltagelse" in res:
        st = load(os.path.join(REPO, "styring-statistik.json"))
        d = res["deltagelse"]
        print(f"- Statistik {st['periode']['fra']} – {st['periode']['til']}: {st['i_alt']['afholdt']} hold afholdt, "
              f"{st['i_alt']['tilmeldte']} tilmeldinger ({d['http']} kald).")
    for n in noter:
        print("- OBS:", n)
    print("Filer:")
    for f, s in status:
        if f.startswith("styring-") or s not in ("uændret",):
            print(f"  {s:16s} {f}")
    for f in fjernet:
        print(f"  {'fjernet':16s} {f}")
    return 0


def fejl(trin, grund, hent, arbejd):
    shutil.rmtree(arbejd, ignore_errors=True)
    print(f"FEJL i trin {trin}: {grund}", file=sys.stderr)
    print(f"Ingen filer er ændret. ({hent.n} kald til goMember i denne kørsel.)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
