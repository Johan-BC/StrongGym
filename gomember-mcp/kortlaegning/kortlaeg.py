#!/usr/bin/env python3
"""
Kortlægning af hvad goMember/MemberLink udstiller UDEN login.

- Bruger udelukkende GoMemberClient(anonymous=True) -> kun GET, intet token,
  ingen Authorization-header, /auth/token kaldes aldrig.
- ALLOWLIST: et path kaldes kun hvis tag er i ALLOWED_TAGS, path ikke er i
  generate.DENIED_PATHS, intet path-segment indeholder et "verbum" fra
  FORBIDDEN_WORDS, og det ikke er et lavniveau ?partitionKey=&rowKey=-endpoint.
- Høflig: maks ~2 kald/sekund, timeout 30s (i klienten), maks MAX_REQUESTS kald.
- Path-id'er tages kun fra data som offentlige kald allerede har returneret;
  maks 3 id-værdier pr. parameteriseret path.
- Persondata: bookinger/fremmøde/medlemmer reduceres til antal + feltnavne og
  gemmes aldrig rå. Gemte snapshots køres gennem sanitize(), som kun beholder
  trænernavne (responsible[].displayName), der i forvejen er offentlige.

Kør fra gomember-mcp/:  python3 kortlaegning/kortlaeg.py
"""
import ast
import datetime as dt
import json
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from gomember_client import GoMemberClient  # noqa: E402

SWAGGER = os.path.join(ROOT, "SGSwagger.json")
DATA_DIR = os.path.join(HERE, "data")
OUT_CATALOG = os.path.join(HERE, "adgang.json")

TODAY = dt.date(2026, 11, 14)
WINDOW_FROM = TODAY - dt.timedelta(weeks=8)
WINDOW_TO = TODAY + dt.timedelta(weeks=8)
EVENTS_CAP = 300
MAX_REQUESTS = 400
MIN_INTERVAL = 0.5  # sekunder -> maks 2 kald/s
MAX_IDS_PER_PATH = 3
SIGNUP_TAG = "Tag2517869245434174618"

ALLOWED_TAGS = {
    "ActivityApi", "ActivityDataApi", "ActivityEventDataApi", "EventApi", "EventNewApi",
    "BookingApi", "TagApi", "TagDataApi", "TagCategoryDataApi", "PriceApi", "PriceDataApi",
    "ProductApi", "SignupApi", "TagPriceDataApi",
}
FORBIDDEN_WORDS = [
    "clone", "update", "batch", "delete", "remove", "create", "add", "assign", "send", "cancel",
    "pay", "refund", "lock", "unlock", "move", "copy", "import", "sync", "generate", "reset",
    "approve", "confirm", "invite", "merge", "process", "activate", "export", "notify", "mail",
    "sms", "validatecancel",
]
# Segmenter der indeholder et forbudt ord, men som efter manuel vurdering er
# læse-navneord. "locked" = liste over låste pladser (tilstand, ikke handling).
SEGMENT_EXCEPTIONS = {"locked"}
# "book" som verbum-segment (fx /book, /bookevent). /api/booking og /bookings er læsninger.
BOOK_VERB_RE = re.compile(r"^book($|[a-z]*$)")
BOOK_READ_SEGMENTS = {"booking", "bookings", "booked-resources"}
# Manuelt vurderet som usikre -> springes over
UNSURE = {
    "/api/tagdata/reorder/{category}/{id}": "skipped – unsure (reorder lyder som en ændring)",
}

# Endpoints hvis svar kan indeholde medlemsdata: kun antal + feltnavne, gemmes aldrig.
PERSONAL_PATHS = {
    "/api/booking", "/api/booking/{id}",
    "/api/activity/{activityId}/event/{eventId}/bookings",
    "/api/activity/{activityId}/event/{eventId}/bookings/{id}",
    "/api/activity/{activityId}/event/{eventId}/locked",
    "/api/activity/{activityId}/attendance",
    "/api/activity/{activityId}/member/{memberId}",
    "/api/booking/grid/{activityId}", "/api/booking/calendar/{activityId}",
    "/api/booking/partners/{activityId}", "/api/booking/griddata/{activityId}",
    "/api/booking/booked-resources/{activityId}",
    "/api/tagdata/members/{id}",
    "/api/signup/family", "/api/signup/GetOrderForMember/{exclusive}",
}

