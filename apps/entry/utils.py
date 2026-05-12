import random
import typing
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from apps.crisis.models import Crisis
from apps.entry.models import Figure, FigureLocation
from apps.event.models import Event
from apps.notification.models import Notification
from apps.organization.models import Organization
from apps.users.models import User


def generate_idu_from_figure_data(figure_data: typing.Dict) -> str:
    def number_to_words_less_than_ten(
        value: Optional[int],
    ) -> Optional[Union[str, int]]:
        if value is None:
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

        if 0 <= value < 10:
            return words[value]

        return value

    def get_cause_text(
        figure_cause: Optional[int],
        disaster_sub_type_id: Optional[int],
        violence_sub_type_id: Optional[int],
        other_sub_type_id: Optional[int],
    ):
        hazard_map_by_id = {
            1: "an earthquake",
            2: "a tsunami",
            3: "dry mass movement",
            4: "a sinkhole",
            5: "volcanic activity",
            6: "desertification",
            7: "a drought",
            8: "erosion",
            9: "salinization",
            10: "sea level rise",
            11: "a wildfire",
            12: "flooding caused by a dam release",
            13: "flooding",
            14: "an avalanche",
            15: "a landslide",
            16: "a rogue wave",
            17: "a cold wave",
            18: "a heat wave",
            19: "a hailstorm",
            20: "a sandstorm",
            21: "a storm",
            22: "storm surge",
            23: "a tornado",
            24: "a tropical cyclone",
            25: "a winter storm",
            26: "mixed disasters",
        }

        conflict_map_by_id = {
            2: "international armed conflict",
            7: "non-international armed conflict",
            11: "civilian state violence",
            12: "crime related violence",
            13: "communal violence",
            14: "conflict",
            17: "conflict",
        }

        other_crisis_by_id = {
            1: "development",
            2: "eviction",
            3: "a technical disaster",
        }

        cause_text = None

        if figure_cause == Crisis.CRISIS_TYPE.DISASTER.value and disaster_sub_type_id is not None:
            cause_text = hazard_map_by_id.get(int(disaster_sub_type))

        elif figure_cause == Crisis.CRISIS_TYPE.CONFLICT.value and violence_sub_type_id is not None:
            cause_text = conflict_map_by_id.get(int(violence_sub_type))

        elif figure_cause == Crisis.CRISIS_TYPE.OTHER.value and other_sub_type_id is not None:
            cause_text = other_crisis_by_id.get(int(other_sub_type_id))

        return cause_text

    def build_location_text(geo_locations: List[Dict]) -> Optional[str]:
        def get_display_names(identifier: str):
            return [
                loc.get("display_name")
                for loc in geo_locations
                if FigureLocation.IDENTIFIER(loc.get("identifier")).label == identifier and loc.get("display_name")
            ]

        origins = ", ".join(get_display_names("Origin"))
        destinations = ", ".join(get_display_names("Destination"))
        origin_and_destinations = get_display_names("ORIGIN_AND_DESTINATION")

        if origins and destinations:
            return f"from {origins} to {destinations}"

        if origin_and_destinations:
            return f"within {', '.join(origin_and_destinations)}"

        all_locations = ", ".join(loc.get("display_name") for loc in geo_locations if loc.get("display_name"))

        return f"in {all_locations}" if all_locations else None

    def get_unit_text(figure, unit) -> Optional[str]:
        unit_text: Optional[str] = None
        if unit == Figure.UNIT.PERSON:
            unit_text = "person" if figure == "one" else "people"
        elif unit == Figure.UNIT.HOUSEHOLD:
            unit_text = "household" if figure == "one" else "households"

        return unit_text

    def format_source(sources: Optional[List[Dict[str, Any]]]) -> str:
        def _is_defined(x) -> bool:
            return x is not None

        sources = Organization.objects.filter(id__in=sources)

        if not sources or len(sources) <= 0:
            return "reported sources"

        authorities = [
            s
            for s in sources
            if Organization.objects.get(id=s.id).organization_kind.name
            in (
                "Government",
                "Local Authority",
            )
        ]

        if authorities:
            return "national authorities" if len(authorities) == 1 else "local authorities"

        media_sources = [s for s in sources if Organization.objects.get(id=s.id).organization_kind.name in ("Media",)]

        if media_sources:
            return "media sources"

        named_sources = [Organization.objects.get(id=s.id).name for s in sources if _is_defined(s.name)]

        if len(named_sources) == 1:
            return named_sources[0]

        if len(named_sources) == 2:
            return f"{named_sources[0]} and {named_sources[1]}"

        if len(named_sources) > 2:
            all_but_last = ", ".join(named_sources[:-1])
            last = named_sources[-1]
            return f"{all_but_last}, and {last}"

        return "reported sources"

    def get_quantifier_text(q: Optional[Figure.QUANTIFIER]) -> Optional[str]:
        quantifier_mapping: dict[Figure.Quantifier, list[str]] = {
            Figure.QUANTIFIER.EXACT: [
                "a total of",
                "at least",
            ],
            Figure.QUANTIFIER.APPROXIMATELY: [
                "around",
                "about",
            ],
            Figure.QUANTIFIER.MORE_THAN_OR_EQUAL: [
                "more than",
                "at least",
            ],
            Figure.QUANTIFIER.LESS_THAN_OR_EQUAL: [
                "up to",
                "fewer than",
            ],
        }

        variants = quantifier_mapping[q]
        index = random.randint(0, len(variants) - 1)

        return variants[index]

    def to_ordinal(n: int) -> str:
        if 10 <= n % 100 <= 20:
            suffix = "th"
        else:
            suffix = {
                1: "st",
                2: "nd",
                3: "rd",
            }.get(n % 10, "th")

        return f"{n}{suffix}"

    def format_date(dt: datetime, *, day=False, month=False, year=False) -> str:
        parts = []

        if month:
            parts.append(dt.strftime("%B"))

        if day:
            parts.append(str(dt.day))

        if year:
            parts.append(str(dt.year))

        return " ".join(parts)

    def format_date_range(start: Optional[str], end: Optional[str] = None) -> Optional[str]:
        if not start:
            return None

        start_date = datetime.fromisoformat(start)
        end_date = datetime.fromisoformat(end) if end else None

        same_year = end_date is not None and start_date.year == end_date.year

        same_month = end_date is not None and same_year and start_date.month == end_date.month

        same_day = end_date is not None and same_month and start_date.day == end_date.day

        if not end_date or same_day:
            return f"on {format_date(start_date, day=True, month=True, year=True)}"

        if same_month:
            return (
                f"between the {to_ordinal(start_date.day)} "
                f"and {to_ordinal(end_date.day)} "
                f"of {format_date(start_date, month=True, year=True)}"
            )

        if same_year:
            return (
                f"between "
                f"{format_date(start_date, day=True, month=True)} "
                f"and "
                f"{format_date(end_date, day=True, month=True, year=True)}"
            )

        return f"between {format_date(start_date, month=True, year=True)} and {format_date(end_date, month=True, year=True)}"

    sources = figure_data.get("sources")
    organizations = Organization.objects.filter(id__in=sources)
    source_text = format_source(organizations)

    quantifier = figure_data.get("quantifier", 0)
    quantifier_text = get_quantifier_text(quantifier)

    displacement_term = figure_data.get("displacement_term", 0)
    displacement_term_text = Figure.FIGURE_TERMS(displacement_term).label
    figure = figure_data.get("figure")
    figure_text = number_to_words_less_than_ten(figure)

    unit = figure_data.get("unit", 0)
    unit_text = get_unit_text(figure_text, unit)
    verb = "was" if figure_text == "one" else "were"

    start_date = figure_data.get("start_date")
    end_date = figure_data.get("end_date")
    date_text = format_date_range(str(start_date), str(end_date))

    locations = figure_data.get("locations", [])
    location_text = build_location_text(locations)

    cause = figure_data.get("main_trigger", 0)
    disaster_sub_type = figure_data.get("disaster_sub_type")
    violence_sub_type = figure_data.get("violence_sub_type")
    other_sub_type = figure_data.get("other_sub_type")
    cause_text = get_cause_text(cause, disaster_sub_type, violence_sub_type, other_sub_type) or "Main Trigger"

    idu = (
        f"According to {source_text}, {quantifier_text} {figure_text} {unit_text} "
        f"{verb} reported {displacement_term_text} {location_text} due to {cause_text} {date_text}."
    )
    return idu.capitalize()


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
