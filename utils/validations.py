from collections import OrderedDict
from copy import deepcopy
from django.utils.translation import gettext
from django.db.models.query import QuerySet


def is_child_parent_dates_valid(
    data,
    instance,
    parent_field=None,
    c_start_field='start_date',
    c_end_field='end_date',
    p_start_field='start_date',
    p_end_field='end_date',
    start_text='start date',
    end_text='end date'
) -> OrderedDict:
    """
    c = child
    p = parent
    """
    errors = OrderedDict()

    c_start_date = data.get(c_start_field, getattr(instance, c_start_field, None))
    c_end_date = data.get(c_end_field, getattr(instance, c_end_field, None))
    if c_start_date and c_end_date and c_start_date > c_end_date:
        # FIXME: this is problematic
        errors[c_start_field] = gettext(f'Choose your {start_text} earlier than {end_text}')
        # FIXME: this is problematic
        errors[c_end_field] = gettext(f'Choose your {start_text} earlier than {end_text}')
    if not parent_field:
        return errors
    parent = instance
    p_start_date = None
    p_end_date = None
    parent_data = deepcopy(data)
    for pf in parent_field.split('.'):
        parent_data = getattr(parent_data, pf, dict())
        parent = parent_data.get(pf, getattr(parent, pf, None))
    if parent:
        p_start_date = getattr(parent, p_start_field, None)
        p_end_date = getattr(parent, p_end_field, None)
    if c_start_date and p_start_date and p_start_date > c_start_date:
        # FIXME: this is problematic
        errors[c_start_field] = gettext(f'Choose your {start_text} between {p_start_date} & {p_end_date}.')
    if c_end_date and p_end_date and c_end_date > p_end_date:
        # FIXME: this is problematic
        errors[c_end_field] = gettext(f'Choose your {end_text} between {p_start_field} & {p_end_field}.')
    return errors


def is_child_parent_inclusion_valid(data, instance, field, parent_field) -> OrderedDict:
    '''
    parent_field= '.' separated field, so that nested fields can be extracted
    '''
    errors = OrderedDict()
    value = data.get(field)
    if not value and instance:
        value = getattr(instance, field, None)
    if hasattr(value, 'all'):  # ManyRelatedManger
        value = value.all()
    if value is not None and type(value) not in (list, tuple, QuerySet):
        value = [value]
    elif value is None:
        value = []
    parent_value = data.get(parent_field.split('.')[0], getattr(instance, parent_field.split('.')[0], None))
    for pf in parent_field.split('.')[1:]:
        parent_value = parent_value.get(pf, None) if hasattr(parent_value, 'get') else getattr(parent_value, pf, None)
    if parent_value:
        if hasattr(parent_value, 'all'):
            parent_value = parent_value.all()
    if parent_value is None:
        parent_value = []
    if set(value).difference(parent_value):
        errors.update({
            # FIXME: this is problematic
            field: gettext(
                f'{field.title()} should be one of the {field}(s) of the {", ".join([str(i) for i in parent_value])}.'
            )
        })
    return errors
