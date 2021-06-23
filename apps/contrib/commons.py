from django_enumfield import enum
from django.utils.translation import gettext_lazy as _
import graphene

from utils.enums import enum_description


class DATE_ACCURACY(enum.Enum):
    DAY = 0
    WEEK = 1
    MONTH = 2
    YEAR = 3

    __labels__ = {
        DAY: _('Day'),
        WEEK: _('Week'),
        MONTH: _('Month'),
        YEAR: _('Year'),
    }


DateAccuracyGrapheneEnum = graphene.Enum.from_enum(DATE_ACCURACY,
                                                   description=enum_description)
