import graphene

from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from utils.enums import enum_description


class ACTION(enum.Enum):
    add = 0
    change = 1
    delete = 2
    sign_off = 3

    __labels__ = {
        add: _("Add"),
        change: _("Change"),
        delete: _("Delete"),
        sign_off: ("Sign Off")
    }


class MODEL(enum.Enum):
    crisis = 0
    event = 1
    entry = 2
    organization = 3
    organizationkind = 4
    contact = 5
    communication = 6
    figure = 7
    summary = 8
    contextualupdate = 9
    resource = 10
    user = 11

    __labels__ = {
        crisis: _('Crisis'),
        event: _('Event'),
        entry: _('Entry'),
        organization: _('Organization'),
        organizationkind: _('Organization Kind'),
        contact: _('Contact'),
        communication: _('Communication'),
        figure: _('Figure'),
        summary: _('Summary'),
        contextualupdate: _('Contextual Update'),
        resource: _('Resource'),
        user: _('User'),
    }


# NOTE: These are permision group names (role names) and are always assumed to
# be upper-cased
class USER_ROLE(enum.Enum):
    ADMIN = 0
    IT_HEAD = 1
    MONITORING_EXPERT_EDITOR = 2
    MONITORING_EXPERT_REVIEWER = 3
    GUEST = 4

    __labels__ = {
        ADMIN: _('ADMIN'),
        IT_HEAD: _('IT_HEAD'),
        MONITORING_EXPERT_EDITOR: _('MONITORING_EXPERT_EDITOR'),
        MONITORING_EXPERT_REVIEWER: _('MONITORING_EXPERT_REVIEWER'),
        GUEST: _('GUEST'),
    }


PermissionActionEnum = graphene.Enum.from_enum(ACTION, enum_description)
PermissionModelEnum = graphene.Enum.from_enum(MODEL, enum_description)
PermissionRoleEnum = graphene.Enum.from_enum(USER_ROLE, enum_description)
