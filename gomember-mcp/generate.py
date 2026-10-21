#!/usr/bin/env python3
"""
Genererer server.py fra goMember/MemberLink swagger-filen.
Køres én gang (eller igen hvis swagger-filen opdateres). Rører kun GET-endpoints
inden for det aftalte scope (Activity, Event, Booking, Tag, TagCategory) -
POST/PUT/PATCH/DELETE bliver aldrig læst fra swagger-filen, så de kan ikke
havne i den genererede server ved en fejl.
"""
import json
import re
import sys

SWAGGER_PATH = sys.argv[1] if len(sys.argv) > 1 else "SGSwagger.json"
OUT_PATH = "server.py"

SCOPED_TAGS = {
    "ActivityApi", "ActivityDataApi", "ActivityEventDataApi",
    "EventApi", "EventNewApi",
    "BookingApi",
    "TagApi", "TagDataApi", "TagCategoryDataApi",
}

# GET-filteret ovenfor sikrer at vi kun bruger HTTP-verbet GET - det er ikke
# det samme som at kaldet er uden sideeffekter. Disse paths er GET i swagger,
# men navnet siger at de opretter eller ændrer data server-side. De holdes ude,
# fordi hele præmissen for denne integration er at den ikke kan skrive i
# goMember. Fjern aldrig et path herfra uden først at have bekræftet mod den
# faktiske server hvad kaldet rent faktisk gør.
DENIED_PATHS = {
    "/api/activitydata/batchupdate/{id}",
    "/api/activitydata/clone/{id}",
    "/api/tagcategorydata/clone/{id}",
    "/api/tagdata/clone/{id}",
}

