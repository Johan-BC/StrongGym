"""
goMember / MemberLink read-only MCP-server til Strong Gym.

AUTO-GENERERET af generate.py ud fra swagger-filen (MemberLink v1).
Rediger ikke denne fil direkte - ret i generate.py og kør den igen, ellers
forsvinder dine rettelser næste gang filen genereres.

Serveren definerer udelukkende 49 GET-værktøjer, afgrænset til:
ActivityApi, ActivityDataApi, ActivityEventDataApi, BookingApi, EventApi, EventNewApi, TagApi, TagCategoryDataApi, TagDataApi.
Der er bevidst IKKE implementeret nogen POST/PUT/PATCH/DELETE noget sted i
gomember_client.py eller denne fil - de metoder findes ikke i klienten, så
der er ingen kodevej til at skrive eller slette data i goMember herfra.

Derudover er 4 GET-paths holdt ude via DENIED_PATHS i generate.py, fordi
de trods GET-verbet ser ud til at ændre data server-side (clone/batchupdate).
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from gomember_client import GoMemberClient

mcp = FastMCP("gomember-readonly")
client = GoMemberClient()


@mcp.tool()
def get_activity(id_: str) -> dict:
    """Hent én aktivitet ud fra dens ID.

    Kilde: GET /api/activity/{id}
    Args:
        id_ (path, påkrævet): The id.
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/activity/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_entity(partition_key: str, row_key: str, fields: str) -> dict:
    """Hent rå entity-data for en aktivitet via partition/row key (lavniveau-opslag).

    Kilde: GET /api/ActivityDataApi
    Args:
        partition_key (query, påkrævet):
        row_key (query, påkrævet):
        fields (query, påkrævet):
    """
    query: dict = {}
    if partition_key is not None:
        query["partitionKey"] = partition_key
    if row_key is not None:
        query["rowKey"] = row_key
    if fields is not None:
        query["fields"] = fields
    path_params = {}
    return client.get("/api/ActivityDataApi", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_event_entity(partition_key: str, row_key: str, fields: str) -> dict:
    """Hent rå entity-data for et aktivitets-event via partition/row key.

    Kilde: GET /api/ActivityEventDataApi
    Args:
        partition_key (query, påkrævet):
        row_key (query, påkrævet):
        fields (query, påkrævet):
    """
    query: dict = {}
    if partition_key is not None:
        query["partitionKey"] = partition_key
    if row_key is not None:
        query["rowKey"] = row_key
    if fields is not None:
        query["fields"] = fields
    path_params = {}
    return client.get("/api/ActivityEventDataApi", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_event_form(xml_form: str, id_: str, department_id: Optional[str] = None) -> dict:
    """Hent formular-data for et event under en aktivitet.

    Kilde: GET /api/activitydata/event/{xmlForm}/{id}
    Args:
        xml_form (path, påkrævet):
        id_ (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"xmlForm": xml_form, "id": id_}
    return client.get("/api/activitydata/event/{xmlForm}/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_event_grid_data(sidx: str, sord: str, page: int, rows: int, search_text: str, tag_filter: str, not_tag_filter: str, department_filter: str, custom_filter: str) -> dict:
    """Hent gitterdata for aktivitets-events.

    Kilde: GET /api/activityeventdata/griddata
    Args:
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        search_text (query, påkrævet):
        tag_filter (query, påkrævet):
        not_tag_filter (query, påkrævet):
        department_filter (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if search_text is not None:
        query["searchText"] = search_text
    if tag_filter is not None:
        query["tagFilter"] = tag_filter
    if not_tag_filter is not None:
        query["notTagFilter"] = not_tag_filter
    if department_filter is not None:
        query["departmentFilter"] = department_filter
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {}
    return client.get("/api/activityeventdata/griddata", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_grid_data(id_: str, sidx: str, sord: str, page: int, rows: int, search_text: str, tag_filter: str, not_tag_filter: str, department_filter: str, custom_filter: str) -> dict:
    """Hent gitter-/tabeldata for én aktivitet (samme data som admin-tabelvisningen bruger).

    Kilde: GET /api/activitydata/griddata/{id}
    Args:
        id_ (path, påkrævet):
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        search_text (query, påkrævet):
        tag_filter (query, påkrævet):
        not_tag_filter (query, påkrævet):
        department_filter (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if search_text is not None:
        query["searchText"] = search_text
    if tag_filter is not None:
        query["tagFilter"] = tag_filter
    if not_tag_filter is not None:
        query["notTagFilter"] = not_tag_filter
    if department_filter is not None:
        query["departmentFilter"] = department_filter
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {"id": id_}
    return client.get("/api/activitydata/griddata/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_activity_resource_form(id_: str, department_id: Optional[str] = None) -> dict:
    """Hent ressourceopsætning for en aktivitet.

    Kilde: GET /api/activitydata/resource/{id}
    Args:
        id_ (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"id": id_}
    return client.get("/api/activitydata/resource/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_attendance(activity_id: str, filter_register_date: Optional[str] = None, filter_to_date: Optional[str] = None, filter_admin_member_id: Optional[str] = None) -> dict:
    """Hent fremmøde/deltagerregistrering for en aktivitet.

    Kilde: GET /api/activity/{activityId}/attendance
    Args:
        activity_id (path, påkrævet):
        filter_register_date (query, valgfri):
        filter_to_date (query, valgfri):
        filter_admin_member_id (query, valgfri):
    """
    query: dict = {}
    if filter_register_date is not None:
        query["filter.registerDate"] = filter_register_date
    if filter_to_date is not None:
        query["filter.toDate"] = filter_to_date
    if filter_admin_member_id is not None:
        query["filter.adminMemberId"] = filter_admin_member_id
    path_params = {"activityId": activity_id}
    return client.get("/api/activity/{activityId}/attendance", path_params=path_params, query_params=query)


@mcp.tool()
def get_attendance_for_member_day(activity_id: str, member_id: str, filter_register_date: Optional[str] = None, filter_to_date: Optional[str] = None, filter_admin_member_id: Optional[str] = None) -> dict:
    """Hent fremmøde for ét specifikt medlem på en aktivitet.

    Kilde: GET /api/activity/{activityId}/member/{memberId}
    Args:
        activity_id (path, påkrævet):
        member_id (path, påkrævet):
        filter_register_date (query, valgfri):
        filter_to_date (query, valgfri):
        filter_admin_member_id (query, valgfri):
    """
    query: dict = {}
    if filter_register_date is not None:
        query["filter.registerDate"] = filter_register_date
    if filter_to_date is not None:
        query["filter.toDate"] = filter_to_date
    if filter_admin_member_id is not None:
        query["filter.adminMemberId"] = filter_admin_member_id
    path_params = {"activityId": activity_id, "memberId": member_id}
    return client.get("/api/activity/{activityId}/member/{memberId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booked_resources(activity_id: str, from_time: str, to_time: str) -> dict:
    """Hent bookede ressourcer for en aktivitet i et givet tidsrum.

    Kilde: GET /api/booking/booked-resources/{activityId}
    Args:
        activity_id (path, påkrævet):
        from_time (query, påkrævet):
        to_time (query, påkrævet):
    """
    query: dict = {}
    if from_time is not None:
        query["fromTime"] = from_time
    if to_time is not None:
        query["toTime"] = to_time
    path_params = {"activityId": activity_id}
    return client.get("/api/booking/booked-resources/{activityId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking(id_: str) -> dict:
    """Hent én booking ud fra ID.

    Kilde: GET /api/booking/{id}
    Args:
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/booking/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking_calendar(activity_id: str) -> dict:
    """Hent kalendervisning af bookinger for en aktivitet.

    Kilde: GET /api/booking/calendar/{activityId}
    Args:
        activity_id (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"activityId": activity_id}
    return client.get("/api/booking/calendar/{activityId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking_for_event(id_: str, activity_id: str, event_id: str) -> dict:
    """Hent én specifik booking under et event.

    Kilde: GET /api/activity/{activityId}/event/{eventId}/bookings/{id}
    Args:
        id_ (path, påkrævet): The id.
        activity_id (path, påkrævet): The activity id.
        event_id (path, påkrævet): The event id.
    """
    query: dict = {}
    pass
    path_params = {"id": id_, "activityId": activity_id, "eventId": event_id}
    return client.get("/api/activity/{activityId}/event/{eventId}/bookings/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking_grid(activity_id: str, filter_from_date: Optional[str] = None, filter_days: Optional[int] = None, filter_activity_id: Optional[str] = None) -> dict:
    """Hent booking-oversigt (gitter) for en aktivitet over et antal dage.

    Kilde: GET /api/booking/grid/{activityId}
    Args:
        activity_id (path, påkrævet): The activity id.
        filter_from_date (query, valgfri):
        filter_days (query, valgfri):
        filter_activity_id (query, valgfri):
    """
    query: dict = {}
    if filter_from_date is not None:
        query["filter.fromDate"] = filter_from_date
    if filter_days is not None:
        query["filter.days"] = filter_days
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    path_params = {"activityId": activity_id}
    return client.get("/api/booking/grid/{activityId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking_grid_data(activity_id: str, sidx: str, sord: str, page: int, rows: int, days_to_show: int, custom_filter: str) -> dict:
    """Hent rå gitterdata for bookinger på en aktivitet.

    Kilde: GET /api/booking/griddata/{activityId}
    Args:
        activity_id (path, påkrævet):
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        days_to_show (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if days_to_show is not None:
        query["daysToShow"] = days_to_show
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {"activityId": activity_id}
    return client.get("/api/booking/griddata/{activityId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_booking_partners(activity_id: str) -> dict:
    """Hent partnere/makkere tilknyttet bookinger for en aktivitet.

    Kilde: GET /api/booking/partners/{activityId}
    Args:
        activity_id (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"activityId": activity_id}
    return client.get("/api/booking/partners/{activityId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_event(id_: str) -> dict:
    """Hent ét event ud fra ID.

    Kilde: GET /api/event/{id}
    Args:
        id_ (path, påkrævet): The id.
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/event/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_event_details_v3(event_id: str) -> dict:
    """Hent detaljerede eventoplysninger (nyere v3-endpoint).

    Kilde: GET /api/event/v3/{eventId}
    Args:
        event_id (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"eventId": event_id}
    return client.get("/api/event/v3/{eventId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_event_for_activity(activity_id: str, id_: str, is_anonymous: Optional[bool] = None) -> dict:
    """Hent et specifikt event under en aktivitet.

    Kilde: GET /api/activity/{activityId}/event/{id}
    Args:
        activity_id (path, påkrævet):
        id_ (path, påkrævet):
        is_anonymous (query, valgfri):
    """
    query: dict = {}
    if is_anonymous is not None:
        query["isAnonymous"] = is_anonymous
    path_params = {"activityId": activity_id, "id": id_}
    return client.get("/api/activity/{activityId}/event/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_event_price(activity_id: str, id_: str, member_id: Optional[str] = None, is_guest: Optional[bool] = None) -> dict:
    """Hent pris for et event, evt. for et specifikt medlem/gæst.

    Kilde: GET /api/activity/{activityId}/event/{id}/myprice
    Args:
        activity_id (path, påkrævet):
        id_ (path, påkrævet):
        member_id (query, valgfri):
        is_guest (query, valgfri):
    """
    query: dict = {}
    if member_id is not None:
        query["memberId"] = member_id
    if is_guest is not None:
        query["isGuest"] = is_guest
    path_params = {"activityId": activity_id, "id": id_}
    return client.get("/api/activity/{activityId}/event/{id}/myprice", path_params=path_params, query_params=query)


@mcp.tool()
def get_events_for_calendar_v3(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_from_time: Optional[str] = None, filter_to_time: Optional[str] = None, filter_tag_id: Optional[str] = None, filter_events_to_show: Optional[int] = None, filter_hide_recurring: Optional[bool] = None, filter_app_mode: Optional[bool] = None, filter_admin: Optional[bool] = None, filter_hide_excess_events: Optional[bool] = None, filter_night_offset_hours: Optional[int] = None, filter_activities: Optional[str] = None, filter_event_types: Optional[str] = None, filter_event_ids: Optional[str] = None, filter_activity_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_parent_id: Optional[str] = None, filter_show_deleted: Optional[bool] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent events til kalendervisning (nyere v3-endpoint) - god til et samlet aktivitetsskema på hjemmesiden.

    Kilde: GET /api/event/v3/calendar
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_from_time (query, valgfri):
        filter_to_time (query, valgfri):
        filter_tag_id (query, valgfri):
        filter_events_to_show (query, valgfri):
        filter_hide_recurring (query, valgfri):
        filter_app_mode (query, valgfri):
        filter_admin (query, valgfri):
        filter_hide_excess_events (query, valgfri):
        filter_night_offset_hours (query, valgfri):
        filter_activities (query, valgfri):
        filter_event_types (query, valgfri):
        filter_event_ids (query, valgfri):
        filter_activity_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_parent_id (query, valgfri):
        filter_show_deleted (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_from_time is not None:
        query["filter.fromTime"] = filter_from_time
    if filter_to_time is not None:
        query["filter.toTime"] = filter_to_time
    if filter_tag_id is not None:
        query["filter.tagId"] = filter_tag_id
    if filter_events_to_show is not None:
        query["filter.eventsToShow"] = filter_events_to_show
    if filter_hide_recurring is not None:
        query["filter.hideRecurring"] = filter_hide_recurring
    if filter_app_mode is not None:
        query["filter.appMode"] = filter_app_mode
    if filter_admin is not None:
        query["filter.admin"] = filter_admin
    if filter_hide_excess_events is not None:
        query["filter.hideExcessEvents"] = filter_hide_excess_events
    if filter_night_offset_hours is not None:
        query["filter.nightOffsetHours"] = filter_night_offset_hours
    if filter_activities is not None:
        query["filter.activities"] = filter_activities
    if filter_event_types is not None:
        query["filter.eventTypes"] = filter_event_types
    if filter_event_ids is not None:
        query["filter.eventIds"] = filter_event_ids
    if filter_activity_ids is not None:
        query["filter.activityIds"] = filter_activity_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_parent_id is not None:
        query["filter.parentId"] = filter_parent_id
    if filter_show_deleted is not None:
        query["filter.showDeleted"] = filter_show_deleted
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/event/v3/calendar", path_params=path_params, query_params=query)


@mcp.tool()
def get_locked_seats_for_event(activity_id: str, event_id: str) -> dict:
    """Hent låste/reserverede pladser for et event.

    Kilde: GET /api/activity/{activityId}/event/{eventId}/locked
    Args:
        activity_id (path, påkrævet):
        event_id (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"activityId": activity_id, "eventId": event_id}
    return client.get("/api/activity/{activityId}/event/{eventId}/locked", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag(id_: str) -> dict:
    """Hent ét hold/etikette (tag) ud fra ID.

    Kilde: GET /api/tag/{id}
    Args:
        id_ (path, påkrævet): The id.
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/tag/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_autoassign(department_id: str, id_: str) -> dict:
    """Hent autotildelings-opsætning for et hold.

    Kilde: GET /api/tagdata/autoassign/{departmentId}/{id}
    Args:
        department_id (path, påkrævet):
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"departmentId": department_id, "id": id_}
    return client.get("/api/tagdata/autoassign/{departmentId}/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_category_entity(partition_key: str, row_key: str, fields: str) -> dict:
    """Hent rå entity-data for en holdkategori via partition/row key.

    Kilde: GET /api/TagCategoryDataApi
    Args:
        partition_key (query, påkrævet):
        row_key (query, påkrævet):
        fields (query, påkrævet):
    """
    query: dict = {}
    if partition_key is not None:
        query["partitionKey"] = partition_key
    if row_key is not None:
        query["rowKey"] = row_key
    if fields is not None:
        query["fields"] = fields
    path_params = {}
    return client.get("/api/TagCategoryDataApi", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_category_form(id_: str) -> dict:
    """Hent formular-data for en holdkategori.

    Kilde: GET /api/tagcategorydata/{id}
    Args:
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/tagcategorydata/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_category_grid_data(sidx: str, sord: str, page: int, rows: int, search_text: str, tag_filter: str, not_tag_filter: str, department_filter: str, custom_filter: str) -> dict:
    """Hent gitterdata for holdkategorier.

    Kilde: GET /api/tagcategorydata/griddata
    Args:
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        search_text (query, påkrævet):
        tag_filter (query, påkrævet):
        not_tag_filter (query, påkrævet):
        department_filter (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if search_text is not None:
        query["searchText"] = search_text
    if tag_filter is not None:
        query["tagFilter"] = tag_filter
    if not_tag_filter is not None:
        query["notTagFilter"] = not_tag_filter
    if department_filter is not None:
        query["departmentFilter"] = department_filter
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {}
    return client.get("/api/tagcategorydata/griddata", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_category_wizard(id_: str) -> dict:
    """Hent en specifik holdkategori-guide.

    Kilde: GET /api/tagcategorydata/wizard/{id}
    Args:
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/tagcategorydata/wizard/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_category_wizard_list() -> dict:
    """Hent liste over holdkategori-guider (wizard-opsætning).

    Kilde: GET /api/tagcategorydata/wizard
    Args:
        (ingen parametre)
    """
    query: dict = {}
    pass
    path_params = {}
    return client.get("/api/tagcategorydata/wizard", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_entity(partition_key: str, row_key: str, fields: str) -> dict:
    """Hent rå entity-data for et hold via partition/row key.

    Kilde: GET /api/TagDataApi
    Args:
        partition_key (query, påkrævet):
        row_key (query, påkrævet):
        fields (query, påkrævet):
    """
    query: dict = {}
    if partition_key is not None:
        query["partitionKey"] = partition_key
    if row_key is not None:
        query["rowKey"] = row_key
    if fields is not None:
        query["fields"] = fields
    path_params = {}
    return client.get("/api/TagDataApi", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_form(type_: str, id_: str, department_id: Optional[str] = None) -> dict:
    """Hent formular-data for et hold ud fra type og ID.

    Kilde: GET /api/tagdata/{type}/{id}
    Args:
        type_ (path, påkrævet):
        id_ (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"type": type_, "id": id_}
    return client.get("/api/tagdata/{type}/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_form_in_category(tag_category_id: str, id_: str, department_id: Optional[str] = None) -> dict:
    """Hent formular-data for et specifikt hold i en kategori.

    Kilde: GET /api/tagdata/category/{tagCategoryId}/{id}
    Args:
        tag_category_id (path, påkrævet):
        id_ (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"tagCategoryId": tag_category_id, "id": id_}
    return client.get("/api/tagdata/category/{tagCategoryId}/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_grid_data(sidx: str, sord: str, page: int, rows: int, search_text: str, tag_filter: str, not_tag_filter: str, department_filter: str, custom_filter: str) -> dict:
    """Hent gitterdata for hold/etiketter.

    Kilde: GET /api/tagdata/griddata
    Args:
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        search_text (query, påkrævet):
        tag_filter (query, påkrævet):
        not_tag_filter (query, påkrævet):
        department_filter (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if search_text is not None:
        query["searchText"] = search_text
    if tag_filter is not None:
        query["tagFilter"] = tag_filter
    if not_tag_filter is not None:
        query["notTagFilter"] = not_tag_filter
    if department_filter is not None:
        query["departmentFilter"] = department_filter
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {}
    return client.get("/api/tagdata/griddata", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_member_form(id_: str, department_id: Optional[str] = None) -> dict:
    """Hent medlemstilknytnings-opsætning for et hold.

    Kilde: GET /api/tagdata/members/{id}
    Args:
        id_ (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"id": id_}
    return client.get("/api/tagdata/members/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_reorder(category: str, id_: str) -> dict:
    """Hent sorteringsdata for hold i en kategori.

    Kilde: GET /api/tagdata/reorder/{category}/{id}
    Args:
        category (path, påkrævet):
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"category": category, "id": id_}
    return client.get("/api/tagdata/reorder/{category}/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tag_role_data() -> dict:
    """Hent rolledata for medlemskort/hold.

    Kilde: GET /api/tagdata/membershipcard
    Args:
        (ingen parametre)
    """
    query: dict = {}
    pass
    path_params = {}
    return client.get("/api/tagdata/membershipcard", path_params=path_params, query_params=query)


@mcp.tool()
def get_tags_in_category(tag_category_id: str, department_id: Optional[str] = None) -> dict:
    """Hent hold under en holdkategori.

    Kilde: GET /api/tagdata/category/{tagCategoryId}
    Args:
        tag_category_id (path, påkrævet):
        department_id (query, valgfri):
    """
    query: dict = {}
    if department_id is not None:
        query["departmentId"] = department_id
    path_params = {"tagCategoryId": tag_category_id}
    return client.get("/api/tagdata/category/{tagCategoryId}", path_params=path_params, query_params=query)


@mcp.tool()
def get_tags_in_category_grid_data(id_: str, sidx: str, sord: str, page: int, rows: int, search_text: str, tag_filter: str, not_tag_filter: str, department_filter: str, custom_filter: str) -> dict:
    """Hent hold under en given holdkategori (gitterdata).

    Kilde: GET /api/tagdata/tagcategory/griddata/{id}
    Args:
        id_ (path, påkrævet):
        sidx (query, påkrævet):
        sord (query, påkrævet):
        page (query, påkrævet):
        rows (query, påkrævet):
        search_text (query, påkrævet):
        tag_filter (query, påkrævet):
        not_tag_filter (query, påkrævet):
        department_filter (query, påkrævet):
        custom_filter (query, påkrævet):
    """
    query: dict = {}
    if sidx is not None:
        query["sidx"] = sidx
    if sord is not None:
        query["sord"] = sord
    if page is not None:
        query["page"] = page
    if rows is not None:
        query["rows"] = rows
    if search_text is not None:
        query["searchText"] = search_text
    if tag_filter is not None:
        query["tagFilter"] = tag_filter
    if not_tag_filter is not None:
        query["notTagFilter"] = not_tag_filter
    if department_filter is not None:
        query["departmentFilter"] = department_filter
    if custom_filter is not None:
        query["customFilter"] = custom_filter
    path_params = {"id": id_}
    return client.get("/api/tagdata/tagcategory/griddata/{id}", path_params=path_params, query_params=query)


@mcp.tool()
def list_activities(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_only_admin: Optional[bool] = None, filter_admin_and_autonomous: Optional[bool] = None, filter_only_groups: Optional[bool] = None, filter_only_autonomous: Optional[bool] = None, filter_activity_mode: Optional[int] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent liste over aktiviteter med filtrering (søgetekst, aktiv/inaktiv, etiketter, side/paginering).

    Kilde: GET /api/activity
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_only_admin (query, valgfri):
        filter_admin_and_autonomous (query, valgfri):
        filter_only_groups (query, valgfri):
        filter_only_autonomous (query, valgfri):
        filter_activity_mode (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_only_admin is not None:
        query["filter.onlyAdmin"] = filter_only_admin
    if filter_admin_and_autonomous is not None:
        query["filter.adminAndAutonomous"] = filter_admin_and_autonomous
    if filter_only_groups is not None:
        query["filter.onlyGroups"] = filter_only_groups
    if filter_only_autonomous is not None:
        query["filter.onlyAutonomous"] = filter_only_autonomous
    if filter_activity_mode is not None:
        query["filter.activityMode"] = filter_activity_mode
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/activity", path_params=path_params, query_params=query)


@mcp.tool()
def list_activity_events(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_from_time: Optional[str] = None, filter_to_time: Optional[str] = None, filter_tag_id: Optional[str] = None, filter_events_to_show: Optional[int] = None, filter_hide_recurring: Optional[bool] = None, filter_app_mode: Optional[bool] = None, filter_admin: Optional[bool] = None, filter_hide_excess_events: Optional[bool] = None, filter_night_offset_hours: Optional[int] = None, filter_activities: Optional[str] = None, filter_event_types: Optional[str] = None, filter_event_ids: Optional[str] = None, filter_activity_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_parent_id: Optional[str] = None, filter_show_deleted: Optional[bool] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent samlet liste over aktivitets-events.

    Kilde: GET /api/activity/event/list
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_from_time (query, valgfri):
        filter_to_time (query, valgfri):
        filter_tag_id (query, valgfri):
        filter_events_to_show (query, valgfri):
        filter_hide_recurring (query, valgfri):
        filter_app_mode (query, valgfri):
        filter_admin (query, valgfri):
        filter_hide_excess_events (query, valgfri):
        filter_night_offset_hours (query, valgfri):
        filter_activities (query, valgfri):
        filter_event_types (query, valgfri):
        filter_event_ids (query, valgfri):
        filter_activity_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_parent_id (query, valgfri):
        filter_show_deleted (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_from_time is not None:
        query["filter.fromTime"] = filter_from_time
    if filter_to_time is not None:
        query["filter.toTime"] = filter_to_time
    if filter_tag_id is not None:
        query["filter.tagId"] = filter_tag_id
    if filter_events_to_show is not None:
        query["filter.eventsToShow"] = filter_events_to_show
    if filter_hide_recurring is not None:
        query["filter.hideRecurring"] = filter_hide_recurring
    if filter_app_mode is not None:
        query["filter.appMode"] = filter_app_mode
    if filter_admin is not None:
        query["filter.admin"] = filter_admin
    if filter_hide_excess_events is not None:
        query["filter.hideExcessEvents"] = filter_hide_excess_events
    if filter_night_offset_hours is not None:
        query["filter.nightOffsetHours"] = filter_night_offset_hours
    if filter_activities is not None:
        query["filter.activities"] = filter_activities
    if filter_event_types is not None:
        query["filter.eventTypes"] = filter_event_types
    if filter_event_ids is not None:
        query["filter.eventIds"] = filter_event_ids
    if filter_activity_ids is not None:
        query["filter.activityIds"] = filter_activity_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_parent_id is not None:
        query["filter.parentId"] = filter_parent_id
    if filter_show_deleted is not None:
        query["filter.showDeleted"] = filter_show_deleted
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/activity/event/list", path_params=path_params, query_params=query)


@mcp.tool()
def list_activity_type_events(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_from_time: Optional[str] = None, filter_to_time: Optional[str] = None, filter_tag_id: Optional[str] = None, filter_events_to_show: Optional[int] = None, filter_hide_recurring: Optional[bool] = None, filter_app_mode: Optional[bool] = None, filter_admin: Optional[bool] = None, filter_hide_excess_events: Optional[bool] = None, filter_night_offset_hours: Optional[int] = None, filter_activities: Optional[str] = None, filter_event_types: Optional[str] = None, filter_event_ids: Optional[str] = None, filter_activity_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_parent_id: Optional[str] = None, filter_show_deleted: Optional[bool] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent events grupperet efter aktivitetstype.

    Kilde: GET /api/activity/event/groups
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_from_time (query, valgfri):
        filter_to_time (query, valgfri):
        filter_tag_id (query, valgfri):
        filter_events_to_show (query, valgfri):
        filter_hide_recurring (query, valgfri):
        filter_app_mode (query, valgfri):
        filter_admin (query, valgfri):
        filter_hide_excess_events (query, valgfri):
        filter_night_offset_hours (query, valgfri):
        filter_activities (query, valgfri):
        filter_event_types (query, valgfri):
        filter_event_ids (query, valgfri):
        filter_activity_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_parent_id (query, valgfri):
        filter_show_deleted (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_from_time is not None:
        query["filter.fromTime"] = filter_from_time
    if filter_to_time is not None:
        query["filter.toTime"] = filter_to_time
    if filter_tag_id is not None:
        query["filter.tagId"] = filter_tag_id
    if filter_events_to_show is not None:
        query["filter.eventsToShow"] = filter_events_to_show
    if filter_hide_recurring is not None:
        query["filter.hideRecurring"] = filter_hide_recurring
    if filter_app_mode is not None:
        query["filter.appMode"] = filter_app_mode
    if filter_admin is not None:
        query["filter.admin"] = filter_admin
    if filter_hide_excess_events is not None:
        query["filter.hideExcessEvents"] = filter_hide_excess_events
    if filter_night_offset_hours is not None:
        query["filter.nightOffsetHours"] = filter_night_offset_hours
    if filter_activities is not None:
        query["filter.activities"] = filter_activities
    if filter_event_types is not None:
        query["filter.eventTypes"] = filter_event_types
    if filter_event_ids is not None:
        query["filter.eventIds"] = filter_event_ids
    if filter_activity_ids is not None:
        query["filter.activityIds"] = filter_activity_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_parent_id is not None:
        query["filter.parentId"] = filter_parent_id
    if filter_show_deleted is not None:
        query["filter.showDeleted"] = filter_show_deleted
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/activity/event/groups", path_params=path_params, query_params=query)


@mcp.tool()
def list_bookings(filter_activity_id: Optional[str] = None, filter_event_id: Optional[str] = None, filter_member_id: Optional[str] = None, filter_guest_email: Optional[str] = None, filter_guest_mobile: Optional[str] = None, filter_resource_bookings: Optional[bool] = None, filter_only_bundles: Optional[bool] = None, filter_show_date: Optional[str] = None, filter_from_date: Optional[str] = None, filter_to_date: Optional[str] = None, filter_resource_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent liste over bookinger med filtrering (aktivitet, event, medlem, dato, etiketter mv.).

    Kilde: GET /api/booking
    Args:
        filter_activity_id (query, valgfri):
        filter_event_id (query, valgfri):
        filter_member_id (query, valgfri):
        filter_guest_email (query, valgfri):
        filter_guest_mobile (query, valgfri):
        filter_resource_bookings (query, valgfri):
        filter_only_bundles (query, valgfri):
        filter_show_date (query, valgfri):
        filter_from_date (query, valgfri):
        filter_to_date (query, valgfri):
        filter_resource_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_event_id is not None:
        query["filter.eventId"] = filter_event_id
    if filter_member_id is not None:
        query["filter.memberId"] = filter_member_id
    if filter_guest_email is not None:
        query["filter.guestEmail"] = filter_guest_email
    if filter_guest_mobile is not None:
        query["filter.guestMobile"] = filter_guest_mobile
    if filter_resource_bookings is not None:
        query["filter.resourceBookings"] = filter_resource_bookings
    if filter_only_bundles is not None:
        query["filter.onlyBundles"] = filter_only_bundles
    if filter_show_date is not None:
        query["filter.showDate"] = filter_show_date
    if filter_from_date is not None:
        query["filter.fromDate"] = filter_from_date
    if filter_to_date is not None:
        query["filter.toDate"] = filter_to_date
    if filter_resource_ids is not None:
        query["filter.resourceIds"] = filter_resource_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/booking", path_params=path_params, query_params=query)


@mcp.tool()
def list_bookings_for_event(activity_id: str, event_id: str, filter_activity_id: Optional[str] = None, filter_event_id: Optional[str] = None, filter_member_id: Optional[str] = None, filter_guest_email: Optional[str] = None, filter_guest_mobile: Optional[str] = None, filter_resource_bookings: Optional[bool] = None, filter_only_bundles: Optional[bool] = None, filter_show_date: Optional[str] = None, filter_from_date: Optional[str] = None, filter_to_date: Optional[str] = None, filter_resource_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent alle bookinger for et specifikt event.

    Kilde: GET /api/activity/{activityId}/event/{eventId}/bookings
    Args:
        activity_id (path, påkrævet): The activity id.
        event_id (path, påkrævet): The event id.
        filter_activity_id (query, valgfri):
        filter_event_id (query, valgfri):
        filter_member_id (query, valgfri):
        filter_guest_email (query, valgfri):
        filter_guest_mobile (query, valgfri):
        filter_resource_bookings (query, valgfri):
        filter_only_bundles (query, valgfri):
        filter_show_date (query, valgfri):
        filter_from_date (query, valgfri):
        filter_to_date (query, valgfri):
        filter_resource_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_event_id is not None:
        query["filter.eventId"] = filter_event_id
    if filter_member_id is not None:
        query["filter.memberId"] = filter_member_id
    if filter_guest_email is not None:
        query["filter.guestEmail"] = filter_guest_email
    if filter_guest_mobile is not None:
        query["filter.guestMobile"] = filter_guest_mobile
    if filter_resource_bookings is not None:
        query["filter.resourceBookings"] = filter_resource_bookings
    if filter_only_bundles is not None:
        query["filter.onlyBundles"] = filter_only_bundles
    if filter_show_date is not None:
        query["filter.showDate"] = filter_show_date
    if filter_from_date is not None:
        query["filter.fromDate"] = filter_from_date
    if filter_to_date is not None:
        query["filter.toDate"] = filter_to_date
    if filter_resource_ids is not None:
        query["filter.resourceIds"] = filter_resource_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {"activityId": activity_id, "eventId": event_id}
    return client.get("/api/activity/{activityId}/event/{eventId}/bookings", path_params=path_params, query_params=query)


@mcp.tool()
def list_event_days(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_from_time: Optional[str] = None, filter_to_time: Optional[str] = None, filter_tag_id: Optional[str] = None, filter_events_to_show: Optional[int] = None, filter_hide_recurring: Optional[bool] = None, filter_app_mode: Optional[bool] = None, filter_admin: Optional[bool] = None, filter_hide_excess_events: Optional[bool] = None, filter_night_offset_hours: Optional[int] = None, filter_activities: Optional[str] = None, filter_event_types: Optional[str] = None, filter_event_ids: Optional[str] = None, filter_activity_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_parent_id: Optional[str] = None, filter_show_deleted: Optional[bool] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent liste over dage med events, med filtrering.

    Kilde: GET /api/activity/event/days
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_from_time (query, valgfri):
        filter_to_time (query, valgfri):
        filter_tag_id (query, valgfri):
        filter_events_to_show (query, valgfri):
        filter_hide_recurring (query, valgfri):
        filter_app_mode (query, valgfri):
        filter_admin (query, valgfri):
        filter_hide_excess_events (query, valgfri):
        filter_night_offset_hours (query, valgfri):
        filter_activities (query, valgfri):
        filter_event_types (query, valgfri):
        filter_event_ids (query, valgfri):
        filter_activity_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_parent_id (query, valgfri):
        filter_show_deleted (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_from_time is not None:
        query["filter.fromTime"] = filter_from_time
    if filter_to_time is not None:
        query["filter.toTime"] = filter_to_time
    if filter_tag_id is not None:
        query["filter.tagId"] = filter_tag_id
    if filter_events_to_show is not None:
        query["filter.eventsToShow"] = filter_events_to_show
    if filter_hide_recurring is not None:
        query["filter.hideRecurring"] = filter_hide_recurring
    if filter_app_mode is not None:
        query["filter.appMode"] = filter_app_mode
    if filter_admin is not None:
        query["filter.admin"] = filter_admin
    if filter_hide_excess_events is not None:
        query["filter.hideExcessEvents"] = filter_hide_excess_events
    if filter_night_offset_hours is not None:
        query["filter.nightOffsetHours"] = filter_night_offset_hours
    if filter_activities is not None:
        query["filter.activities"] = filter_activities
    if filter_event_types is not None:
        query["filter.eventTypes"] = filter_event_types
    if filter_event_ids is not None:
        query["filter.eventIds"] = filter_event_ids
    if filter_activity_ids is not None:
        query["filter.activityIds"] = filter_activity_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_parent_id is not None:
        query["filter.parentId"] = filter_parent_id
    if filter_show_deleted is not None:
        query["filter.showDeleted"] = filter_show_deleted
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/activity/event/days", path_params=path_params, query_params=query)


@mcp.tool()
def list_events(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_only_admin: Optional[bool] = None, filter_admin_and_autonomous: Optional[bool] = None, filter_only_groups: Optional[bool] = None, filter_only_autonomous: Optional[bool] = None, filter_activity_mode: Optional[int] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent liste over events med filtrering.

    Kilde: GET /api/event
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_only_admin (query, valgfri):
        filter_admin_and_autonomous (query, valgfri):
        filter_only_groups (query, valgfri):
        filter_only_autonomous (query, valgfri):
        filter_activity_mode (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_only_admin is not None:
        query["filter.onlyAdmin"] = filter_only_admin
    if filter_admin_and_autonomous is not None:
        query["filter.adminAndAutonomous"] = filter_admin_and_autonomous
    if filter_only_groups is not None:
        query["filter.onlyGroups"] = filter_only_groups
    if filter_only_autonomous is not None:
        query["filter.onlyAutonomous"] = filter_only_autonomous
    if filter_activity_mode is not None:
        query["filter.activityMode"] = filter_activity_mode
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/event", path_params=path_params, query_params=query)


@mcp.tool()
def list_events_for_activity(activity_id: str, filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_only_admin: Optional[bool] = None, filter_admin_and_autonomous: Optional[bool] = None, filter_only_groups: Optional[bool] = None, filter_only_autonomous: Optional[bool] = None, filter_activity_mode: Optional[int] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent alle events for en given aktivitet - god til holdets skema.

    Kilde: GET /api/activity/{ActivityId}/event
    Args:
        activity_id (path, påkrævet):
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_only_admin (query, valgfri):
        filter_admin_and_autonomous (query, valgfri):
        filter_only_groups (query, valgfri):
        filter_only_autonomous (query, valgfri):
        filter_activity_mode (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_only_admin is not None:
        query["filter.onlyAdmin"] = filter_only_admin
    if filter_admin_and_autonomous is not None:
        query["filter.adminAndAutonomous"] = filter_admin_and_autonomous
    if filter_only_groups is not None:
        query["filter.onlyGroups"] = filter_only_groups
    if filter_only_autonomous is not None:
        query["filter.onlyAutonomous"] = filter_only_autonomous
    if filter_activity_mode is not None:
        query["filter.activityMode"] = filter_activity_mode
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {"ActivityId": activity_id}
    return client.get("/api/activity/{ActivityId}/event", path_params=path_params, query_params=query)


@mcp.tool()
def list_relevant_events_for_member(filter_activity_id: Optional[str] = None, filter_from_offset: Optional[str] = None, filter_from_time: Optional[str] = None, filter_to_time: Optional[str] = None, filter_tag_id: Optional[str] = None, filter_events_to_show: Optional[int] = None, filter_hide_recurring: Optional[bool] = None, filter_app_mode: Optional[bool] = None, filter_admin: Optional[bool] = None, filter_hide_excess_events: Optional[bool] = None, filter_night_offset_hours: Optional[int] = None, filter_activities: Optional[str] = None, filter_event_types: Optional[str] = None, filter_event_ids: Optional[str] = None, filter_activity_ids: Optional[str] = None, filter_tag_ids: Optional[str] = None, filter_parent_id: Optional[str] = None, filter_show_deleted: Optional[bool] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent events der er relevante ud fra filtrering (bruges typisk til medlemsvisning).

    Kilde: GET /api/event/relevant
    Args:
        filter_activity_id (query, valgfri):
        filter_from_offset (query, valgfri):
        filter_from_time (query, valgfri):
        filter_to_time (query, valgfri):
        filter_tag_id (query, valgfri):
        filter_events_to_show (query, valgfri):
        filter_hide_recurring (query, valgfri):
        filter_app_mode (query, valgfri):
        filter_admin (query, valgfri):
        filter_hide_excess_events (query, valgfri):
        filter_night_offset_hours (query, valgfri):
        filter_activities (query, valgfri):
        filter_event_types (query, valgfri):
        filter_event_ids (query, valgfri):
        filter_activity_ids (query, valgfri):
        filter_tag_ids (query, valgfri):
        filter_parent_id (query, valgfri):
        filter_show_deleted (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_activity_id is not None:
        query["filter.activityId"] = filter_activity_id
    if filter_from_offset is not None:
        query["filter.fromOffset"] = filter_from_offset
    if filter_from_time is not None:
        query["filter.fromTime"] = filter_from_time
    if filter_to_time is not None:
        query["filter.toTime"] = filter_to_time
    if filter_tag_id is not None:
        query["filter.tagId"] = filter_tag_id
    if filter_events_to_show is not None:
        query["filter.eventsToShow"] = filter_events_to_show
    if filter_hide_recurring is not None:
        query["filter.hideRecurring"] = filter_hide_recurring
    if filter_app_mode is not None:
        query["filter.appMode"] = filter_app_mode
    if filter_admin is not None:
        query["filter.admin"] = filter_admin
    if filter_hide_excess_events is not None:
        query["filter.hideExcessEvents"] = filter_hide_excess_events
    if filter_night_offset_hours is not None:
        query["filter.nightOffsetHours"] = filter_night_offset_hours
    if filter_activities is not None:
        query["filter.activities"] = filter_activities
    if filter_event_types is not None:
        query["filter.eventTypes"] = filter_event_types
    if filter_event_ids is not None:
        query["filter.eventIds"] = filter_event_ids
    if filter_activity_ids is not None:
        query["filter.activityIds"] = filter_activity_ids
    if filter_tag_ids is not None:
        query["filter.tagIds"] = filter_tag_ids
    if filter_parent_id is not None:
        query["filter.parentId"] = filter_parent_id
    if filter_show_deleted is not None:
        query["filter.showDeleted"] = filter_show_deleted
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/event/relevant", path_params=path_params, query_params=query)


@mcp.tool()
def list_tags(filter_mode: Optional[str] = None, filter_created_offset: Optional[str] = None, filter_current_page: Optional[int] = None, filter_modified_offset: Optional[str] = None, filter_offset_entity: Optional[str] = None, filter_tag_filter: Optional[str] = None, filter_page_size: Optional[int] = None, filter_is_active: Optional[bool] = None, filter_search_text: Optional[str] = None, filter_partition_key: Optional[str] = None) -> dict:
    """Hent liste over hold/etiketter (tags) med filtrering.

    Kilde: GET /api/tag
    Args:
        filter_mode (query, valgfri):
        filter_created_offset (query, valgfri):
        filter_current_page (query, valgfri):
        filter_modified_offset (query, valgfri):
        filter_offset_entity (query, valgfri):
        filter_tag_filter (query, valgfri):
        filter_page_size (query, valgfri):
        filter_is_active (query, valgfri):
        filter_search_text (query, valgfri):
        filter_partition_key (query, valgfri):
    """
    query: dict = {}
    if filter_mode is not None:
        query["filter.mode"] = filter_mode
    if filter_created_offset is not None:
        query["filter.createdOffset"] = filter_created_offset
    if filter_current_page is not None:
        query["filter.currentPage"] = filter_current_page
    if filter_modified_offset is not None:
        query["filter.modifiedOffset"] = filter_modified_offset
    if filter_offset_entity is not None:
        query["filter.offsetEntity"] = filter_offset_entity
    if filter_tag_filter is not None:
        query["filter.tagFilter"] = filter_tag_filter
    if filter_page_size is not None:
        query["filter.pageSize"] = filter_page_size
    if filter_is_active is not None:
        query["filter.isActive"] = filter_is_active
    if filter_search_text is not None:
        query["filter.searchText"] = filter_search_text
    if filter_partition_key is not None:
        query["filter.partitionKey"] = filter_partition_key
    path_params = {}
    return client.get("/api/tag", path_params=path_params, query_params=query)


@mcp.tool()
def validate_booking_cancellation(id_: str) -> dict:
    """Tjek om en booking kan afbestilles ud fra reglerne (udfører ikke selve afbestillingen).

    Kilde: GET /api/booking/{id}/validatecancel
    Args:
        id_ (path, påkrævet):
    """
    query: dict = {}
    pass
    path_params = {"id": id_}
    return client.get("/api/booking/{id}/validatecancel", path_params=path_params, query_params=query)


if __name__ == "__main__":
    mcp.run()
