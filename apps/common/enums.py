from django_enumfield import enum
from django.utils.translation import gettext_lazy as _


class GENDER_TYPE(enum.Enum):
    MALE = 0
    FEMALE = 1
    UNSPECIFIED = 2
    OTHER = 3

    __labels__ = {
        MALE: _("Male"),
        FEMALE: _("Female"),
        UNSPECIFIED: _("Unspecified"),
        OTHER: _("Other"),
    }


class QA_RULE_TYPE(enum.Enum):
    # constants for QA dashboard filter
    HAS_NO_RECOMMENDED_FIGURES = 0
    HAS_MULTIPLE_RECOMMENDED_FIGURES = 1

    __labels__ = {
        HAS_NO_RECOMMENDED_FIGURES: _("Has no recommended figures"),
        HAS_MULTIPLE_RECOMMENDED_FIGURES: _("Has mutiple recommended figures"),
    }


class EVENT_OTHER_SUB_TYPE(enum.Enum):
    DEVELOPMENT = 0
    EVICTION = 1
    TECHNICAL_DISASTER = 2
    # TODO: add more based on IDMC inputs

    __labels__ = {
        DEVELOPMENT: _('Development'),
        EVICTION: _('Eviction'),
        TECHNICAL_DISASTER: _('Technical disaster'),
    }
