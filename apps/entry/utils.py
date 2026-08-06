import typing
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureLocation
from apps.event.models import DisasterSubType, Event, OtherSubType, ViolenceSubType
from apps.notification.models import Notification
from apps.organization.models import Organization
from apps.users.models import User

# IDU (Internal Displacement Update) excerpt text generation.
# Ported from the frontend generateExcerptIduText.

# 1-indexed month names, hardcoded so output does not depend on the locale
_MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

_QUANTIFIER_MAPPING: Dict[str, Optional[str]] = {
    "EXACT": None,
    "APPROXIMATELY": "around",
    "MORE_THAN_OR_EQUAL": "at least",
    "LESS_THAN_OR_EQUAL": "up to",
}

_HOUSING_CONDITION_TEXT: Dict[str, str] = {
    "DESTROYED_HOUSING": "destroyed",
    "PARTIALLY_DESTROYED_HOUSING": "partially destroyed",
    "UNINHABITABLE_HOUSING": "rendered uninhabitable",
}

_TERM_TEXT_OVERRIDES: Dict[str, str] = {
    "RETURNS": "returned",
    "IN_RELIEF_CAMP": "in a relief camp",
    "MULTIPLE_OR_OTHER": "displaced",
    "HOMELESS": "rendered homeless",
}


def _enum_member(enum_cls, value):
    """The enum member for a member or its raw value."""
    if value is None:
        return None
    return enum_cls(getattr(value, "value", value))


def _enum_name(enum_cls, value) -> Optional[str]:
    # `is not None`, never truthiness: value-0 members (e.g. UNIT.PERSON) are falsy.
    member = _enum_member(enum_cls, value)
    return member.name if member is not None else None


def to_ordinal(n: int) -> str:
    mod100 = n % 100
    if 11 <= mod100 <= 13:
        return f"{n}th"
    last = n % 10
    if last == 1:
        return f"{n}st"
    if last == 2:
        return f"{n}nd"
    if last == 3:
        return f"{n}rd"
    return f"{n}th"


def join_with_and(items: Sequence[str]) -> str:
    """[] -> "", [a] -> "a", [a, b] -> "a and b", [a, b, c] -> "a, b, and c"."""
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def get_quantifier_text(quantifier: Optional[str]) -> Optional[str]:
    if not quantifier:
        # Placeholder, matching the other unset-field placeholders.
        return "(Quantifier)"
    return _QUANTIFIER_MAPPING.get(quantifier)


def _to_calendar_date(value: typing.Union[str, date, None]) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def format_date_range(
    start: typing.Union[str, date, None],
    end: typing.Union[str, date, None] = None,
) -> Optional[str]:
    start_date = _to_calendar_date(start)
    if start_date is None:
        return None

    def get_full_date_str(d: date) -> str:
        return f"{_MONTH_NAMES[d.month]} {d.day}, {d.year}"

    def get_day_month_str(d: date) -> str:
        return f"{_MONTH_NAMES[d.month]} {d.day}"

    end_date = _to_calendar_date(end)
    if end_date is None:
        return f"on {get_full_date_str(start_date)}"

    same_year = start_date.year == end_date.year
    same_month = same_year and start_date.month == end_date.month
    same_day = same_month and start_date.day == end_date.day

    if same_day:
        return f"on {get_full_date_str(start_date)}"
    if same_month:
        return (
            f"between the {to_ordinal(start_date.day)} and {to_ordinal(end_date.day)} "
            f"of {_MONTH_NAMES[start_date.month]} {start_date.year}"
        )
    if same_year:
        return f"between {get_day_month_str(start_date)} and {get_full_date_str(end_date)}"
    return f"between {get_full_date_str(start_date)} and {get_full_date_str(end_date)}"


def format_source(sources: Optional[Sequence[Dict[str, Any]]]) -> str:
    """Authority/media kinds collapse to fixed labels in a fixed order; every other
    kind keeps its own name. The fixed order makes output independent of input order.
    """
    sources = list(sources or [])

    def has_kind(kind: str) -> bool:
        return any(s.get("organization_kind") == kind for s in sources)

    labels: List[str] = []
    if has_kind("Local Authority"):
        labels.append("local authorities")
    if has_kind("Government"):
        labels.append("national authorities")
    if has_kind("Media"):
        labels.append("media sources")

    named_sources = [
        s.get("name")
        for s in sources
        if s.get("organization_kind") not in ("Local Authority", "Government", "Media") and s.get("name") is not None
    ]
    seen: typing.Set[str] = set()
    for name in named_sources:
        if name not in seen:
            seen.add(name)
            labels.append(name)

    # Empty -> ""; the "(Source)" placeholder is applied once, when assembling the sentence.
    return join_with_and(labels)


def number_to_words_less_than_ten(num: Optional[int]) -> Optional[str]:
    if num is None:
        return None

    words = [
        "zero",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
    ]

    if 0 <= num < 10:
        return words[num]

    # Grouped integer like "1,156" for >= 10 (reported is an int, so no decimals).
    return f"{num:,}"


def get_lowest_admin_level(display_name: Optional[str]) -> Optional[str]:
    if not display_name:
        return None
    return display_name.split(",")[0].strip()


