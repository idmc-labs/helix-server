"""
codename will be built as <action>_<model> and used as...
Permission.objects.get(codename=<codename>)
"""

from .enums import ACTION, MODEL, USER_ROLE

USER_ROLES = [USER_ROLE.ADMIN, USER_ROLE.IT_HEAD, USER_ROLE.MONITORING_EXPERT_EDITOR,
         USER_ROLE.MONITORING_EXPERT_REVIEWER, USER_ROLE.GUEST]

# All except user
ALL_MODELS = {MODEL.crisis, MODEL.event, MODEL.entry, MODEL.organization,
              MODEL.organizationkind, MODEL.contact, MODEL.communication,
              MODEL.figure, MODEL.summary, MODEL.contextualupdate,
              MODEL.resource}

# NOTE: To add custom permissions, add `bla_model` like `sign_off_model`.
PERMISSIONS = {
    USER_ROLE.ADMIN: {
        ACTION.add: ALL_MODELS | {MODEL.user},
        ACTION.change: ALL_MODELS | {MODEL.user},
        ACTION.delete: ALL_MODELS | {MODEL.user},
    },
    USER_ROLE.IT_HEAD: {
        ACTION.add: ALL_MODELS,
        ACTION.change: ALL_MODELS,
        ACTION.delete: ALL_MODELS,
        ACTION.sign_off: {MODEL.entry},
    },
    USER_ROLE.MONITORING_EXPERT_EDITOR: {
        ACTION.add: ALL_MODELS,
        ACTION.change: ALL_MODELS,
        ACTION.delete: ALL_MODELS,
    },
    USER_ROLE.MONITORING_EXPERT_REVIEWER: {
        ACTION.add: ALL_MODELS - {MODEL.entry, MODEL.figure},
        ACTION.change: ALL_MODELS - {MODEL.entry, MODEL.figure},
        ACTION.delete: ALL_MODELS - {MODEL.entry, MODEL.figure},
    },
    USER_ROLE.GUEST: {
        ACTION.add: set(),
        ACTION.change: set(),
        ACTION.delete: set(),
    }
}
