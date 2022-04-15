__all__ = ['PermissionRoleEnum', 'PermissionActionEnum', 'PermissionModelEnum']

import graphene

from django.utils.translation import gettext_lazy as _
from django_enumfield import enum
from utils.enums import enum_description


class PERMISSION_ACTION(enum.Enum):
    add = 0
    change = 1
    delete = 2
    sign_off = 3
    approve = 4

    __labels__ = {
        add: _('Add'),
        change: _('Change'),
        delete: _('Delete'),
        sign_off: _('Sign Off'),
        approve: _('Approve')
    }


class PERMISSION_ENTITY(enum.Enum):
    crisis = 0
    event = 1
    entry = 2
    organization = 3
    organizationkind = 4
    contact = 5
    communication = 6
    figure = 7
    summary = 8
    contextualanalysis = 9
    resource = 10
    user = 11
    review = 12
    actor = 13
    parkeditem = 14
    reviewcomment = 15
    contextualupdate = 16
    report = 17
    reportcomment = 18
    portfolio = 19
    contextofviolence = 20

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
        contextualanalysis: _('Contextual Analysis'),
        resource: _('Resource'),
        user: _('User'),
        review: _('Review'),
        reviewcomment: _('Review Comment'),
        actor: _('Actor'),
        parkeditem: _('Parked Item'),
        contextualupdate: _('Contextual Update'),
        report: _('Report'),
        reportcomment: _('Report Comment'),
        portfolio: _('Portfolio'),
        contextofviolence: _('Context of violence')
    }


# NOTE: These are permision group names (role names) and are always assumed to
# be upper-cased
class USER_ROLE(enum.Enum):
    ADMIN = 0
    REGIONAL_COORDINATOR = 1
    MONITORING_EXPERT = 2
    GUEST = 3

    __labels__ = {
        ADMIN: _('Admin'),
        MONITORING_EXPERT: _('Monitoring Expert'),
        REGIONAL_COORDINATOR: _('Regional Coordinator'),
        GUEST: _('Guest'),
    }


PermissionActionEnum = graphene.Enum.from_enum(PERMISSION_ACTION, enum_description)
PermissionModelEnum = graphene.Enum.from_enum(PERMISSION_ENTITY, enum_description)
PermissionRoleEnum = graphene.Enum.from_enum(USER_ROLE, enum_description)

enum_map = dict(
    PERMISSION_ENTITY=PermissionModelEnum,
    PERMISSION_ACTION=PermissionActionEnum,
    USER_ROLE=PermissionRoleEnum
)