def _lowest_admin_levels(display_names: Sequence[Optional[str]]) -> List[str]:
    """Lowest admin level of each name, deduped preserving order (many locations
    can collapse to the same name)."""
    result: List[str] = []
    seen: typing.Set[str] = set()
    for display_name in display_names:
        level = get_lowest_admin_level(display_name)
        if level is not None and level not in seen:
            seen.add(level)
            result.append(level)
    return result


def _resolve_cause_text(input_data: Dict[str, Any]) -> Optional[str]:
    # Unknown id, or a row with a null idu_name, degrades to the "(Main trigger)"
    # placeholder rather than raising.
    figure_cause = _enum_name(Crisis.CRISIS_TYPE, input_data.get("figure_cause"))
    lookups = {
        "DISASTER": ("disaster_sub_type", DisasterSubType),
        "CONFLICT": ("violence_sub_type", ViolenceSubType),
        "OTHER": ("other_sub_type", OtherSubType),
    }
    match = lookups.get(figure_cause)
    if match is None:
        return None
    field, model = match
    sub_type_id = input_data.get(field)
    if sub_type_id is None:
        return None
    try:
        obj = model.objects.filter(id=int(sub_type_id)).first()
    except (TypeError, ValueError):
        return None
    if obj is None:
        return None
    return obj.idu_name or None


def generate_excerpt_idu_text(input_data: Dict[str, Any]) -> str:
    """Build the IDU excerpt from figure-shaped input.

    Every field is optional; anything missing renders as a placeholder.
    """
    located = [
        (_enum_name(FigureLocation.IDENTIFIER, loc.get("identifier")), loc.get("display_name"))
        for loc in (input_data.get("geo_locations") or [])
    ]

    def get_lowest_level_locations(identifier: Optional[str]) -> List[str]:
        return _lowest_admin_levels([name for ident, name in located if ident == identifier])

    origin_levels = get_lowest_level_locations("ORIGIN")
    destination_levels = get_lowest_level_locations("DESTINATION")
    origin_and_destination_levels = get_lowest_level_locations("ORIGIN_AND_DESTINATION")

    # Origin and destination that resolve to the same place(s) read as "in".
    same_origin_and_destination = (
        len(origin_levels) > 0
        and len(origin_levels) == len(destination_levels)
        and all(loc in destination_levels for loc in origin_levels)
    )

    term_member = _enum_member(Figure.FIGURE_TERMS, input_data.get("term"))
    term = term_member.name if term_member is not None else None

    location_text: Optional[str]
    if same_origin_and_destination:
        location_text = f"in {join_with_and(origin_levels)}"
    elif len(origin_levels) > 0 and len(destination_levels) > 0:
        location_text = f"from {join_with_and(origin_levels)} to {join_with_and(destination_levels)}"
    elif term == "RETURNS" and len(destination_levels) > 0:
        # Returns tagged with only a destination reads "returned to <place>".
        location_text = f"to {join_with_and(destination_levels)}"
    elif len(origin_and_destination_levels) > 0:
        location_text = f"in {join_with_and(origin_and_destination_levels)}"
    else:
        all_locations = join_with_and(_lowest_admin_levels([name for _, name in located]))
        location_text = f"in {all_locations}" if all_locations else None

    reported = input_data.get("reported")
    cause_text = _resolve_cause_text(input_data)
    housing_condition = _HOUSING_CONDITION_TEXT.get(term) if term else None

    unit = _enum_name(Figure.UNIT, input_data.get("unit"))
    unit_text: Optional[str] = None
    if reported is not None:
        is_plural = reported != 1
        if unit == "PERSON":
            unit_text = "people" if is_plural else "person"
        elif unit == "HOUSEHOLD" and housing_condition:
            unit_text = "houses" if is_plural else "house"
        elif unit == "HOUSEHOLD":
            unit_text = "households" if is_plural else "household"

    term_text: Optional[str]
    if housing_condition:
        term_text = housing_condition
    elif term and term in _TERM_TEXT_OVERRIDES:
        term_text = _TERM_TEXT_OVERRIDES[term]
    elif term_member is not None:
        term_text = str(term_member.label).lower()
    else:
        term_text = None

    # Person + housing reads "the housing of {figure} people were <condition>".
    subject_prefix = "the housing of" if (housing_condition and unit == "PERSON") else None

    quantifier = _enum_name(Figure.QUANTIFIER, input_data.get("quantifier"))
    # An inexact quantifier ("up to" / "around") is dropped when the figure is exactly one.
    drop_quantifier_for_one = reported == 1 and quantifier in ("LESS_THAN_OR_EQUAL", "APPROXIMATELY")
    quantifier_field = None if drop_quantifier_for_one else get_quantifier_text(quantifier)

    # Assemble the sentence; any missing piece falls back to its bracketed placeholder.
    # A subject prefix ("the housing of ...") is singular, so the verb is "was".
    verb = "was" if (subject_prefix or reported == 1) else "were"
    parts = [
        subject_prefix,
        quantifier_field,
        number_to_words_less_than_ten(reported) or "(Figure)",
        unit_text or "(People or Household)",
        None if term == "RETURNS" else verb,  # Returns carries its own past-tense verb
        term_text or "(Term)",
        location_text or "(Location)",
        "following" if term == "RETURNS" else "due to",
        cause_text or "(Main trigger)",
        format_date_range(input_data.get("start_date"), input_data.get("end_date")) or "(Date of Event DD/MM/YYY)",
    ]
    body = " ".join(part for part in parts if part is not None)
    source_type = format_source(input_data.get("sources") or []) or "(Source)"
    return f"According to {source_type}, {body}."


