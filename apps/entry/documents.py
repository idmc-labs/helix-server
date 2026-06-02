readme_data_raw = [
    ("ID", "Unique identifier"),
    ("Old ID", "Legacy ID from Helix 1.0"),
    ("Created at", "Data of creation of the figure"),
    ("Updated at", "Data of update of the figure"),
    ("ISO3", 'ISO 3166-1 alpha-3. The ISO3 "AB9" was assigned to the Abyei Area'),
    ("Country", "Country's or territory short name"),
    ("Centroid", "Country's centroid"),
    ("Lat", "Country's Lat in decimal degrees"),
    ("Lon", "Country's Lon in decimal degrees"),
    ("Region", "IDMC regions"),
    ("Geographical region", "IDMC geographical regions"),
    (
        "Figure cause",
        "Cause or main driver of displacement:  Conflict: New displacements"
        " due to conflict and other forms of violence. (colour code:  #EF7D04. Disasters:"
        " New displacements due to natural hazards (colour code: #008ECA)",
    ),
    ("Year", "Year of displacement"),
    ("Figure category", "Type of displacement metric"),
    (
        "Figure role",
        "Role of the figure. Recommended figures correspond to reporting"
        " figures while triangulation figures correspond to figures used for triangulation.",
    ),
    (
        "Total figures",
        "Total figures in terms of people. Ex. If a figure is reported in"
        " households we transform the figure into an estimated number of people by multipliying"
        " the rerported figure with the AHHS",
    ),
    ("Reported", "Reported figure. Figures can be reported in households of numbers of people"),
    ("Figure term", "Reported term used by the source of the figure"),
    ("Unit", "Unit of reporting. It can be households or people"),
    ("Quantifier", "Level of uncertainty or accuracy of the figure"),
    ("Household size", "Average household size. This values are comapiled by IDMC from UN and national sources."),
    ("Is housing destruction", "Housing destruction recommended figure (Yes/No)"),
    (
        "Displacement occurred",
        "Mark the time when displacement happened relative to the time of"
        " the displacement driver. Displacement can ocurr as a prevention mechanism before shock that"
        " drives displacement, during the shock or as a result of the shock.",
    ),
    ("Include in IDU", "Figure published as an Internal Displacement Update -I DU (Yes/No)"),
    ("Excerpt IDU", "IDU text"),
    ("Violence type", "Violence type as per IDMC methodology"),
    ("Violence sub type", "Violence sub type as per IDMC methodology"),
    ("OSV sub type", "OSV sub type as per IDMC methodology"),
    ("Context of violences", "Context of violences as per IDMC methodology"),
    ("Hazard category", "Hazard category as per EM-DAT definitions"),
    ("Hazard sub category", "Hazard sub category as per EM-DAT definitions"),
    ("Hazard type", "Hazard type as per EM-DAT definitions"),
    ("Hazard sub type", "Hazard sub type  as per EM-DAT definitions"),
    (
        "Other event sub type",
        "This category is selected when the driver of displacement"
        " is not clear or when it  represents multiple driver types.",
    ),
    ("Start date", "start date of displacement flow"),
    ("Start date accuracy", "uncertanty or accuracy of start date"),
    ("End date", "end date of thedisplacement flow"),
    ("End date accuracy", "uncertanty or accuracy of end date"),
    ("Stock date", "Stock date"),
    ("Stock date accuracy", "uncertanty or accuracy of stock date"),
    ("Stock reporting date", "Stock reporting date. This date correspond to the IDMC reporting period."),
    ("Analysis and calculation logic", "Description of the calculation of the figures"),
    ("Link", "Link of the figure"),
    ("Publishers", "Publisher of the figure"),
    ("Sources", "Source of the figure"),
    ("Sources type", "Type of source"),
    ("Sources reliability", "Reliability of the source "),
    ("Sources methodology", "Methodology used by the source of the figure"),
    ("Source excerpt", "Source excerpt"),
    ("Source url", "Source url"),
    ("Source document", "Link to the document uploaded to Helix"),
    ("Locations name", "Name of locations were displacement was reported"),
    ("Locations coordinates", "Coordinates of the locations reported"),
    ("Locations accuracy", "Accuracy of locations"),
    ("Locations type", "Type of locations"),
    ("Entry ID", "Entry ID"),
    ("Entry old ID", "Legacy ID from Helix 1.0"),
    ("Entry title", "Entry name"),
    ("Publication Date", "Entry publication date"),
    ("Confidential", "Is the entry confidential (Yes/No)"),
    ("Entry link", "Entry link"),
    ("Disability", "Has the dataset describes populations with disabilities (Yes/No)"),
    ("Indigenous people", "Has the dataset describes indigenous populations (Yes/No)"),
    ("Event ID", "Event ID"),
    ("Event old ID", "Legacy ID from Helix 1.0"),
    ("Event name", "Event name"),
    ("Event code", "Event or hazard unique identifiers. Ex. GLIDEnumber, FEMA ID, etc"),
    ("Event cause", "Cause or main driver of displacement event."),
    ("Event main trigger", "Event main hazard sub  type or conflict type"),
    ("Event start date", "Event or hazard start date"),
    ("Event end date", "Event or hazard end date date"),
    ("Event start date accuracy", "uncertanty or accuracy of event start date"),
    ("Event end date accuracy", "uncertanty or accuracy of event end date"),
    ("Event narrative", "Description of the event"),
    ("Crisis ID", "Crisis ID"),
    ("Crisis name", "Crisis name "),
    ("Tags", "Labels or tags that allow flagging different thematic areas."),
    (
        "Has age disaggregated data",
        "This toggle marks if the dataset has information on age or or gender disaggregated data",
    ),
    ("Revision progress", "Status of the revision progress"),
    ("Assignee", "Assignee responsible of the revision process"),
    ("Created by", "Name of the expert that created the entry"),
    ("Updated by", "Name of the last persone modifiying the entry"),
]

