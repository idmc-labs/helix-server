from typing import Literal

TUPLE_SEPARATOR = ', '
ARRAY_SEPARATOR = '; '
FIELD_SEPARATOR = ':'


def get_attr_list_from_event_codes(
    event_codes: str,
    type: Literal['code', 'code_type', 'iso3'],
):
    from apps.event.models import EventCode

    def _get_event_code_label(key: int) -> str:
        obj = EventCode.EVENT_CODE_TYPE.get(key)
        # NOTE: Why are we using int type for key
        return getattr(obj, "label", key)

    if not event_codes or event_codes == '':
        return []

    # NOTE: We also get aggregation when there is not data
    # so we also check for '::'
    splitted_event_codes = [
        event_code.split(FIELD_SEPARATOR)
        for event_code in event_codes
        if event_code != f'{FIELD_SEPARATOR}{FIELD_SEPARATOR}'
    ]

    return [
        event_code[0] if type == 'code'
        else _get_event_code_label(int(event_code[1])) if type == 'code_type'
        else event_code[2]
        for event_code in splitted_event_codes
    ]


def get_attr_str_from_event_codes(
    event_codes: str,
    type: Literal['code', 'code_type', 'iso3'],
):
    return ARRAY_SEPARATOR.join(get_attr_list_from_event_codes(event_codes, type))
