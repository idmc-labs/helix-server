import functools
import typing

REDIS_SEPARATOR = ":"
INTERNAL_SEPARATOR = ":"

EXTERNAL_TUPLE_SEPARATOR = ", "
EXTERNAL_ARRAY_SEPARATOR = "; "
EXTERNAL_FIELD_SEPARATOR = ":"


@functools.lru_cache(maxsize=None)
def _cached_enum_label(enum_cls, member) -> str:
    return str(member.label)


def get_enum_label(member) -> typing.Optional[str]:
    """django_enumfield resolves the gettext translation on EVERY `.label`
    access, and the exports look a label up per row. Caching is safe because
    celery exports run under a single locale. Keyed by (class, member):
    members are int-like, so same-valued members of DIFFERENT enums are equal
    and hash-equal and would poison a member-only key."""
    if member is None:
        return None
    return _cached_enum_label(type(member), member)


def format_locations(
    locations_data: typing.List[typing.Tuple[str, str, str, str]],
) -> typing.List[typing.Tuple[str, str, str, str]]:
    from apps.entry.models import FigureLocation

    def _get_accuracy_label(key: str) -> str:
        return get_enum_label(FigureLocation.ACCURACY(int(key)))

    def _get_identifier_label(key: str) -> str:
        return get_enum_label(FigureLocation.IDENTIFIER(int(key)))

    location_list = []
    for loc in locations_data:
        location_name, location, accuracy, type_of_point = loc
        location_list.append(
            [
                location_name.strip(),
                location,
                _get_accuracy_label(accuracy),
                _get_identifier_label(type_of_point),
            ]
        )
    return location_list


def format_locations_raw(
    locations_data: typing.List[typing.Tuple[str, str, str, str, str]],
) -> typing.List[typing.Tuple[int, str, str, int, int]]:
    location_list = []
    for loc in locations_data:
        location_id, location_name, location, accuracy, type_of_point = loc
        location_list.append(
            [
                int(location_id),
                location_name.strip(),
                location,
                int(accuracy),
                int(type_of_point),
            ]
        )
    return location_list


def format_locations_as_string(
    locations_data: typing.List[typing.Tuple[str, str, str, str]],
) -> str:
    return EXTERNAL_ARRAY_SEPARATOR.join(EXTERNAL_FIELD_SEPARATOR.join(loc) for loc in format_locations(locations_data))


class ExtractLocationData(typing.TypedDict):
    display_name: typing.List[str]
    lat_lon: typing.List[str]
    accuracy: typing.List[str]
    type_of_points: typing.List[str]


class ExtractLocationDataRaw(typing.TypedDict):
    ids: typing.List[str]
    display_name: typing.List[str]
    lat_lon: typing.List[str]
    accuracy: typing.List[int]
    type_of_points: typing.List[int]


class ExtractLocationDataAsString(typing.TypedDict):
    display_name: str
    lat_lon: str
    accuracy: str
    type_of_points: str


def extract_location_data_list(
    data: typing.List[typing.Tuple[str, str, str, str]],
) -> ExtractLocationData:
    # Split the formatted location data into individual components
    location_components = format_locations(data)

    transposed_components = zip(*location_components)

    return {
        "display_name": next(transposed_components, []),
        "lat_lon": next(transposed_components, []),
        "accuracy": next(transposed_components, []),
        "type_of_points": next(transposed_components, []),
    }


def extract_location_raw_data_list(
    data: typing.List[typing.Tuple[str, str, str, str, str]],
) -> ExtractLocationDataRaw:
    # Split the formatted location data into individual components
    location_components = format_locations_raw(data)

    transposed_components = zip(*location_components)

    return {
        "ids": next(transposed_components, []),
        "display_name": next(transposed_components, []),
        "lat_lon": next(transposed_components, []),
        "accuracy": next(transposed_components, []),
        "type_of_points": next(transposed_components, []),
    }


def extract_location_data(
    data: typing.List[typing.Tuple[str, str, str, str]],
) -> ExtractLocationDataAsString:
    location_components = extract_location_data_list(data)

    return {
        "display_name": EXTERNAL_ARRAY_SEPARATOR.join(location_components["display_name"]),
        "lat_lon": EXTERNAL_ARRAY_SEPARATOR.join(location_components["lat_lon"]),
        "accuracy": EXTERNAL_ARRAY_SEPARATOR.join(location_components["accuracy"]),
        "type_of_points": EXTERNAL_ARRAY_SEPARATOR.join(location_components["type_of_points"]),
    }


