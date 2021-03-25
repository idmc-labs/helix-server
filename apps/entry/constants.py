from django_enumfield import enum


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
    EVACUATED=dict(name="Evacuated", housing=False),
    DISPLACED=dict(name="Displaced", housing=False),
    DESTROYED_HOUSING=dict(name="Destroyed housing", housing=True),
    PARTIALLY_DESTROYED_HOUSING=dict(name="Partially destroyed housing", housing=True),
    UNINHABITABLE_HOUSING=dict(name="Uninhabitable housing", housing=True),
    FORCED_TO_FLEE=dict(name="Forced to flee", housing=False),
    HOMELESS=dict(name="Homeless", housing=False),
    IN_RELIEF_CAMP=dict(name="In relief camp", housing=False),
    SHELTERED=dict(name="Sheltered", housing=False),
    RELOCATED=dict(name="Relocated", housing=False),
    AFFECTED=dict(name="Affected", housing=False),
    RETURNS=dict(name="Returns", housing=False),
    MULTIPLE_OR_OTHER=dict(name="Multiple/Other", housing=False),
)

class DISAGGREGATED_AGE_SEX_CHOICES(enum.Enum):
    MALE = 0
    FEMALE = 1

    __labels__ = {
        MALE: 'Male',
        FEMALE: 'Female',
    }


DISAGGREGATED_AGE_CATEGORIES = [
    "unspecified",
    "0-1",
    "0-10",
    "0-11",
    "0-14",
    "0-15",
    "0-16",
    "0-17",
    "0-18",
    "0-2",
    "0-3",
    "0-4",
    "0-5",
    "0-6",
    "0-9",
    "1-12",
    "1-3",
    "1-4",
    "1-5",
    "10-14",
    "10-19",
    "11-18",
    "12+",
    "12-17",
    "12-18",
    "13-17",
    "13-19",
    "15-17",
    "15-18",
    "15-19",
    "15-59",
    "15-64",
    "16-59",
    "17",
    "17-5",
    "17-59",
    "18+",
    "18-15",
    "18-25",
    "18-28",
    "18-30",
    "18-49",
    "18-50",
    "18-55",
    "18-59",
    "18-60",
    "18-64",
    "19+",
    "19-34",
    "19-59",
    "19-65",
    "2-5",
    "20+",
    "20-29",
    "20-59",
    "26-59",
    "29-60",
    "3-5",
    "30-59",
    "34-49",
    "35-49",
    "4-19",
    "4-5",
    "5+",
    "5-11",
    "5-14",
    "5-17",
    "5-18",
    "5-9",
    "50",
    "50+",
    "50-70",
    "56+",
    "59+",
    "6-11",
    "6-12",
    "6-17",
    "6-18",
    "60+",
    "61+",
    "65+",
    "70+",
    "71+",
    "adults",
    "aged people",
    "all",
    "boys",
    "children",
    "children of school-going age",
    "disables",
    "elderly",
    "girls",
    "infants",
    "kids",
    "living with disabilities",
    "minors",
    "needing medical assistance",
    "not working age (excluding pensioners)",
    "pensioners",
    "pregnant women",
    "unaccompanied minors",
    "women",
    "working age",
    "youngs",
    "youth",
]
