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


class QA_RECOMMENDED_FIGURE_TYPE(enum.Enum):
    # constants for QA dashboard filter
    HAS_NO_RECOMMENDED_FIGURES = 0
    HAS_MULTIPLE_RECOMMENDED_FIGURES = 1

    __labels__ = {
        HAS_NO_RECOMMENDED_FIGURES: _("Has no recommended figures"),
        HAS_MULTIPLE_RECOMMENDED_FIGURES: _("Has mutiple recommended figures"),
    }
