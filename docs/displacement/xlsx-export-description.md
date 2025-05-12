This endpoint provides quality-controlled, annually validated data on internal displacement due to conflicts and disasters.

| Field                                       | Description                                                                                                                                                                                            |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ISO3                                        | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area.                                                                                                                  |
| Name                                        | Short name of the country or territory.                                                                                                                                                                |
| Year                                        | Indicates the year for which displacement data are reported.                                                                                                                                           |
| Conflict Stock Displacement                 | Total number of IDPs (rounded figures at the national level), as a result of conflict and violence as of the end of the reporting year. Units are recorded as 'People'.                                 |
| Conflict Stock Displacement (Raw)           | Total number of IDPs (not rounded), as a result of conflict and violence as of the end of the reporting year. Units are recorded as 'People'.                                                           |
| Conflict Internal Displacements             | Total number of internal displacements reported (rounded figures at national level), as a result of conflict and violence over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements'. |
| Conflict Internal Displacements (Raw)       | Total number of internal displacements reported (not rounded), as a result of conflict and violence over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements'.                       |
| Disaster Internal Displacements             | Total number of internal displacements reported (rounded figures at national level), as a result of disasters over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements'.             |
| Disaster Internal Displacements (Raw)       | Total number of internal displacements reported (not rounded), as a result of disasters over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements'.                                   |
| Disaster Stock Displacement                 | Total number of IDPs (rounded figures at national level), as a result of disasters as of the end of the reporting year. Units are recorded as 'People'.                                                 |
| Disaster Stock Displacement (Raw)          | Total number of IDPs (not rounded), as a result of disasters as of the end of the reporting year. Units are recorded as 'People'.

This dataset provides contextual information and analysis documented by IDMC analysts. It captures flags related to methodology, caveats, sources, and challenges identified for each metric, reporting year, and country.

| Field                   | Description |
|-------------------------|-------------|
| ISO3                    | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Year                    | Indicates the year for which displacement data are reported. |
| Figure cause            | Identifies the trigger of displacement, such as conflict or disasters. |
| Figure category         | Categorizes the type of displacement metric. It details values for Internal Displacements (internal displacement flows) and Total Number of IDPs, (Internal displacement stocks) as defined earlier in this document. |
| Description             | Provides contextual information about the data, including sources and data limitations. It is essential for representing the analysis conducted by IDMC analysts. This field also details the methodology used, descriptions of sources, and outlines any caveats and challenges identified with the displacement figures reported. |
| Figures                 | Represents the total number of internal displacements or IDPs. For internal displacements, units are recorded as 'internal displacement flows' or 'internal displacement movements'. For the total number of IDPs, units reflect the total number of people living in displacement. |
| Figures rounded         | Displays rounded figures to provide a simplified view of the data that matches the figures reported in the Global Report on Internal Displacement (GRID). |

Sex and Age Disaggregated Data (SADD) for displacement associated with conflict or disasters is often scarce. One way to estimate it is to use SADD available at the national level. IDMC employs United Nations Population Estimates and Projections to break down the number of internally displaced people by sex and age. The methodology and limitations of this approach are described on IDMC’s website at: https://www.internal-displacement.org/monitoring-tools

| Field | Description |
|-------|-------------|
| ISO3 | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Country | Short name of the country or territory. |
| Year | The year for which displacement figures are reported. |
| Sex | This field contains information on Female, Male, and Both Sexes categories following the United Nations Department of Economic and Social Affairs (UN DESA) classifications. |
| Cause | Identifies the trigger of displacement, such as conflict or disasters. |
| Age_0_4 | Represents the age cohort from newborns to 4 years old. |
| Age_5_11 | Represents children aged 5 to 11 years. |
| Age_12_17 | Represents adolescents aged 12 to 17 years. |
| Age_18_59 | Represents adults aged 18 to 59 years. |
| Age_60_plus | Represents the population aged 60 years and older. |

