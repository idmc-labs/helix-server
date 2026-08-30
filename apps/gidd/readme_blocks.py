"""Shared README prose for the GIDD exports.

Four exports ship a README describing the same database, so the preamble is assembled here
once and parameterised where an export legitimately says something different about itself --
which cause it covers, which sheets it carries, how it should be cited. The GeoJSON dump
carries the same text as a single string; `rows_to_text` renders the row form for it.
"""

import typing

Rows = typing.List[typing.List[str]]

SOURCE_ROW = "SOURCE: Internal Displacement Monitoring Centre (IDMC)"
CONTACT_ROW = "CONTACT: ch.datainfo@idmc.ch"

CITATION_URL = "https://www.internal-displacement.org/database/displacement-data/"

DATABASE_NAME = "Global Internal Displacement Database"
DATABASE_NAME_DISASTERS = "Global Internal Displacement Database - Disasters"


# --- description ---------------------------------------------------------------------------

MONITORING_PARAGRAPH = (
    "The Internal Displacement Monitoring Centre (IDMC) monitors internal displacement events globally, "
    "triggered by disasters, conflict, and other forms of violence. It gathers and analyses both "
    "structured and unstructured secondary data from diverse sources—including government agencies, "
    "UN agencies, the International Federation of the Red Cross and Red Crescent, and the media."
)

TRIANGULATION_PARAGRAPH = (
    "IDMC analysts rigorously analyse and triangulate all reported data. The data undergo thorough quality "
    "control processes, involving engagement with primary data collectors for peer review and validation. "
    "This meticulous approach guarantees that the data reported by IDMC reflects high accuracy."
)

VALIDATION_PARAGRAPH = (
    "The data in the Global Internal Displacement Database (GIDD) is annually validated and peer-reviewed, "
    "having passed through various quality control processes in consultation with different UN agencies, "
    "goverments and local data providers."
)

PERIOD_PARAGRAPH = (
    "The GIDD database documents displacement due to conflict from 2009 to 2023 and disaster-induced "
    "displacement from 2008 to 2023. For detailed definitions and more comprehensive descriptions, please "
    "refer to the IDMC Monitoring Tools (https://www.internal-displacement.org/monitoring-tools)."
)


def description_rows() -> Rows:
    return [
        [MONITORING_PARAGRAPH],
        [],
        [TRIANGULATION_PARAGRAPH],
        [],
        [VALIDATION_PARAGRAPH],
        [],
        [PERIOD_PARAGRAPH],
    ]


# --- key definitions -----------------------------------------------------------------------

DEFINITION_FLOWS = (
    "Internal Displacements (flows): This metric represents the number of internal displacements, or "
    "internal displacement population flows, reported from January 1st to December 31st of a reporting year. "
    "This figure may include individuals who are displaced multiple times during the year by different events."
)

DEFINITION_IDPS = (
    "Total number of Internally Displaced Persons (IDPs) (stocks): This metric represents the total number "
    "of people living in situations of internal displacement as of the end of the reporting year, "
    "specifically on December 31st of each year."
)

DEFINITION_CONFLICT_DISPLACEMENT = (
    "Conflict displacement: Refers to situations where people are forced to leave their homes or places of "
    "habitual residence as a result or in order to avoid the impact of armed conflict, communal violence "
    "and criminal violence."
)

DEFINITION_DISASTER_DISPLACEMENT = (
    "Disaster displacement: Refers to situations where people are forced to leave their homes or places of "
    "habitual residence as a result, or in anticipation of the negative impact of natural hazards."
)

DEFINITION_DISASTER = (
    "Disaster: A serious disruption of the functioning of a community or a society involving widespread "
    "human, material, economic or environmental losses and impacts, which exceeds the ability of the "
    "affected community or society to cope using its own resources (UNSDR)."
)


def definition_rows(covers_conflict: bool = True) -> Rows:
    """The metric and trigger definitions, minus any trigger the export does not report."""
    return [
        [DEFINITION_FLOWS],
        [DEFINITION_IDPS],
        *([[DEFINITION_CONFLICT_DISPLACEMENT]] if covers_conflict else []),
        [DEFINITION_DISASTER_DISPLACEMENT],
        [DEFINITION_DISASTER],
    ]


# --- licence, coverage, citation -----------------------------------------------------------

LICENSE_ROW = (
    "USE LICENSE: This content is licensed under CC BY-NC. Detailed licensing information is available at "
    "Creative Commons License (See: https://creativecommons.org/licenses/by-nc/4.0/)."
)

