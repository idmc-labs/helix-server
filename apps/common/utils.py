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
        return event_code[2]

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
