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
CROSS_BORDER_FLIGHT = 'Cross-border Flight'
CROSS_BORDER_RETURN = 'Cross-border Return'
RELOCATION_ELSEWHERE = 'Relocation Elsewhere'
DEATHS = 'Deaths'
PROVISIONAL_SOLUTIONS = 'Provisional Solutions'
FAILED_LOCAL_INTEGRATION = 'Failed Local Integration'
LOCAL_INTEGRATION = 'Local Integration'
FAILED_RETURN_RETURNEE_DISPLACEMENT = 'Failed Return / Returnee Displacement'
UNVERIFIED_STOCK = 'Unverified'
UNVERIFIED_FLOW = 'Unverified'

# constants for QA dashboard filter
HAS_NO_RECOMMENDED_FIGURES = "Has no recommended figures"
HAS_MULTIPLE_RECOMMENDED_FIGURES = "Has mutiple recommended figures"

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

FIGURE_TERMS = dict(
    # With displacement occurred option
    EVACUATED=dict(
        name="Evacuated",
        housing=False,
        displacement_occur=True,
    ),
    DISPLACED=dict(
        name="Displaced",
        housing=False,
        displacement_occur=True,
    ),
    FORCED_TO_FLEE=dict(
        name="Forced to flee",
        housing=False,
        displacement_occur=True,
    ),
    RELOCATED=dict(
        name="Relocated",
        housing=False,
        displacement_occur=True,
    ),
    SHELTERED=dict(
        name="Sheltered",
        housing=False,
        displacement_occur=True,
    ),
    IN_RELIEF_CAMP=dict(
        name="In relief camp",
        housing=False,
        displacement_occur=True,
    ),
    # END
    DESTROYED_HOUSING=dict(name="Destroyed housing", housing=True),
    PARTIALLY_DESTROYED_HOUSING=dict(name="Partially destroyed housing", housing=True),
    UNINHABITABLE_HOUSING=dict(name="Uninhabitable housing", housing=True),
    HOMELESS=dict(name="Homeless", housing=False),
    AFFECTED=dict(name="Affected", housing=False),
    RETURNS=dict(name="Returns", housing=False),
    MULTIPLE_OR_OTHER=dict(name="Multiple/Other", housing=False),
)

LESS_THAN_FIVE = "<5"
FIVE_TO_FOURTEEN = "5-14"
FIFTEEN_TO_TWENTRY_FOUR = "15-24"
ZERO_TO_SEVENTEEN = "0-17"
EIGHTEEN_TO_FIFTYNINE = "18-59"
SIXTY_PLUS = "60+"
OTHER_AGES = "Other ages"


AGE_CATEGORIES_TO_EXPORT = {
    LESS_THAN_FIVE: ["<=1", "0-2", "0-3", "0-4", "2-5", "3-5"],
    FIVE_TO_FOURTEEN: ["5-9", "5-11", "5-14", "6-11", "6-12"],
    FIFTEEN_TO_TWENTRY_FOUR: ["15-17", "15-18", "15-24"],
    ZERO_TO_SEVENTEEN: [
        "<1", "0-10", "0-14", "0-15", "0-16", "0-17", "0-2", "0-3", "0-4",
        "0-5", "0-6", "0-9", "1-3", "1-4", "1-5", "1-12", "10-14"
    ],
    EIGHTEEN_TO_FIFTYNINE: ["18-24", "18-25", "18-59"],
    SIXTY_PLUS: ["60+"],
    OTHER_AGES: [
        "0-18", "10-19", "10-24", "11-18", "12+", "12-17", "12-18", "13-17",
        "13-19", "15-59", "15-64", "16-59", "17-59", "18+", "18-60", "18-64",
        "19+", "20+", "20-59", "26-59", "5+", "5-17", "5-18", "50+", "6-17",
        "6-18", "65+", "unknown"
    ],
}