# Medlems-tælling (pkt. 5): maks 6 liste-endpoints, ét kald hver, mindste sidestørrelse.
MEMBER_PROBES = [
    ("/api/members", {"filter.pageSize": 1, "filter.currentPage": 1}),
    ("/api/memberdata/grid/data", {"sidx": "", "sord": "asc", "page": 1, "rows": 1, "searchText": "",
                                   "tagFilter": "", "allTagFilter": "", "notTagFilter": "",
                                   "departmentFilter": "", "customFilter": ""}),
    ("/api/members/gallery", {}),
    ("/api/members/family", {}),
    ("/api/members/dataresponsible", {}),
    ("/api/members/me", {}),
]

GRID_Q = {"sidx": "", "sord": "asc", "page": 1, "rows": 100, "searchText": "", "tagFilter": "",
          "notTagFilter": "", "departmentFilter": "", "customFilter": ""}


def iso(d):
    return dt.datetime.combine(d, dt.time()).isoformat()


NEAR_FROM, NEAR_TO = iso(TODAY), iso(TODAY + dt.timedelta(days=14))
EVENT_FILTER_Q = {"eventsToShow": EVENTS_CAP, "fromOffset": NEAR_FROM, "toTime": NEAR_TO}

# ---------------------------------------------------------------- persondata

PERSONAL_KEY_RE = re.compile(
    r"(email|e-mail|phone|mobile|telefon|address|adresse|street|zip|postal|cpr|ssn|birth|"
    r"firstname|lastname|fullname|membernumber|memberid|guest|password|token|iban|account)", re.I)
PERSONAL_LIST_KEYS = {"invitemembers", "attendees", "participants", "members", "bookings",
                      "booked_members", "waitinglistmembers", "partners", "persons",
                      "responsibleusersids"}
# Altid fjernet uanset værditype (medlemsnumre/-id'er kan være tal)
ALWAYS_STRIP_RE = re.compile(r"(membernumber|memberid|cpr|ssn)", re.I)


def sanitize(x, parent_key=""):
    """Fjern medlems-identificerende værdier. Behold trænernavne (responsible[].displayName)."""
    if isinstance(x, list):
        if parent_key.lower() in PERSONAL_LIST_KEYS:
            return {"_count": len(x)}
        if parent_key.lower() == "responsible":
            return [{"displayName": r.get("displayName")} if isinstance(r, dict) else r for r in x]
        return [sanitize(i, parent_key) for i in x]
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            kl = k.lower()
            if ALWAYS_STRIP_RE.search(kl) or (PERSONAL_KEY_RE.search(kl) and isinstance(v, str)):
                # kun tekstværdier (fx maxGuestsPerMember=int og checkEmail=bool er ikke persondata)
                out[k] = "<fjernet>" if v not in (None, "", [], {}) else v
            elif kl in ("membername", "username", "firstname", "lastname") and v:
                out[k] = "<fjernet>"
            elif isinstance(v, (list, dict)) and kl in PERSONAL_LIST_KEYS:
                out[k] = {"_count": len(v)}
            else:
                out[k] = sanitize(v, k)
        return out
    return x