# Bounded, not open-ended: every export ships from one release, so each states the same end year.
COVERAGE_ALL_CAUSES = (
    "COVERAGE: Global. The GIDD provides data on internal displacement caused by conflict from 2009 "
    "through 2024, covering both internal displacements (flows) and the total number of IDPs (stocks). "
    "Data on internal displacements triggered by disasters dates back to 2008 and runs through 2024; "
    "the metrics on the total number of IDPs from disaster-related events are available from 2019 "
    "through 2024."
)

COVERAGE_DISASTERS_ONLY = (
    "COVERAGE: Global. The GIDD provides data on internal displacements triggered by disasters dating back "
    "to 2008 and running through 2024; the metrics on the total number of IDPs from disaster-related "
    "events are available from 2019 through 2024."
)


def citation_row(database: str = DATABASE_NAME) -> str:
    return (
        "All derived work from IDMC data could cite IDMC following this example: Internal Displacement "
        f"Monitoring Centre. {database}. IDMC (2026). Available at: "
        f"{CITATION_URL} (Accessed: [date of access])."
    )


def preamble_block(
    title: str,
    filename: str,
    extracted_on: str,
    last_update: str,
    description: Rows,
    definitions: Rows,
    coverage: str,
    license_row: str = LICENSE_ROW,
    citation: typing.Optional[str] = None,
    version: typing.Optional[str] = None,
) -> Rows:
    """Everything from TITLE down to CONTACT, in the order every GIDD README publishes it."""
    return [
        [f"TITLE: {title}"],
        [],
        [f"FILENAME: {filename}"],
        [],
        [SOURCE_ROW],
        [],
        [f"DATE EXTRACTED: {extracted_on}"],
        [],
        [f"LAST UPDATE: {last_update}"],
        [],
        *([[f"README VERSION: {version}"], []] if version else []),
        ["DESCRIPTION:"],
        *description,
        [],
        ["KEY DEFINITIONS:"],
        [],
        *definitions,
        [],
        [license_row],
        [],
        [coverage],
        [],
        ["CITATION:"],
        [citation or citation_row()],
        [],
        [CONTACT_ROW],
    ]


def data_description_block(name: str) -> Rows:
    """The heading that introduces the field list for one sheet of the workbook."""
    return [[], [f"DATA DESCRIPTION: {name}"], []]


# --- displacement export, README version 4 --------------------------------------------------
#
# Version 4 revised the prose above for this export alone: it reports through 2024, states the
# year-end rule behind the annual IDPs total, and documents the API. Its changelog sheet tracks
# the wording, so the revisions live here rather than being folded into the shared text.

DISPLACEMENT_DESCRIPTION = (
    "The Internal Displacement Monitoring Centre (IDMC) monitors internal displacement events globally, "
    "triggered by disasters, conflict, and other forms of violence. It gathers and analyses both structured "
    "and unstructured secondary data from diverse sources - including government agencies, UN agencies, the "
    "International Federation of the Red Cross and Red Crescent, and the media.\n"
    "\n"
    "IDMC analysts rigorously analyse and triangulate all reported data. The data undergo thorough quality "
    "control processes, involving engagement with primary data collectors for peer review and validation. "
    "This meticulous approach guarantees that the data reported by IDMC reflects high accuracy.\n"
    "\n"
    "The data in the Global Internal Displacement Database (GIDD) is annually validated and peer-reviewed, "
    "having passed through various quality control processes in consultation with different UN agencies, "
    "governments and local data providers.\n"
    "\n"
    "The GIDD database documents displacement due to conflict from 2009 to 2024 and disaster-induced "
    "displacement from 2008 to 2024. For detailed definitions and more comprehensive descriptions, please "
    "refer to the IDMC Monitoring Tools (https://www.internal-displacement.org/monitoring-tools).\n"
    "\n"
    "This page provides guidance on obtaining access, using the API, and understanding IDMC's data structure. "
    "To request an API key, please email ch.datainfo@idmc.ch with a brief description of your intended use. "
    "For detailed specifications, including data models, field definitions, and usage examples, consult the "
    "IDMC API Swagger documentation at https://helix-tools-api.idmcdb.org/external-api/."
)