# Håndkurateret navn + beskrivelse pr. path, så værktøjsnavnene giver mening
# for en model der skal vælge det rigtige værktøj. Kun GET-paths herfra bruges.
NAME_MAP = {
    "/api/activity/{id}": ("get_activity", "Hent én aktivitet ud fra dens ID."),
    "/api/activity": ("list_activities", "Hent liste over aktiviteter med filtrering (søgetekst, aktiv/inaktiv, etiketter, side/paginering)."),
    "/api/activitydata/griddata/{id}": ("get_activity_grid_data", "Hent gitter-/tabeldata for én aktivitet (samme data som admin-tabelvisningen bruger)."),
    "/api/activitydata/resource/{id}": ("get_activity_resource_form", "Hent ressourceopsætning for en aktivitet."),
    "/api/activitydata/event/{xmlForm}/{id}": ("get_activity_event_form", "Hent formular-data for et event under en aktivitet."),
    "/api/ActivityDataApi": ("get_activity_entity", "Hent rå entity-data for en aktivitet via partition/row key (lavniveau-opslag)."),
    "/api/activityeventdata/griddata": ("get_activity_event_grid_data", "Hent gitterdata for aktivitets-events."),
    "/api/ActivityEventDataApi": ("get_activity_event_entity", "Hent rå entity-data for et aktivitets-event via partition/row key."),
    "/api/booking/{id}": ("get_booking", "Hent én booking ud fra ID."),
    "/api/activity/{activityId}/event/{eventId}/bookings/{id}": ("get_booking_for_event", "Hent én specifik booking under et event."),
    "/api/booking/{id}/validatecancel": ("validate_booking_cancellation", "Tjek om en booking kan afbestilles ud fra reglerne (udfører ikke selve afbestillingen)."),
    "/api/booking/booked-resources/{activityId}": ("get_booked_resources", "Hent bookede ressourcer for en aktivitet i et givet tidsrum."),
    "/api/booking": ("list_bookings", "Hent liste over bookinger med filtrering (aktivitet, event, medlem, dato, etiketter mv.)."),
    "/api/activity/{activityId}/event/{eventId}/bookings": ("list_bookings_for_event", "Hent alle bookinger for et specifikt event."),
    "/api/activity/{activityId}/event/{eventId}/locked": ("get_locked_seats_for_event", "Hent låste/reserverede pladser for et event."),
    "/api/activity/{activityId}/attendance": ("get_attendance", "Hent fremmøde/deltagerregistrering for en aktivitet."),
    "/api/activity/{activityId}/member/{memberId}": ("get_attendance_for_member_day", "Hent fremmøde for ét specifikt medlem på en aktivitet."),
    "/api/booking/grid/{activityId}": ("get_booking_grid", "Hent booking-oversigt (gitter) for en aktivitet over et antal dage."),
    "/api/booking/calendar/{activityId}": ("get_booking_calendar", "Hent kalendervisning af bookinger for en aktivitet."),
    "/api/booking/partners/{activityId}": ("get_booking_partners", "Hent partnere/makkere tilknyttet bookinger for en aktivitet."),
    "/api/booking/griddata/{activityId}": ("get_booking_grid_data", "Hent rå gitterdata for bookinger på en aktivitet."),
    "/api/activity/event/days": ("list_event_days", "Hent liste over dage med events, med filtrering."),
    "/api/event/{id}": ("get_event", "Hent ét event ud fra ID."),
    "/api/activity/{activityId}/event/{id}": ("get_event_for_activity", "Hent et specifikt event under en aktivitet."),
    "/api/event": ("list_events", "Hent liste over events med filtrering."),
    "/api/activity/{activityId}/event/{id}/myprice": ("get_event_price", "Hent pris for et event, evt. for et specifikt medlem/gæst."),
    "/api/event/relevant": ("list_relevant_events_for_member", "Hent events der er relevante ud fra filtrering (bruges typisk til medlemsvisning)."),
    "/api/activity/event/list": ("list_activity_events", "Hent samlet liste over aktivitets-events."),
    "/api/activity/event/groups": ("list_activity_type_events", "Hent events grupperet efter aktivitetstype."),
    "/api/activity/{ActivityId}/event": ("list_events_for_activity", "Hent alle events for en given aktivitet - god til holdets skema."),
    "/api/event/v3/{eventId}": ("get_event_details_v3", "Hent detaljerede eventoplysninger (nyere v3-endpoint)."),
    "/api/event/v3/calendar": ("get_events_for_calendar_v3", "Hent events til kalendervisning (nyere v3-endpoint) - god til et samlet aktivitetsskema på hjemmesiden."),
    "/api/tag/{id}": ("get_tag", "Hent ét hold/etikette (tag) ud fra ID."),
    "/api/tag": ("list_tags", "Hent liste over hold/etiketter (tags) med filtrering."),
    "/api/tagcategorydata/griddata": ("get_tag_category_grid_data", "Hent gitterdata for holdkategorier."),
    "/api/tagcategorydata/wizard": ("get_tag_category_wizard_list", "Hent liste over holdkategori-guider (wizard-opsætning)."),
    "/api/tagcategorydata/wizard/{id}": ("get_tag_category_wizard", "Hent en specifik holdkategori-guide."),
    "/api/tagcategorydata/{id}": ("get_tag_category_form", "Hent formular-data for en holdkategori."),
    "/api/TagCategoryDataApi": ("get_tag_category_entity", "Hent rå entity-data for en holdkategori via partition/row key."),
    "/api/tagdata/griddata": ("get_tag_grid_data", "Hent gitterdata for hold/etiketter."),
    "/api/tagdata/tagcategory/griddata/{id}": ("get_tags_in_category_grid_data", "Hent hold under en given holdkategori (gitterdata)."),
    "/api/tagdata/members/{id}": ("get_tag_member_form", "Hent medlemstilknytnings-opsætning for et hold."),
    "/api/tagdata/autoassign/{departmentId}/{id}": ("get_tag_autoassign", "Hent autotildelings-opsætning for et hold."),
    "/api/tagdata/reorder/{category}/{id}": ("get_tag_reorder", "Hent sorteringsdata for hold i en kategori."),
    "/api/tagdata/category/{tagCategoryId}": ("get_tags_in_category", "Hent hold under en holdkategori."),
    "/api/tagdata/category/{tagCategoryId}/{id}": ("get_tag_form_in_category", "Hent formular-data for et specifikt hold i en kategori."),
    "/api/tagdata/membershipcard": ("get_tag_role_data", "Hent rolledata for medlemskort/hold."),
    "/api/tagdata/{type}/{id}": ("get_tag_form", "Hent formular-data for et hold ud fra type og ID."),
    "/api/TagDataApi": ("get_tag_entity", "Hent rå entity-data for et hold via partition/row key."),
}

TYPE_MAP = {
    "string": "str",
    "integer": "int",
    "boolean": "bool",
    "number": "float",
}


def py_type(param):
    t = TYPE_MAP.get(param.get("type"), "str")
    return t


def py_arg_name(swagger_name):
    # "filter.activityId" -> "filter_activity_id", "ActivityId" -> "activity_id"
    n = swagger_name.replace(".", "_")
    n = re.sub(r'(?<!^)(?=[A-Z])', '_', n).lower()
    n = re.sub(r'_+', '_', n).strip('_')
    if n in ("id", "type"):
        n = n + "_"  # undgå at skygge Python-builtins
    if re.match(r'^\d', n):
        n = "_" + n
    return n


