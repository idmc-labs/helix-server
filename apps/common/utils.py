def get_event_code(event_codes, type=None):
    from apps.event.models import EventCode

    def _get_event_code_label(key):
        obj = EventCode.EVENT_CODE_TYPE.get(key)
        return getattr(obj, "label", key)
    if not event_codes or event_codes == '':
        return

    # FIXME: We also get aggregation when there is not data
    splitted_event_codes = [event_code.split(':') for event_code in event_codes if event_code != '::']

    # TODO: get country as well

    return ', '.join([
        event_code[0] if type == 'code'
        else _get_event_code_label(int(event_code[1])
                                   if type == 'code_type' else event_code[2])
        for event_code in splitted_event_codes
    ])