def _sources_from_ids(source_ids: Optional[Sequence[int]]) -> List[Dict[str, Optional[str]]]:
    if not source_ids:
        return []
    organizations = Organization.objects.filter(id__in=source_ids).select_related("organization_kind")
    by_id = {org.id: org for org in organizations}
    # Preserve the caller's order.
    result: List[Dict[str, Optional[str]]] = []
    for source_id in source_ids:
        org = by_id.get(int(source_id)) if source_id is not None else None
        if org is None:
            continue
        kind = org.organization_kind.name if org.organization_kind_id else None
        result.append({"name": org.name, "organization_kind": kind})
    return result


def generate_idu_excerpt(input_with_ids: Dict[str, Any]) -> str:
    """Generate the IDU excerpt from figure-shaped input whose ``sources`` are
    Organization ids. The single entrypoint for the live-preview query and for
    figure auto-generation."""
    data = dict(input_with_ids)
    data["sources"] = _sources_from_ids(data.get("sources"))
    return generate_excerpt_idu_text(data)


def figure_to_idu_input(figure: Figure) -> Dict[str, Any]:
    """Reshape a saved Figure into ``generate_idu_excerpt`` input.

    m2m fields (geo_locations, sources) must already be populated.
    """
    return {
        "geo_locations": [
            {"identifier": loc.identifier, "display_name": loc.display_name} for loc in figure.geo_locations.all()
        ],
        "reported": figure.reported,
        "figure_cause": figure.figure_cause,
        "disaster_sub_type": figure.disaster_sub_type_id,
        "violence_sub_type": figure.violence_sub_type_id,
        "other_sub_type": figure.other_sub_type_id,
        "term": figure.term,
        "unit": figure.unit,
        "quantifier": figure.quantifier,
        "start_date": figure.start_date,
        "end_date": figure.end_date,
        "sources": [org.id for org in figure.sources.all()],
    }


def get_figure_notification_type(event, is_deleted=False, is_new=False):
    if event.review_status in [
        Event.EVENT_REVIEW_STATUS.SIGNED_OFF,
        Event.EVENT_REVIEW_STATUS.SIGNED_OFF_BUT_CHANGED,
    ]:
        if is_deleted:
            return Notification.Type.FIGURE_DELETED_IN_SIGNED_EVENT
        if is_new:
            return Notification.Type.FIGURE_CREATED_IN_SIGNED_EVENT
        # For update
        return Notification.Type.FIGURE_UPDATED_IN_SIGNED_EVENT

    elif event.review_status in [
        Event.EVENT_REVIEW_STATUS.APPROVED,
        Event.EVENT_REVIEW_STATUS.APPROVED_BUT_CHANGED,
    ]:
        if is_deleted:
            return Notification.Type.FIGURE_DELETED_IN_APPROVED_EVENT
        if is_new:
            return Notification.Type.FIGURE_CREATED_IN_APPROVED_EVENT
        # For update
        return Notification.Type.FIGURE_UPDATED_IN_APPROVED_EVENT


def get_event_notification_type(event, is_figure_deleted=False, is_figure_new=False):
    return get_figure_notification_type(event, is_deleted=is_figure_deleted, is_new=is_figure_new)


def send_figure_notifications(
    figure: Figure,
    actor: User,
    notification_type: Notification.Type,
    is_deleted: bool = False,
    event: typing.Optional[Event] = None,
):
    _event = event or figure.event

    recipients = [
        user["id"]
        for user in Event.regional_coordinators(
            _event,
            actor=actor,
        )
    ]
    if _event.created_by_id:
        recipients.append(_event.created_by_id)
    if _event.assignee_id:
        recipients.append(_event.assignee_id)

    Notification.send_safe_multiple_notifications(
        recipients=recipients,
        actor=actor,
        event=_event,
        entry=figure.entry,
        type=notification_type,
        **(dict(figure=figure) if not is_deleted else dict()),
    )


class BulkUpdateFigureManager:
    event_ids: typing.Set[int]
    figure_moved_from_event: typing.Set[Event]
    figure_moved_to_event: typing.Set[Event]

    def __enter__(self):
        self.event_ids = set()
        self.figure_moved_from_event = set()
        self.figure_moved_to_event = set()
        return self

    def add_event(self, event_id: int):
        self.event_ids.add(event_id)

    # Note: Using *_ will make typing make this as non context manager
    def __exit__(self, exc_type, exc_value, exc_traceback):
        # Update status
        for event_id in self.event_ids:
            Figure.update_event_status_and_send_notifications(event_id)