def describe(body):
    """Returnér (kind, item_count, field_names)."""
    if body is None:
        return "error", None, []
    if isinstance(body, dict) and set(body) == {"raw_text"}:
        t = body["raw_text"].lstrip()
        return ("html" if t.startswith("<") else "text"), None, []
    if body in ({}, []):
        return "empty", 0, []
    if isinstance(body, list):
        first = body[0] if body else None
        return "list", len(body), sorted(first.keys()) if isinstance(first, dict) else []
    if isinstance(body, dict):
        count = None
        for k in ("records", "total", "totalCount", "count", "totalRecords", "Total", "Records"):
            if isinstance(body.get(k), int):
                count = body[k]
                break
        for k in ("rows", "items", "data", "Items", "Rows", "results"):
            if isinstance(body.get(k), list) and count is None:
                count = len(body[k])
        return "object", count, sorted(body.keys())
    return "scalar", None, []


def row_fields(body):
    """Feltnavne for én række i en liste/grid (kun navne, aldrig værdier)."""
    if isinstance(body, list) and body and isinstance(body[0], dict):
        return sorted(body[0].keys())
    if isinstance(body, dict):
        for k in ("rows", "items", "data", "Items", "Rows", "results"):
            v = body.get(k)
            if isinstance(v, list) and v:
                r = v[0]
                if isinstance(r, dict):
                    if isinstance(r.get("cell"), list):
                        return [f"cell[{len(r['cell'])}]"] + sorted(k2 for k2 in r if k2 != "cell")
                    return sorted(r.keys())
    return []


def structure(body, prefix="", depth=0, out=None):
    """Indlejrede feltnavne + listelængder (aldrig værdier) - til persondata-endpoints."""
    out = {} if out is None else out
    if depth > 4:
        return out
    if isinstance(body, dict):
        for k, v in body.items():
            kp = f"{prefix}.{k}" if prefix else k
            if isinstance(v, list):
                out[kp] = f"list[{len(v)}]"
                if v:
                    structure(v[0], kp + "[]", depth + 1, out)
            elif isinstance(v, dict):
                out[kp] = f"object[{len(v)}]"
                structure(v, kp, depth + 1, out)
            else:
                out[kp] = type(v).__name__
    elif isinstance(body, list):
        out[prefix or "[]"] = f"list[{len(body)}]"
        if body:
            structure(body[0], (prefix or "") + "[]", depth + 1, out)
    return out


def count_fields(body):
    if isinstance(body, dict):
        return {k: v for k, v in body.items()
                if isinstance(v, (int, float)) and re.search(r"(total|count|records|page)", k, re.I)}
    if isinstance(body, list):
        return {"_list_length": len(body)}
    return {}


# ---------------------------------------------------------------- kald

class Prober:
    def __init__(self):
        self.client = GoMemberClient(anonymous=True)
        self.n = 0
        self._last = 0.0
        self.calls = []

    def get(self, path, path_params=None, query=None, label=None):
        if self.n >= MAX_REQUESTS:
            raise RuntimeError("request-loft nået")
        wait = MIN_INTERVAL - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()
        self.n += 1
        status, body, err, ctype = None, None, "", ""
        try:
            body = self.client.get(path, path_params=path_params, query_params=query)
            status = self.client.last_response.status_code
        except requests.HTTPError as e:
            r = e.response
            status = r.status_code if r is not None else None
            txt = (r.text if r is not None else str(e)) or ""
            err = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))[:200].strip()
        except requests.RequestException as e:
            err = f"{type(e).__name__}: {str(e)[:150]}"
        resp = self.client.last_response
        if resp is not None:
            ctype = resp.headers.get("content-type", "")
        kind, cnt, fields = describe(body) if status == 200 else ("error", None, [])
        if kind == "html" and resp is not None and resp.history:
            err = f"redirect -> {resp.url[:120]}"
        rec = {"path": path, "path_params": path_params or {}, "query": query or {}, "status": status,
               "content_type": ctype.split(";")[0], "kind": kind, "item_count": cnt,
               "fields": fields[:80], "error": err}
        self.calls.append(rec)
        print(f"[{self.n:3d}] {status} {kind:6s} {path} {path_params or ''} -> {cnt if cnt is not None else ''}",
              flush=True)
        return rec, body