DISPLACEMENT_DEFINITIONS: Rows = [
    [
        "Internal Displacements (flows): The number of internal displacements, or "
        "population flows, reported from January 1st to December 31st of a reporting year. "
        "May include individuals displaced multiple times during the year by different events."
    ],
    [
        "Total number of Internally Displaced Persons (IDPs) (stocks): The total number "
        "of people living in situations of internal displacement as of December 31st of each year. "
        "Operational rule: where multiple stock-reporting dates exist within a year, "
        "only the December 31 (year-end) snapshot is used to compute the annual IDPs total, "
        "to avoid double-counting across in-year snapshots."
    ],
    [
        "Conflict displacement: Situations where people are forced to leave their homes or places of "
        "habitual residence as a result, or in order to avoid the impact of armed conflict, communal violence "
        "and criminal violence."
    ],
    [
        "Disaster displacement: Situations where people are forced to leave their homes or places of "
        "habitual residence as a result, or in anticipation, of the negative impact of natural hazards."
    ],
    [DEFINITION_DISASTER],
]

DISPLACEMENT_LICENSE_ROW = (
    "USE LICENSE: This content is licensed under CC BY-NC. See: https://creativecommons.org/licenses/by-nc/4.0/."
)


DISAGGREGATION_FIELD_ROWS: Rows = [
    ["ID: IDMC figure unique identifier."],
    ["ISO3: Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area."],
    ["Country / Territory: Short name of the country or territory."],
    ["Geographical region: Corresponds to IDMC's geographical regions."],
    ["Figure cause: Identifies the trigger of displacement, such as conflict or disasters."],
    ["Year: Indicates the year for which displacement data are reported."],
    [
        "Figure category: Categorizes the type of displacement metric. It details values for Internal "
        "Displacements (internal displacement flows) and Total Number of IDPs (internal displacement stocks), "
        "as defined earlier in this document."
    ],
    [
        "Total figures: Represents the total number of internal displacements or IDPs. For internal "
        "displacements, units are recorded as 'internal displacement flows' or 'internal displacement "
        "movements'. For the total number of IDPs, units reflect the total number of people living in displacement."
    ],
    [
        "Reported figures: This field represents the values reported by the original source. Figures can be "
        "reported either in terms of households or individual counts."
    ],
    [
        "Figure unit: This field specifies the type of unit reported in the 'Reported' column. Possible values "
        "include 'households' or 'people'. The category people includes 'internal displacement flows' or 'internal"
        " displacement movements'."
    ],
    [
        "Household size: This metric represents the average number of individuals per household. It is "
        "calculated using data from various sources, including the United Nations Department of Economic and "
        "Social Affairs (UNDESA), national statistical offices, and estimates from local primary data providers "
        "shared with IDMC."
    ],
    ["Hazard Category: Hazard category based on the CRED EM-DAT classification."],
    ["Hazard sub category: Hazard sub category based on the CRED EM-DAT classification."],
    ["Hazard Type: Hazard type as categorized by CRED EM-DAT."],
    ["Hazard Sub-Type: Specific sub-type of the hazard based on CRED EM-DAT."],
    ["Start date: Start date of displacement flow."],
    ["Start date accuracy: Uncertainty or accuracy of start date."],
    ["End date: End date of the displacement flow."],
    ["End date accuracy: Uncertainty or accuracy of end date."],
    [
        "Stock date: This field indicates the year in which the data for the IDP metric (total number of "
        "internally displaced persons or stocks) was collected."
    ],
    ["Stock date accuracy: Uncertainty or accuracy of stock date."],
    [
        "Stock reporting date: This field reflects the year IDMC uses to report the total number of internally "
        "displaced persons (IDPs). It represents the IDMC reporting year, which may not coincide with the "
        "actual data collection year. Given the protracted nature of displacement, annual updates on the total "
        "number of IDPs may not always be available. To maintain accuracy in reporting, IDMC relies on the "
        "most recent verified data until evidence shows that the displaced population has achieved a durable "
        "solution."
    ],
    ["Publishers: Organizations responsible for distributing and disseminating internal displacement data"],
    [
        "Sources: This field lists the names of the primary data providers or the original sources for the "
        "internal displacement data reported by IDMC."
    ],
    ["Sources type: This field categorizes the type of source as defined by IDMC."],
    ["Event ID: Unique identifier for events as assigned by IDMC."],
    [
        "Event name: This field includes the event's coded name, which is based on the country, type of hazard, "
        "location, and start date. It also incorporates the common or official name of the event, when available."
    ],
    ["Event cause: Identifies the trigger of displacement, such as conflict or disasters."],
    [
        "Event main trigger: This field identifies the primary hazard subtype or conflict type that initiated "
        "the event, serving as the main driver of a disaster or conflict. For disasters, associated fields such "
        'as "Hazard Category", "Hazard Subcategory", "Hazard Type", and "Hazard Sub-Type" detail the '
        "cascading impacts stemming from this main trigger. For instance, a tropical storm identified as the "
        'main driver of displacement might lead to reports in "Hazard Sub-Type" of floods, landslides, and '
        "other related disaster types arising from the initial hazard."
    ],
    ["Event start date: Event or hazard start date."],
    ["Event end date: Event or hazard end date."],
    ["Event start date accuracy: Uncertainty or accuracy of event start date."],
    ["Event end date accuracy: Uncertainty or accuracy of event end date."],
    [
        "Is housing destruction: This field indicates whether the displacement data includes individuals "
        'displaced by housing destruction. Values are "Yes" if the data reflects households whose homes were '
        'destroyed, and "No" otherwise. This field relies on the data specified in "Reported Figures" and '
        'is linked to the "Unit" of measurement used, which in this context refers to houses destroyed.'
    ],
    [
        "Violence type: This field categorizes the type of violence using IDMC's typology, which aligns with "
        "international classifications. The categories include\n"
        "- International Armed Conflict (IAC): Refers to armed conflict between two or more states.\n"
        "- Non-International Armed Conflict (NIAC): Refers to armed conflict occurring within the "
        "territory of a single state between its government and non-state armed groups, or between such groups "
        "themselves.\n"
        "- Unclear/Unknown: Indicates situations where the type of violence is not definitively categorized "
        "due to limited information.\n"
        "- Other situations of violence (OSV): Refers to cases of communal violence, civilian-state "
        "violence and crime-related violence."
    ],
    [
        "Event codes (Code:Type): Unique codes such as the GLIDE number and other database-specific codes used "
        "to identify and track specific events across various databases."
    ],
    [
        "Locations name: This field indicates the names of locations where displacement incidents have been "
        "reported. It's important to note that this field may exhibit a many-to-one relationship, signifying "
        "that multiple location names could be associated with a single reported figure, preventing "
        "disaggregation by individual location. This becomes particularly relevant in geospatial analysis, "
        "where Geographic Information System (GIS) software may interpret these multi-point entities as single "
        "data points, potentially leading to the inadvertent double-counting of figures. To mitigate this "
        "issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of "
        'locations or distributing the "Total figures" values based on a weighting factor such as population '
        "density. This ensures a more accurate representation of the displacement data across individual "
        "locations and prevents duplication of figures during analysis."
    ],
    [
        "Locations coordinates: This field contains geographic coordinates representing the reported locations. "
        "Please note that this field contains multipoints  meaning that multiple locations may represent one "
        "figure. It's important to note that this field may exhibit a many-to-one relationship, signifying "
        "that multiple location names could be associated with a single reported figure, preventing "
        "disaggregation by individual location. This becomes particularly relevant in geospatial analysis, "
        "where Geographic Information System (GIS) software may interpret these multi-point entities as single "
        "data points, potentially leading to the inadvertent double-counting of figures. To mitigate this "
        "issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of "
        'locations or distributing the "Total figures" values based on a weighting factor such as population '
        "density. This ensures a more accurate representation of the displacement data across individual "
        "locations and prevents duplication of figures during analysis."
    ],
    [
        "Locations accuracy: This field indicates the estimated precision of the reported locations. It "
        "serves as a clue to the likely administrative unit level (e.g. country, state, district) used for "
        "reporting."
    ],
    [
        "Locations type: This field specifies the type of displacement location within a reported event. It "
        "can indicate\n"
        "- Origin: The place where people were displaced from.\n"
        "- Destination: The location where displaced people arrived.\n"
        "- Both: In some cases, both origin and destination information might be included. It's crucial to "
        "note that different locations reported for a single figure may pertain to both the origin and "
        "destination of displacement incidents. This distinction is particularly salient in geospatial "
        "analysis, where Geographic Information System (GIS) software may interpret these multi-point entities "
        "as singular data points, potentially resulting in inadvertent double-counting of figures. To mitigate "
        "this issue, it is recommended to preprocess the dataset prior to GIS analysis to ensure accurate "
        "representation and avoid duplication of figures."
    ],
    [
        "Displacement occurred: This field contains values that represent if preventive evacuations were "
        "reported. These evacuations are the result of existing early warning systems."
    ],
]


def rows_to_text(rows: Rows) -> str:
    """Render README rows as the plain text the GeoJSON dump publishes.

    Revision tables carry one cell per column, so they are tab separated -- several country
    names contain a comma.
    """
    return "".join("\t".join(str(cell) for cell in row) + "\n" for row in rows)
