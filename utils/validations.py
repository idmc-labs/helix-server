from collections import OrderedDict
from django.utils.translation import gettext
from django.db.models.query import QuerySet
from django.conf import settings
import requests


class MissingCaptchaException(Exception):
    pass


def is_child_parent_dates_valid(
    c_start_date, c_end_date,
    p_start_date, p_name
) -> OrderedDict:
    """
    c = child
    p = parent
    """
    errors = OrderedDict()

    if c_start_date and c_end_date and c_start_date > c_end_date:
        errors['start_date'] = gettext('Choose your start date earlier than end date.')
        errors['end_date'] = gettext('Choose your start date earlier than end date.')
        return errors
    if c_start_date and p_start_date and p_start_date > c_start_date:
        errors['start_date'] = gettext('Choose your start date after %s start date: %s.') % (
            p_name,
            p_start_date
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


def validate_hcaptcha(captcha, site_key):
    CAPTCHA_VERIFY_URL = 'https://hcaptcha.com/siteverify'
    SECRET_KEY = settings.HCAPTCHA_SECRET

    data = {'secret': SECRET_KEY, 'response': captcha, 'sitekey': site_key}
    response = requests.post(url=CAPTCHA_VERIFY_URL, data=data)

    response_json = response.json()
    return response_json['success']
