"""
codename will be built as <action>_<model> and used as...
Permission.objects.get(codename=<codename>)
"""

# NOTE: These are permision group names (role names) and are always assumed to be upper-cased
ADMIN = 'ADMIN'
IT_HEAD = 'IT_HEAD'
MONITORING_EXPERT_EDITOR = 'EDITOR'
MONITORING_EXPERT_REVIEWER = 'REVIEWER'
GUEST = 'GUEST'

ROLES = [ADMIN, IT_HEAD, MONITORING_EXPERT_EDITOR, MONITORING_EXPERT_REVIEWER, GUEST]

# All except user
ALL_MODELS = {'crisis', 'event', 'entry', 'organization', 'organizationkind', 'contact',
              'communication', 'figure', 'summary', 'contextualupdate', 'resource'}

# NOTE: To add custom permissions, add `bla_model` like `sign_off_model`.
PERMISSIONS = {
    ADMIN: {
        'add': ALL_MODELS | {'user'},
        'change': ALL_MODELS | {'user'},
        'delete': ALL_MODELS | {'user'},
    },
    IT_HEAD: {
        'add': ALL_MODELS,
        'change': ALL_MODELS,
        'delete': ALL_MODELS,
        'sign_off': {'entry'},
    },
    MONITORING_EXPERT_EDITOR: {
        'add': ALL_MODELS,
        'change': ALL_MODELS,
        'delete': ALL_MODELS,
    },
    MONITORING_EXPERT_REVIEWER: {
        'add': ALL_MODELS - {'entry', 'figure'},
        'change': ALL_MODELS - {'entry', 'figure'},
        'delete': ALL_MODELS - {'entry', 'figure'},
    },
    GUEST: {
        'add': [],
        'change': [],
        'delete': [],
    }
}
