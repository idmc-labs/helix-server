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
        errors[c_start_field] = gettext('Choose your %s earlier than %s') % (start_text, c_end_date)
        errors[c_end_field] = gettext('Choose your %s earlier than %s') % (start_text, c_end_date)
    if not parent_field:
        return errors
    parent = instance
    p_start_date = None
    p_end_date = None
    parent_data = deepcopy(data)
    __first = True
    for pf in parent_field.split('.'):
        if __first:
            # only look into parent_data once
            parent = parent_data.get(pf) or getattr(parent, pf, None)
        else:
            if hasattr(parent, 'get'):
                parent = parent.get(pf)
            else:
                parent = getattr(parent, pf, None)
    if parent:
        p_start_date = getattr(parent, p_start_field, None)
        p_end_date = getattr(parent, p_end_field, None)
    if c_start_date and p_start_date and p_start_date > c_start_date:
        errors[c_start_field] = gettext('Choose your start date between %(p_start_date)s & %(p_end_date)s.') % dict(
            p_start_date=p_start_date,
            p_end_date=p_end_date,
        )
    if c_end_date and p_end_date and c_end_date > p_end_date:
        errors[c_end_field] = gettext('Choose your end date between %(p_start_date)s & %(p_end_date)s.') % dict(
            p_start_date=p_start_date,
            p_end_date=p_end_date,
        )
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
            field: gettext('%(field_name)s should be one of the following: %(parents)s.') % dict(
                field_name=field.title(),
                parents={", ".join([str(i) for i in parent_value])}
            )
        })
    return errors
