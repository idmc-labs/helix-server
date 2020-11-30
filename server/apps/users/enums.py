import graphene

from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from utils.enums import enum_description


class ACTION(enum.Enum):
    ADD = 'add'
    CHANGE = 'change'
    DELETE = 'delete'
    SIGN_OFF = 'sign_off'

    __labels__ = {
        ADD: _("Add"),
        CHANGE: _("Change"),
        DELETE: _("Delete"),
        SIGN_OFF: ("Sign Off")
    }


class MODEL(enum.Enum):
    CRISIS = 'crisis'
    EVENT = 'event'
    ENTRY = 'entry'
    ORGANIZATION = 'organization'
    ORGANIZATION_KIND = 'organizationkind'
    CONTACT = 'contact'
    COMMUNICATION = 'communication'
    FIGURE = 'figure'
    SUMMARY = 'summary'
    CONTEXTUAL_UPDATE = 'contextualupdate'
    RESOURCE = 'resource'
    USER = 'user'

    __labels__ = {
        CRISIS: _('crisis'),
        EVENT: _('event'),
        ENTRY: _('entry'),
        ORGANIZATION: _('organization'),
        ORGANIZATION_KIND: _('organizationkind'),
        CONTACT: _('contact'),
        COMMUNICATION: _('communication'),
        FIGURE: _('figure'),
        SUMMARY: _('summary'),
        CONTEXTUAL_UPDATE: _('contextualupdate'),
        RESOURCE: _('resource'),
        USER: _('user'),
    }


# NOTE: These are permision group names (role names) and are always assumed to
# be upper-cased
class ROLE(enum.Enum):
    ADMIN = 'ADMIN'
    IT_HEAD = 'IT_HEAD'
    MONITORING_EXPERT_EDITOR = 'MONITORING_EXPERT_EDITOR'
    MONITORING_EXPERT_REVIEWER = 'MONITORING_EXPERT_REVIEWER'
    GUEST = 'GUEST'

    __labels__ = {
        ADMIN: _('ADMIN'),
        IT_HEAD: _('IT_HEAD'),
        MONITORING_EXPERT_EDITOR: _('MONITORING_EXPERT_EDITOR'),
        MONITORING_EXPERT_REVIEWER: _('MONITORING_EXPERT_REVIEWER'),
        GUEST: _('GUEST'),
    }


PermissionActionEnum = graphene.Enum.from_enum(ACTION, enum_description)
PermissionModelEnum = graphene.Enum.from_enum(MODEL, enum_description)
PermissionRoleEnum = graphene.Enum.from_enum(ROLE, enum_description)
