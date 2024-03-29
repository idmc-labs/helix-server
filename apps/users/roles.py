"""
codename will be built as <action>_<model> and used as...
Permission.objects.get(codename=<codename>)
"""

from .enums import PERMISSION_ACTION, PERMISSION_ENTITY, USER_ROLE

USER_ROLES = [
    USER_ROLE.ADMIN,
    USER_ROLE.MONITORING_EXPERT,
    USER_ROLE.REGIONAL_COORDINATOR,
    USER_ROLE.DIRECTORS_OFFICE,
    USER_ROLE.REPORTING_TEAM,
    USER_ROLE.GUEST
]

MONITORING_EXPERT_MODELS = {
    PERMISSION_ENTITY.crisis,
    PERMISSION_ENTITY.event,
    PERMISSION_ENTITY.contextualupdate,
    PERMISSION_ENTITY.entry,
    PERMISSION_ENTITY.figure,
    PERMISSION_ENTITY.reviewcomment,
    PERMISSION_ENTITY.parkeditem,
    PERMISSION_ENTITY.organization,
    PERMISSION_ENTITY.summary,
    PERMISSION_ENTITY.contact,
    PERMISSION_ENTITY.communication,
    PERMISSION_ENTITY.contextualanalysis,
    PERMISSION_ENTITY.resource,
    PERMISSION_ENTITY.report,
    PERMISSION_ENTITY.reportcomment,
    PERMISSION_ENTITY.figuretag,
}

REGIONAL_COORDINATOR_MODELS = MONITORING_EXPERT_MODELS | {
    PERMISSION_ENTITY.actor,
    PERMISSION_ENTITY.organizationkind,
    PERMISSION_ENTITY.contextofviolence,
}

ADMIN_MODELS = REGIONAL_COORDINATOR_MODELS | {
    PERMISSION_ENTITY.user,
    PERMISSION_ENTITY.portfolio,
    PERMISSION_ENTITY.client,
}

# NOTE: To add custom permissions, add `bla_model` like `sign_off_model`.
PERMISSIONS = {
    USER_ROLE.ADMIN: {
        PERMISSION_ACTION.add: ADMIN_MODELS,
        PERMISSION_ACTION.change: ADMIN_MODELS,
        PERMISSION_ACTION.delete: ADMIN_MODELS,
        PERMISSION_ACTION.approve: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.figure},
        PERMISSION_ACTION.sign_off: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.event},
        PERMISSION_ACTION.assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.self_assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_self_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.update_pfa_visibility: {PERMISSION_ENTITY.report},
        PERMISSION_ACTION.update_gidd_data: {PERMISSION_ENTITY.gidd},
        PERMISSION_ACTION.update_release_meta_data: {PERMISSION_ENTITY.gidd},
    },
    USER_ROLE.REGIONAL_COORDINATOR: {
        PERMISSION_ACTION.add: REGIONAL_COORDINATOR_MODELS,
        PERMISSION_ACTION.change: REGIONAL_COORDINATOR_MODELS,
        PERMISSION_ACTION.delete: REGIONAL_COORDINATOR_MODELS,
        PERMISSION_ACTION.approve: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.figure},
        PERMISSION_ACTION.sign_off: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.event},
        PERMISSION_ACTION.assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.self_assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_self_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.update_pfa_visibility: {PERMISSION_ENTITY.report},
        PERMISSION_ACTION.update_gidd_data: set(),
        PERMISSION_ACTION.update_release_meta_data: set(),
    },
    USER_ROLE.MONITORING_EXPERT: {
        PERMISSION_ACTION.add: MONITORING_EXPERT_MODELS,
        PERMISSION_ACTION.change: MONITORING_EXPERT_MODELS,
        PERMISSION_ACTION.delete: MONITORING_EXPERT_MODELS,
        PERMISSION_ACTION.approve: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.figure},
        PERMISSION_ACTION.sign_off: set(),
        PERMISSION_ACTION.assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.self_assign: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.clear_self_assignee: {PERMISSION_ENTITY.event},
        PERMISSION_ACTION.update_pfa_visibility: set(),
        PERMISSION_ACTION.update_gidd_data: set(),
        PERMISSION_ACTION.update_release_meta_data: set(),
    },
    USER_ROLE.DIRECTORS_OFFICE: {
        PERMISSION_ACTION.add: set(),
        PERMISSION_ACTION.change: {PERMISSION_ENTITY.report},
        PERMISSION_ACTION.delete: set(),
        PERMISSION_ACTION.approve: set(),
        PERMISSION_ACTION.sign_off: set(),
        PERMISSION_ACTION.assign: set(),
        PERMISSION_ACTION.self_assign: set(),
        PERMISSION_ACTION.clear_assignee: set(),
        PERMISSION_ACTION.clear_self_assignee: set(),
        PERMISSION_ACTION.update_gidd_data: set(),
        PERMISSION_ACTION.update_release_meta_data: set(),
    },
    USER_ROLE.REPORTING_TEAM: {
        PERMISSION_ACTION.add: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.organization, PERMISSION_ENTITY.figuretag},
        PERMISSION_ACTION.change: {PERMISSION_ENTITY.report, PERMISSION_ENTITY.organization, PERMISSION_ENTITY.figuretag},
        PERMISSION_ACTION.delete: {PERMISSION_ENTITY.report},
        PERMISSION_ACTION.approve: set(),
        PERMISSION_ACTION.sign_off: set(),
        PERMISSION_ACTION.assign: set(),
        PERMISSION_ACTION.self_assign: set(),
        PERMISSION_ACTION.clear_assignee: set(),
        PERMISSION_ACTION.clear_self_assignee: set(),
        PERMISSION_ACTION.update_gidd_data: set(),
        PERMISSION_ACTION.update_release_meta_data: set(),
    },
    USER_ROLE.GUEST: {
        PERMISSION_ACTION.add: set(),
        PERMISSION_ACTION.change: set(),
        PERMISSION_ACTION.delete: set(),
        PERMISSION_ACTION.approve: set(),
        PERMISSION_ACTION.sign_off: set(),
        PERMISSION_ACTION.assign: set(),
        PERMISSION_ACTION.self_assign: set(),
        PERMISSION_ACTION.clear_assignee: set(),
        PERMISSION_ACTION.clear_self_assignee: set(),
        PERMISSION_ACTION.update_gidd_data: set(),
        PERMISSION_ACTION.update_release_meta_data: set(),
    }
}
