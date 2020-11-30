"""
codename will be built as <action>_<model> and used as...
Permission.objects.get(codename=<codename>)
"""

from .enums import ACTION, MODEL, ROLE

ROLES = [ROLE.ADMIN, ROLE.IT_HEAD, ROLE.MONITORING_EXPERT_EDITOR,
         ROLE.MONITORING_EXPERT_REVIEWER, ROLE.GUEST]

# All except user
ALL_MODELS = {MODEL.crisis, MODEL.event, MODEL.entry, MODEL.organization,
              MODEL.organizationkind, MODEL.contact, MODEL.communication,
              MODEL.figure, MODEL.summary, MODEL.contextualupdate,
              MODEL.resource}

# NOTE: To add custom permissions, add `bla_model` like `sign_off_model`.
PERMISSIONS = {
    ROLE.ADMIN: {
        ACTION.add: ALL_MODELS | {MODEL.user},
        ACTION.change: ALL_MODELS | {MODEL.user},
        ACTION.delete: ALL_MODELS | {MODEL.user},
    },
    ROLE.IT_HEAD: {
        ACTION.add: ALL_MODELS,
        ACTION.change: ALL_MODELS,
        ACTION.delete: ALL_MODELS,
        ACTION.sign_off: {MODEL.entry},
    },
    ROLE.MONITORING_EXPERT_EDITOR: {
        ACTION.add: ALL_MODELS,
        ACTION.change: ALL_MODELS,
        ACTION.delete: ALL_MODELS,
    },
    ROLE.MONITORING_EXPERT_REVIEWER: {
        ACTION.add: ALL_MODELS - {MODEL.entry, MODEL.figure},
        ACTION.change: ALL_MODELS - {MODEL.entry, MODEL.figure},
        ACTION.delete: ALL_MODELS - {MODEL.entry, MODEL.figure},
    },
    ROLE.GUEST: {
        ACTION.add: set(),
        ACTION.change: set(),
        ACTION.delete: set(),
    }
}
