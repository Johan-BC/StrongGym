"""
Fælles stier for kortlægnings-scripts.

Normalt ligger alt i denne mappe (data/, adgang.json, holdtyper.json, ...) og
styring-*.json i repo-roden. opdater.py bygger i en midlertidig arbejdsmappe og
sætter derfor:
  KORTLAEG_DIR  mappen med data/, adgang.json, holdtyper.json, deltagelse*.json
  STYRING_UD    mappen hvor styring-*.json skrives
  STYRING_FORRIGE  mappen med de forrige styring-*.json (til fornuftskontrol)
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

KORTLAEG_DIR = os.environ.get("KORTLAEG_DIR") or HERE
DATA_DIR = os.path.join(KORTLAEG_DIR, "data")
STYRING_UD = os.environ.get("STYRING_UD") or REPO
STYRING_FORRIGE = os.environ.get("STYRING_FORRIGE") or REPO


def snapshot_tid():
    """Tidspunkt (lokal tid) for holdplanens øjebliksbillede.

    holdplan_meta.json skrives af den lette natlige opdatering (holdplan.py). Den
    fulde kortlægning (kortlaeg.py) sletter data/*.json og skriver adgang.json -
    så bruges adgang.json["generated"] som før."""
    meta = os.path.join(DATA_DIR, "holdplan_meta.json")
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as f:
            return json.load(f)["generated"], "holdplan_meta.json"
    with open(os.path.join(KORTLAEG_DIR, "adgang.json"), encoding="utf-8") as f:
        return json.load(f)["generated"], "adgang.json"


def forrige(navn):
    """Indlæs forrige styring-*.json (eller None)."""
    p = os.path.join(STYRING_FORRIGE, navn)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except ValueError:
        return None