def format_event_codes(
    event_codes_data: typing.List[typing.Union[typing.Tuple[str, str, str], typing.Tuple[str, str]]],
) -> typing.List[typing.Union[typing.Tuple[str, str, str], typing.Tuple[str, str]]]:
    from apps.event.models import EventCode

    def _get_event_code_label(key: str) -> str:
        return get_enum_label(EventCode.EVENT_CODE_TYPE(int(key)))

    code_list = []
    for code in event_codes_data:
        if len(code) == 3:
            event_code, event_code_type, event_iso3 = code
            if not event_code and not event_code_type and not event_iso3:
                continue
            code_list.append(
                [
                    event_code,
                    _get_event_code_label(event_code_type),
                    event_iso3,
                ]
            )
        else:
            event_code, event_code_type = code
            if not event_code and not event_code_type:
                continue
            code_list.append(
                [
                    event_code,
                    _get_event_code_label(event_code_type),
                ]
            )

    return code_list


def format_event_codes_raw(
    event_codes_data: typing.List[typing.Tuple[str, str, str, str]],
) -> typing.List[typing.Tuple[int, str, int, str]]:
    code_list = []
    for code in event_codes_data:
        _id, event_code, event_code_type, event_iso3 = code
        if _id is None:
            continue
        code_list.append(
            [
                int(_id),
                event_code,
                int(event_code_type),
                event_iso3,
            ]
        )
    return code_list


def format_event_codes_as_string(
    event_codes_data: typing.List[typing.Union[typing.Tuple[str, str, str], typing.Tuple[str, str]]],
) -> str:
    return EXTERNAL_ARRAY_SEPARATOR.join(EXTERNAL_FIELD_SEPARATOR.join(loc) for loc in format_event_codes(event_codes_data))


def extract_event_code_data_list(data: typing.List[typing.Union[typing.Tuple[str, str, str], typing.Tuple[str, str]]]):
    # Split the formatted event code data into individual components
    event_code_components = format_event_codes(data)

    transposed_components = zip(*event_code_components)

    return {
        "code": next(transposed_components, []),
        "code_type": next(transposed_components, []),
        "iso3": next(transposed_components, []),
    }


def extract_event_code_data(data: typing.List[typing.Union[typing.Tuple[str, str, str], typing.Tuple[str, str]]]):
    # Split the formatted event code data into individual components
    extracted_data = extract_event_code_data_list(data)

    return {
        "code": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("code", [])),
        "code_type": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("code_type", [])),
        "iso3": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("iso3", [])),
    }


def extract_event_code_data_raw_list(data: typing.List[typing.Tuple[str, str, str, str]]):
    # Split the formatted event code data into individual components
    event_code_components = format_event_codes_raw(data)

    transposed_components = zip(*event_code_components)

    return {
        "id": next(transposed_components, []),
        "code": next(transposed_components, []),
        "code_type": next(transposed_components, []),
        "iso3": next(transposed_components, []),
    }


def extract_event_code_data_raw(data: typing.List[typing.Tuple[str, str, str, str]]):
    # Split the formatted event code data into individual components
    extracted_data = extract_event_code_data_raw_list(data)

    return {
        "id": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("id", [])),
        "code": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("code", [])),
        "code_type": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("code_type", [])),
        "iso3": EXTERNAL_ARRAY_SEPARATOR.join(extracted_data.get("iso3", [])),
    }


class ExtractSourceData(typing.TypedDict):
    ids: typing.List[int]
    sources: typing.List[str]
    sources_type: typing.List[str]


def extract_source_data(data: typing.List[typing.Tuple[str, str, str]]) -> ExtractSourceData:
    ids = []
    sources = []
    sources_type = []
    for _id, source, source_type in data:
        if _id is None:
            continue
        ids.append(int(_id))
        sources.append(source)
        sources_type.append(source_type)
    return {
        "ids": ids,
        "sources": sources,
        "sources_type": sources_type,
    }


def extract_source_data_as_string(data: typing.List[typing.Tuple[str, str]]) -> str:
    return EXTERNAL_ARRAY_SEPARATOR.join(EXTERNAL_FIELD_SEPARATOR.join(item) for item in data)


class ExtractPublisherData(typing.TypedDict):
    ids: typing.List[int]
    publishers: typing.List[str]
    publishers_type: typing.List[str]


def extract_publisher_data(data: typing.List[typing.Tuple[str, str, str]]) -> ExtractPublisherData:
    ids = []
    publishers = []
    publishers_type = []
    for _id, publisher, publisher_type in data:
        if _id is None:
            continue
        ids.append(int(_id))
        publishers.append(publisher)
        publishers_type.append(publisher_type)
    return {
        "ids": ids,
        "publishers": publishers,
        "publishers_type": publishers_type,
    }


def extract_context_of_voilence_raw_data_list(data: typing.List[typing.Tuple[str, str]]):
    ids = []
    context_of_violence = []
    for _id, violence in data:
        if _id is None:
            continue
        ids.append(int(_id))
        context_of_violence.append(violence)
    return {
        "ids": ids,
        "context_of_violence": context_of_violence,
    }


def extract_tag_raw_data_list(data: typing.List[typing.Tuple[str, str]]):
    ids = []
    tags = []
    for _id, tag in data:
        if _id is None:
            continue
        ids.append(int(_id))
        tags.append(tag)
    return {
        "ids": ids,
        "tags": tags,
    }
