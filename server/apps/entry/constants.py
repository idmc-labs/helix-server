# These will initialize the figure types and sub types
STOCK = 'Stock'
FLOW = 'Flow'

IDP = 'IDP'
RETURNEES = 'Returnees'
LOCALLY_INTEGRATED_IDPS = 'Locally Integrated IDPs'
IDPS_SETTLED_ELSEWHERE = 'IDPs Settled Elsewhere'
PEOPLE_DISPLACED_ACROSS_BORDERS = 'People displaced across borders'
NEW_DISPLACEMENT = 'New Displacement'
MULTIPLE_DISPLACEMENT = 'Multiple Displacement'

FIGURE_TYPE_SUB_TYPES = {
    STOCK: [IDP, RETURNEES, LOCALLY_INTEGRATED_IDPS, IDPS_SETTLED_ELSEWHERE,
            PEOPLE_DISPLACED_ACROSS_BORDERS],
    FLOW: [NEW_DISPLACEMENT, MULTIPLE_DISPLACEMENT]
}