def build_ops():
    with open(SWAGGER_PATH, encoding="utf-8") as f:
        spec = json.load(f)
    paths = spec["paths"]
    ops = []
    for path, path_item in paths.items():
        get_op = path_item.get("get")
        if get_op is None:
            continue
        tags = set(get_op.get("tags", []))
        if not (tags & SCOPED_TAGS):
            continue
        if path in DENIED_PATHS:
            continue
        if path not in NAME_MAP:
            raise SystemExit(f"Mangler navn til path: {path} (tilføj til NAME_MAP)")
        func_name, description = NAME_MAP[path]
        params = get_op.get("parameters", [])
        ops.append({
            "path": path,
            "func_name": func_name,
            "description": description,
            "params": params,
            "operation_id": get_op.get("operationId"),
        })
    return ops, spec


def render_tool(op):
    path = op["path"]
    func_name = op["func_name"]
    description = op["description"]
    params = op["params"]

    path_params = [p for p in params if p["in"] == "path"]
    query_params = [p for p in params if p["in"] == "query"]

    # path-params er altid required; sortér dem foran de optionelle query-params
    args = []
    swagger_to_py = {}
    for p in path_params:
        py_name = py_arg_name(p["name"])
        swagger_to_py[p["name"]] = (py_name, "path")
        args.append(f'{py_name}: {py_type(p)}')

    required_query = [p for p in query_params if p.get("required")]
    optional_query = [p for p in query_params if not p.get("required")]

    for p in required_query:
        py_name = py_arg_name(p["name"])
        swagger_to_py[p["name"]] = (py_name, "query")
        args.append(f'{py_name}: {py_type(p)}')

    for p in optional_query:
        py_name = py_arg_name(p["name"])
        swagger_to_py[p["name"]] = (py_name, "query")
        args.append(f'{py_name}: Optional[{py_type(p)}] = None')

    sig_args = ", ".join(args) if args else ""

    # path-format-streng: {activityId} -> {activity_id_val} osv, med rigtige swagger-navne bevaret til .format()
    format_path = path
    path_fmt_kwargs = []
    for p in path_params:
        py_name, _ = swagger_to_py[p["name"]]
        format_path = format_path.replace("{" + p["name"] + "}", "{" + p["name"] + "}")
        path_fmt_kwargs.append(f'"{p["name"]}": {py_name}')

    query_build_lines = []
    for p in query_params:
        py_name, _ = swagger_to_py[p["name"]]
        query_build_lines.append(f'    if {py_name} is not None:\n        query["{p["name"]}"] = {py_name}')

    doc_param_lines = []
    for p in path_params + query_params:
        py_name, kind = swagger_to_py[p["name"]]
        req = "påkrævet" if p.get("required") else "valgfri"
        pdesc = p.get("description") or ""
        doc_param_lines.append(f"        {py_name} ({kind}, {req}): {pdesc}".rstrip())

    doc_params_block = "\n".join(doc_param_lines)
    query_block = "\n".join(query_build_lines) if query_build_lines else "    pass"

    tool_src = f'''
@mcp.tool()
def {func_name}({sig_args}) -> dict:
    """{description}

    Kilde: GET {path}
    Args:
{doc_params_block if doc_params_block else "        (ingen parametre)"}
    """
    query: dict = {{}}
{query_block}
    path_params = {{{", ".join(path_fmt_kwargs)}}}
    return client.get("{format_path}", path_params=path_params, query_params=query)
'''
    return tool_src


def main():
    ops, spec = build_ops()
    ops.sort(key=lambda o: o["func_name"])

    tool_blocks = "\n".join(render_tool(op) for op in ops)

    header = f'''"""
goMember / MemberLink read-only MCP-server til Strong Gym.

AUTO-GENERERET af generate.py ud fra swagger-filen ({spec["info"]["title"]} {spec["info"]["version"]}).
Rediger ikke denne fil direkte - ret i generate.py og kør den igen, ellers
forsvinder dine rettelser næste gang filen genereres.

Serveren definerer udelukkende {len(ops)} GET-værktøjer, afgrænset til:
{", ".join(sorted(SCOPED_TAGS))}.
Der er bevidst IKKE implementeret nogen POST/PUT/PATCH/DELETE noget sted i
gomember_client.py eller denne fil - de metoder findes ikke i klienten, så
der er ingen kodevej til at skrive eller slette data i goMember herfra.

Derudover er {len(DENIED_PATHS)} GET-paths holdt ude via DENIED_PATHS i generate.py, fordi
de trods GET-verbet ser ud til at ændre data server-side (clone/batchupdate).
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from gomember_client import GoMemberClient

mcp = FastMCP("gomember-readonly")
client = GoMemberClient()

'''

    footer = '''

if __name__ == "__main__":
    mcp.run()
'''

    # eksplicit utf-8: uden den skriver Python på Windows i cp1252, og så kan
    # den genererede fil ikke importeres pga. de danske tegn i docstrings
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(header + tool_blocks + footer)

    print(f"Skrev {OUT_PATH} med {len(ops)} read-only værktøjer.")


if __name__ == "__main__":
    main()
