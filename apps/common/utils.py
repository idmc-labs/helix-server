import typing


REDIS_SEPARATOR = ':'
INTERNAL_SEPARATOR = ':'

EXTERNAL_TUPLE_SEPARATOR = ', '
EXTERNAL_ARRAY_SEPARATOR = '; '
EXTERNAL_FIELD_SEPARATOR = ':'

EventCodeDataType = typing.List[
    typing.Union[
        typing.Tuple[str, str, str],
        typing.Tuple[None, None, None],
    ]
]

EventCodeAttrType = typing.Literal['code', 'code_type', 'iso3']


def format_locations(locations_data):
    from apps.entry.models import OSMName

    def _get_accuracy_label(key: str) -> str:
        obj = OSMName.OSM_ACCURACY(int(key))
        return getattr(obj, "label", key)

    def _get_identifier_label(key: str) -> str:
        obj = OSMName.IDENTIFIER(int(key))
        return getattr(obj, "label", key)

    location_list = []
    for loc in locations_data:
        location_name, location, accuracy, type_of_point = loc
        location_list.append(EXTERNAL_FIELD_SEPARATOR.join([
            location_name.strip(),
            location,
            _get_accuracy_label(accuracy),
            _get_identifier_label(type_of_point)
        ]))
    return EXTERNAL_ARRAY_SEPARATOR.join(location_list)


def format_event_codes(event_codes):
    from apps.event.models import EventCode

    def _get_event_code_label(key: str) -> str:
        obj = EventCode.EVENT_CODE_TYPE(int(key))
        return getattr(obj, "label", key)

    code_list = []
    for code in event_codes:
        if len(code) == 3:
            event_code, event_code_type, event_iso3 = code
            if not event_code and not event_code_type and not event_iso3:
                continue
            code_list.append(EXTERNAL_FIELD_SEPARATOR.join([
                event_code,
                _get_event_code_label(event_code_type),
                event_iso3,
            ]))
        else:
            event_code, event_code_type = code
            if not event_code and not event_code_type:
                continue
            code_list.append(EXTERNAL_FIELD_SEPARATOR.join([
                event_code,
                _get_event_code_label(event_code_type),
            ]))

    return EXTERNAL_ARRAY_SEPARATOR.join(code_list)


def get_attr_list_from_event_codes(event_codes: EventCodeDataType, attr_type: EventCodeAttrType):
    from apps.event.models import EventCode

    def _get_event_code_label(key: str) -> str:
        obj = EventCode.EVENT_CODE_TYPE(int(key))
        # NOTE: Why are we using int type for key
        return getattr(obj, "label", key)

    def _get_by_type(event_code: typing.Tuple[str, str, str]):
        if attr_type == 'code':
            return event_code[0]
        elif attr_type == 'code_type':
            return _get_event_code_label(event_code[1])
        return event_code

    if not event_codes or event_codes == '':
        return []

    return [
        _get_by_type(event_code)
        for event_code in event_codes
        if event_code != [None, None, None]
    ]


def get_attr_str_from_event_codes(event_codes: EventCodeDataType, attr_type: EventCodeAttrType):
    return EXTERNAL_ARRAY_SEPARATOR.join(
        get_attr_list_from_event_codes(event_codes, attr_type)
    )
