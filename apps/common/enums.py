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
