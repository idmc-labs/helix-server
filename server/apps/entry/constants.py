# These will initialize the figure types and sub types
STOCK = 'Stock'
FLOW = 'Flow'

IDPS = 'IDPs'
RETURNEES = 'Returnees'
RETURN = 'Return'
LOCALLY_INTEGRATED_IDPS = 'Locally Integrated IDPs'
IDPS_SETTLED_ELSEWHERE = 'IDPs Settled Elsewhere'
PEOPLE_DISPLACED_ACROSS_BORDERS = 'People displaced across borders'
NEW_DISPLACEMENT = 'New Displacement'
MULTIPLE_DISPLACEMENT = 'Multiple Displacement'
PARTIAL_STOCK = 'Partial'
PARTIAL_FLOW = 'Partial'
CROSS_BORDER_FLIGHT = 'Cross-border Flight',
CROSS_BORDER_RETURN = 'Cross-border Return'
RELOCATION_ELSEWHERE = 'Relocation Elsewhere'
DEATHS = 'Deaths'
PROVISIONAL_SOLUTIONS = 'Provisional Solutions'
FAILED_LOCAL_INTEGRATION = 'Failed Local Integration'
LOCAL_INTEGRATION = 'Local Integration'
FAILED_RETURN_RETURNEE_DISPLACEMENT = 'Failed Return / Returnee Displacement'
UNVERIFIED_STOCK = 'Unverified'
UNVERIFIED_FLOW = 'Unverified'

FIGURE_TYPE_SUB_TYPES = {
    STOCK: [IDPS, RETURNEES, LOCALLY_INTEGRATED_IDPS, IDPS_SETTLED_ELSEWHERE,
            PEOPLE_DISPLACED_ACROSS_BORDERS, PARTIAL_STOCK, UNVERIFIED_STOCK],
    FLOW: [NEW_DISPLACEMENT, MULTIPLE_DISPLACEMENT, RETURN, PARTIAL_FLOW,
           FAILED_RETURN_RETURNEE_DISPLACEMENT, LOCAL_INTEGRATION,
           UNVERIFIED_FLOW, CROSS_BORDER_RETURN, FAILED_LOCAL_INTEGRATION,
           PROVISIONAL_SOLUTIONS, DEATHS, RELOCATION_ELSEWHERE,
           CROSS_BORDER_FLIGHT]
}

# FIGURE TAGS
FIGURE_TAGS = [
    'Protracted (1 year)',
    'Crime-induced displacement',
    'Transboundary disaster',
    'Protracted',
    'Indigenous communities affected',
    'Multi-causality',
    'Protracted (5 years)',
    'Chronic/repeated displacement',
]
