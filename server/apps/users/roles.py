"""
codename will be built as <action>_<model> and used as...
Permission.objects.get(codename=<codename>)
"""

from .enums import PERMISSION_ACTION, PERMISSION_ENTITY, USER_ROLE

USER_ROLES = [USER_ROLE.ADMIN, USER_ROLE.IT_HEAD, USER_ROLE.MONITORING_EXPERT_EDITOR,
              USER_ROLE.MONITORING_EXPERT_REVIEWER, USER_ROLE.GUEST]

# All except user
ALL_MODELS = {PERMISSION_ENTITY.crisis, PERMISSION_ENTITY.event,
              PERMISSION_ENTITY.entry, PERMISSION_ENTITY.organization,
              PERMISSION_ENTITY.organizationkind, PERMISSION_ENTITY.contact,
              PERMISSION_ENTITY.communication, PERMISSION_ENTITY.figure,
              PERMISSION_ENTITY.summary, PERMISSION_ENTITY.contextualupdate,
              PERMISSION_ENTITY.resource, PERMISSION_ENTITY.review,
              PERMISSION_ENTITY.actor, PERMISSION_ENTITY.parkeditem,
              PERMISSION_ENTITY.reviewcomment}

# NOTE: To add custom permissions, add `bla_model` like `sign_off_model`.
PERMISSIONS = {
    USER_ROLE.ADMIN: {
        PERMISSION_ACTION.add: ALL_MODELS | {PERMISSION_ENTITY.user},
        PERMISSION_ACTION.change: ALL_MODELS | {PERMISSION_ENTITY.user},
        PERMISSION_ACTION.delete: ALL_MODELS | {PERMISSION_ENTITY.user},
    },
    USER_ROLE.IT_HEAD: {
        PERMISSION_ACTION.add: ALL_MODELS,
        PERMISSION_ACTION.change: ALL_MODELS,
        PERMISSION_ACTION.delete: ALL_MODELS,
        PERMISSION_ACTION.sign_off: {PERMISSION_ENTITY.entry},
    },
    USER_ROLE.MONITORING_EXPERT_EDITOR: {
        PERMISSION_ACTION.add: ALL_MODELS,
        PERMISSION_ACTION.change: ALL_MODELS,
        PERMISSION_ACTION.delete: ALL_MODELS,
    },
    USER_ROLE.MONITORING_EXPERT_REVIEWER: {
        PERMISSION_ACTION.add: ALL_MODELS - {PERMISSION_ENTITY.entry, PERMISSION_ENTITY.figure},
        PERMISSION_ACTION.change: ALL_MODELS - {PERMISSION_ENTITY.entry, PERMISSION_ENTITY.figure},
        PERMISSION_ACTION.delete: ALL_MODELS - {PERMISSION_ENTITY.entry, PERMISSION_ENTITY.figure},
    },
    USER_ROLE.GUEST: {
        PERMISSION_ACTION.add: set(),
        PERMISSION_ACTION.change: set(),
        PERMISSION_ACTION.delete: set(),
    }
}