README_DATA = [{"column_name": column_name, "description": description} for column_name, description in readme_data_raw]


# --- Explode-by-locations Readme ---
#
# Built programmatically from `readme_data_raw` so that any future edit to a
# shared row description propagates to both default and explode Readmes.
_EXPLODE_DROPPED_COLUMN_NAMES = {
    "Centroid",
    "Lat",
    "Lon",
    "Locations name",
    "Locations coordinates",
    "Locations accuracy",
    "Locations type",
}

_TOTAL_FIGURES_REPEAT_SUFFIX = " Value is repeated across all rows belonging to the same figure."

_ALLOCATED_FIGURE_ROW = (
    "Allocated figure",
    "This location's share of `Total figures`, computed by equal division within the figure's"
    " locations of the same Location identifier. Integer remainder is distributed by Location ID ascending.",
)

_EXTRA_LOCATION_ROWS = [
    ("Location ID", "Unique identifier of the location."),
    ("Location", "Display name of the location."),
    ("Location lat, lng", "Location coordinates as 'latitude, longitude'."),
    ("Location accuracy", "Accuracy level of the location."),
    (
        "Location identifier",
        "Whether this row attributes the location as the Origin or Destination of the displacement."
        " A location originally tagged 'Origin and destination' produces two rows — one set to Origin,"
        " one to Destination.",
    ),
]

_EXPLODE_NOTE_ROWS = [
    (
        "About",
        "This file contains one row per (figure, location, identifier) combination. Each row attributes"
        " a share of a figure's displacement value to a specific location, distinguished by whether the"
        " location is an Origin or a Destination of the displacement.",
    ),
    (
        "Excluded figures",
        "Figures without any associated location are not included in this export. Figures with `Total figures`"
        " equal to 0 are also excluded. To see all figures regardless of locations, use the default figure export.",
    ),
    (
        "Allocation method",
        "`Allocated figure` is computed by dividing `Total figures` equally among the figure's locations of the"
        " same Location identifier (Origin or Destination). Because displacement counts must be whole numbers,"
        " the integer remainder is distributed by `Location ID` ascending — the first locations each receive one"
        " additional person until the remainder is exhausted.",
    ),
    (
        "Origin and destination locations",
        "A location whose underlying identifier is \"Origin and destination\" produces two rows for the same"
        " figure: one with `Location identifier` = `Origin` (counted in the origin allocation), and one with"
        " `Location identifier` = `Destination` (counted in the destination allocation).",
    ),
    (
        "Aggregating safely",
        "Summing `Allocated figure` over the entire sheet double-counts figures that have both origin and"
        " destination locations. To aggregate by identifier, filter `Location identifier` to a single value"
        " first. To compute the true grand total of displacement, group by `ID` and take any one row's"
        " `Total figures` per figure.",
    ),
    (
        "Asymmetric figures",
        "A figure with only origin locations contributes zero rows to a `Location identifier = Destination`"
        " aggregation (and vice versa). Per-identifier sums may therefore under-count the displacement total."
        " Use the `Total figures` column on any row to recover the figure's full value.",
    ),
]


def _build_readme_data_explode_raw():
    rows = []
    for column_name, description in readme_data_raw:
        if column_name in _EXPLODE_DROPPED_COLUMN_NAMES:
            continue
        if column_name == "Total figures":
            rows.append((column_name, description + _TOTAL_FIGURES_REPEAT_SUFFIX))
            rows.append(_ALLOCATED_FIGURE_ROW)
            continue
        rows.append((column_name, description))
    rows.extend(_EXTRA_LOCATION_ROWS)
    rows.append(("", ""))
    rows.extend(_EXPLODE_NOTE_ROWS)
    return rows


readme_data_explode_raw = _build_readme_data_explode_raw()

README_DATA_EXPLODE = [
    {"column_name": column_name, "description": description}
    for column_name, description in readme_data_explode_raw
]