def save(name, body):
    with open(os.path.join(DATA_DIR, name), "w", encoding="utf-8") as f:
        json.dump(sanitize(body), f, ensure_ascii=False, indent=1)


def slug(path, params):
    s = path.strip("/").replace("api/", "", 1)
    for k, v in (params or {}).items():
        s = s.replace("{" + k + "}", str(v))
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


# ---------------------------------------------------------------- allowlist

def load_denied():
    tree = ast.parse(open(os.path.join(ROOT, "generate.py"), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "DENIED_PATHS" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise RuntimeError("DENIED_PATHS ikke fundet i generate.py")


def classify(path, denied):
    """Returnér None hvis path må kaldes, ellers skip-årsag."""
    if path in denied:
        return "skipped – DENIED_PATHS i generate.py"
    if path in UNSURE:
        return UNSURE[path]
    if re.fullmatch(r"/api/[A-Za-z]+Api", path):
        return "skipped – lavniveau ?partitionKey=&rowKey= entity-endpoint"
    for seg in path.lower().strip("/").split("/"):
        if seg.startswith("{") or seg in SEGMENT_EXCEPTIONS or seg in BOOK_READ_SEGMENTS:
            continue
        if BOOK_VERB_RE.match(seg):
            return f"skipped – segment '{seg}' (book som verbum)"
        for w in FORBIDDEN_WORDS:
            if w in seg:
                return f"skipped – segment '{seg}' indeholder '{w}'"
    return None


def catalogue_paths(swagger):
    out = []
    for p, ops in swagger["paths"].items():
        op = ops.get("get")
        if not op:
            continue
        tags = op.get("tags", [])
        if set(tags) & ALLOWED_TAGS:
            out.append({"path": p, "tag": tags[0], "requires_security": bool(op.get("security")),
                        "operationId": op.get("operationId")})
    return out


# ---------------------------------------------------------------- main

def main():
    swagger = json.load(open(SWAGGER, encoding="utf-8"))
    denied = load_denied()
    entries = catalogue_paths(swagger)
    pr = Prober()
    os.makedirs(DATA_DIR, exist_ok=True)
    for old in os.listdir(DATA_DIR):  # re-kørbar: fjern gamle snapshots
        if old.endswith(".json"):
            os.remove(os.path.join(DATA_DIR, old))
    results = {}  # path -> list af call-records

    def run(path, pp=None, q=None, save_as=None):
        rec, body = pr.get(path, pp, q)
        results.setdefault(path, []).append(rec)
        if rec["status"] == 200 and path in PERSONAL_PATHS:
            rec["structure"] = dict(list(structure(body).items())[:60])
        if rec["status"] == 200 and path not in PERSONAL_PATHS and rec["kind"] in ("list", "object") and save_as:
            save(save_as, body)
        return rec, body if rec["status"] == 200 else None

    # 1) Holdplan i månedsbidder, 8 uger tilbage -> 8 uger frem
    print("== Holdplan ==")
    slots = []
    chunks = []
    d = WINDOW_FROM
    while d < WINDOW_TO:
        e = min(dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1), WINDOW_TO)
        chunks.append((d, e))
        d = e
    schedule_meta = []
    while chunks:
        a, b = chunks.pop(0)
        q = {"eventsToShow": EVENTS_CAP, "fromOffset": iso(a), "toTime": iso(b)}
        rec, body = run("/api/activity/event/days", None, q)
        if body is None:
            continue
        n = sum(len(x.get("slots", [])) for x in body)
        if n >= EVENTS_CAP and (b - a).days > 1:
            mid = a + (b - a) / 2
            print(f"   {n} events = loft -> deler {a}..{b}")
            chunks[:0] = [(a, mid), (mid, b)]
            continue
        schedule_meta.append({"from": iso(a), "to": iso(b), "days": len(body), "events": n})
        save(f"schedule_{a}_{b}.json", body)
        for day in body:
            slots.extend(day.get("slots", []))

    activity_ids = list(dict.fromkeys(s["activityId"] for s in slots if s.get("activityId")))
    tag_ids = list(dict.fromkeys(t for s in slots for t in (s.get("tagsAssigned") or [])))
    # Seneste fremtidige events først (mest sandsynligt "levende")
    fut = sorted([s for s in slots if s.get("startTime", "") >= iso(TODAY)], key=lambda s: s["startTime"])
    ev_pairs = list(dict.fromkeys((s["activityId"], s["eventId"]) for s in fut))
    ev_entities = list(dict.fromkeys(s["entityId"] for s in fut if s.get("entityId")))
    booked_ev = [(s["activityId"], s["eventId"]) for s in fut if s.get("booked")]
    print(f"   events i alt: {len(slots)}, aktiviteter: {len(activity_ids)}, tags: {len(tag_ids)}")

    # 2) Lister uden path-parametre
    print("== Lister ==")
    plain_queries = {
        "/api/activity": {"filter.pageSize": 200, "filter.currentPage": 1},
        "/api/event": {"filter.pageSize": 200, "filter.currentPage": 1},
        "/api/booking": {"filter.pageSize": 1, "filter.currentPage": 1},
        "/api/activity/event/days": None,  # allerede kaldt
        "/api/event/relevant": EVENT_FILTER_Q,
        "/api/activity/event/list": EVENT_FILTER_Q,
        "/api/activity/event/groups": EVENT_FILTER_Q,
        "/api/event/v3/calendar": EVENT_FILTER_Q,
        "/api/tag": {"filter.pageSize": 500, "filter.currentPage": 1},
        "/api/tagcategorydata/griddata": GRID_Q,
        "/api/tagdata/griddata": GRID_Q,
        "/api/activityeventdata/griddata": dict(GRID_Q, rows=20),
        "/api/tagpricedata/griddata": {"sidx": "", "sord": "asc", "page": 1, "rows": 100,
                                       "customFilter": "", "searchText": ""},
    }
    bodies = {}
    for e in entries:
        p = e["path"]
        e["skip_reason"] = classify(p, denied)
        if e["skip_reason"] or "{" in p:
            continue
        if p in plain_queries and plain_queries[p] is None:
            continue
        rec, body = run(p, None, plain_queries.get(p, {}), save_as=slug(p, None) + ".json")
        bodies[p] = body

    # Id'er fra offentlige svar
    def ids_from(body, keys=("entityId", "id")):
        out = []
        items = body if isinstance(body, list) else (body or {}).get("rows") or (body or {}).get("items") or []
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                for k in keys:
                    if isinstance(it.get(k), str) and it[k]:
                        out.append(it[k])
                        break
        return list(dict.fromkeys(out))

    def find_values(body, key_re):
        found = []

        def walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if re.fullmatch(key_re, k) and isinstance(v, str) and v:
                        found.append(v)
                    walk(v)
            elif isinstance(x, list):
                for i in x:
                    walk(i)
        walk(body)
        return list(dict.fromkeys(found))

    product_ids = ids_from((bodies.get("/api/product") or {}).get("products"), keys=("id", "entityId"))
    cat_ids = find_values([bodies.get("/api/tag"), bodies.get("/api/tagcategorydata/griddata")],
                          r"(category|tagCategoryId|categoryId|TagCategoryId)")
    cat_ids = [c for c in cat_ids if c.startswith("TC")] or cat_ids
    tag_ids_all = list(dict.fromkeys(tag_ids + ids_from(bodies.get("/api/tag"))))
    tagprice_ids = ids_from(bodies.get("/api/tagpricedata/griddata"))
    booking_ids = []  # kun hvis offentlige data afslører dem - forventes ikke

    # 3) Parameteriserede paths
    print("== Parameteriserede ==")
    act3 = list(dict.fromkeys([s["activityId"] for s in fut] + activity_ids))[:MAX_IDS_PER_PATH]
    # foretræk events med bookinger til booking-relaterede kald
    bev3 = (booked_ev + ev_pairs)[:MAX_IDS_PER_PATH]
    ev3 = ev_pairs[:MAX_IDS_PER_PATH]
    ent3 = ev_entities[:MAX_IDS_PER_PATH]
    tag3 = ([SIGNUP_TAG] if SIGNUP_TAG in tag_ids_all else []) + [t for t in tag_ids_all if t != SIGNUP_TAG]
    tag3 = tag3[:MAX_IDS_PER_PATH]
    win_q = {"fromTime": NEAR_FROM, "toTime": NEAR_TO}

    plan = {
        "/api/activity/{id}": [({"id": a}, {}) for a in act3],
        "/api/activitydata/resource/{id}": [({"id": a}, {}) for a in act3],
        "/api/activity/{ActivityId}/event": [({"ActivityId": a}, {"filter.pageSize": 50}) for a in act3],
        "/api/activity/{activityId}/price": [({"activityId": a}, {}) for a in act3],
        "/api/activity/{activityId}/attendance": [({"activityId": a}, {}) for a in act3],
        "/api/booking/booked-resources/{activityId}": [({"activityId": a}, win_q) for a in act3],
        "/api/booking/grid/{activityId}": [({"activityId": a}, {"filter.fromDate": NEAR_FROM, "filter.days": 7}) for a in act3],
        "/api/booking/calendar/{activityId}": [({"activityId": a}, {}) for a in act3],
        "/api/booking/partners/{activityId}": [({"activityId": a}, {}) for a in act3],
        "/api/booking/griddata/{activityId}": [({"activityId": a}, {"sidx": "", "sord": "asc", "page": 1, "rows": 1,
                                                                      "daysToShow": 7, "customFilter": ""}) for a in act3],
        "/api/activity/{activityId}/event/{id}": [({"activityId": a, "id": e}, {"isAnonymous": "true"}) for a, e in ev3],
        "/api/activity/{activityId}/event/{id}/myprice": [({"activityId": a, "id": e}, {"isGuest": "true"}) for a, e in ev3],
        "/api/activity/{activityId}/event/{eventId}/price": [({"activityId": a, "eventId": e}, {}) for a, e in ev3],
        "/api/activity/{activityId}/event/{eventId}/bookings": [({"activityId": a, "eventId": e}, {"filter.pageSize": 1}) for a, e in bev3],
        "/api/activity/{activityId}/event/{eventId}/locked": [({"activityId": a, "eventId": e}, {}) for a, e in bev3],
        "/api/event/{id}": [({"id": x}, {}) for x in ent3],
        "/api/event/v3/{eventId}": [({"eventId": x}, {}) for x in ent3],
        "/api/tag/{id}": [({"id": t}, {}) for t in tag3],
        "/api/pricedata/tag/{id}": [({"id": t}, {}) for t in tag3],
        "/api/tagdata/members/{id}": [({"id": t}, {}) for t in tag3],
        "/api/signup/{id}": [({"id": SIGNUP_TAG}, {})],
        "/api/signup/GetOrderForMember/{exclusive}": [({"exclusive": "false"}, {})],
        "/api/pricedata/product/{id}": [({"id": x}, {}) for x in product_ids[:MAX_IDS_PER_PATH]],
        "/api/tagpricedata/{id}": [({"id": x}, {}) for x in tagprice_ids[:MAX_IDS_PER_PATH]],
        "/api/tagcategorydata/{id}": [({"id": c}, {}) for c in cat_ids[:MAX_IDS_PER_PATH]],
        "/api/tagcategorydata/wizard/{id}": [({"id": c}, {}) for c in cat_ids[:MAX_IDS_PER_PATH]],
        "/api/tagdata/tagcategory/griddata/{id}": [({"id": c}, GRID_Q) for c in cat_ids[:MAX_IDS_PER_PATH]],
        "/api/tagdata/category/{tagCategoryId}": [({"tagCategoryId": c}, {}) for c in cat_ids[:MAX_IDS_PER_PATH]],
        "/api/booking/{id}": [({"id": b}, {}) for b in booking_ids[:MAX_IDS_PER_PATH]],
    }
    no_source = {
        "/api/activity/{activityId}/member/{memberId}": "skipped – kræver memberId (persondata; ingen id fra offentlige data, gættes ikke)",
        "/api/activity/{activityId}/event/{eventId}/bookings/{id}": "skipped – intet booking-id i offentlige data",
        "/api/booking/{id}": "skipped – intet booking-id i offentlige data",
        "/api/activitydata/griddata/{id}": "skipped – unsure hvilken id-type {id} er",
        "/api/activitydata/event/{xmlForm}/{id}": "skipped – xmlForm-værdi ukendt",
        "/api/pricedata/activity/{actType}/{id}": "skipped – actType-værdi ukendt",
        "/api/tagdata/{type}/{id}": "skipped – type-værdi ukendt",
        "/api/tagdata/category/{tagCategoryId}/{id}": "skipped – unsure om {id} er tag-id; ikke afprøvet",
    }
    for e in entries:
        p = e["path"]
        if e["skip_reason"] or "{" not in p:
            continue
        calls = plan.get(p) or []
        if not calls:
            e["skip_reason"] = no_source.get(p, "skipped – ingen id fra offentlige data")
            continue
        for i, (pp, q) in enumerate(calls[:MAX_IDS_PER_PATH]):
            run(p, pp, q, save_as=slug(p, pp) + ".json")

    # 4) Medlems-tælling - ét kald hver, kun status/nøgler/tal/feltnavne
    print("== Medlems-probe ==")
    member_probe = []
    for p, q in MEMBER_PROBES:
        rec, body = pr.get(p, None, q)
        member_probe.append({
            "path": p, "query": q, "status": rec["status"], "kind": rec["kind"],
            "content_type": rec["content_type"],
            "top_level_keys": sorted(body.keys()) if isinstance(body, dict) and rec["kind"] == "object" else [],
            "count_fields": count_fields(body) if rec["status"] == 200 else {},
            "row_field_names": row_fields(body) if rec["status"] == 200 else [],
            "error": rec["error"],
        })
        del body  # ingen værdier gemmes

    # 5) Katalog
    for e in entries:
        calls = results.get(e["path"], [])
        e["called"] = bool(calls)
        if calls:
            ok = [c for c in calls if c["status"] == 200]
            best = ok[0] if ok else calls[0]
            e["status"] = best["status"]
            e["statuses"] = [c["status"] for c in calls]
            e["kind"] = best["kind"]
            e["item_count"] = best["item_count"]
            e["fields"] = best["fields"]
            e["error"] = best["error"][:200]
            e["personal_reduced_to_counts"] = e["path"] in PERSONAL_PATHS
            e["calls"] = [{"path_params": c["path_params"], "query": c["query"], "status": c["status"],
                           "kind": c["kind"], "item_count": c["item_count"], "error": c["error"][:120],
                           **({"structure": c["structure"]} if "structure" in c else {})}
                          for c in calls]
    status_counts = {}
    for c in pr.calls:
        status_counts[str(c["status"])] = status_counts.get(str(c["status"]), 0) + 1
    catalog = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "base_url": pr.client.base_url,
        "mode": "anonymous (ingen login, ingen Authorization-header)",
        "requests_made": pr.n,
        "status_counts": status_counts,
        "schedule_window": {"from": iso(WINDOW_FROM), "to": iso(WINDOW_TO), "chunks": schedule_meta,
                            "events_total": len(slots), "distinct_activities": len(activity_ids),
                            "distinct_tags": len(tag_ids)},
        "endpoints": entries,
        "member_probe": member_probe,
    }
    with open(OUT_CATALOG, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=1)
    print(f"Færdig: {pr.n} kald, statusfordeling {status_counts}")


if __name__ == "__main__":
    main()
