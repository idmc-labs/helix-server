This endpoints provides annually validated data on internal displacement caused by disasters, conflicts, and other situations of violence, as compiled and reported by IDMC.

| Field                                       | Description                                                                                                                                                                                            |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ISO3                                        | ISO 3166-1 alpha-3 code. AB9 = Abyei Area
| Name                                        | Short name of the country or territory.
| Year                                        | Year for which displacement data are reported.
| Conflict Stock Displacement                 | Total number of IDPs (rounded, national level), conflict and violence, end of reporting year. Units: People.
| Conflict Stock Displacement (Raw)           | Total number of IDPs (not rounded), conflict and violence, end of reporting year. Units: People.
| Conflict Internal Displacements             | Total internal displacements reported (rounded, national level), conflict and violence, over the reporting year. Units: flows / movements.
| Conflict Internal Displacements (Raw)       | Total internal displacements (not rounded), conflict and violence, over the reporting year. Units: flows / movements.
| Disaster Internal Displacements             | Total internal displacements reported (rounded, national level), disasters, over the reporting year. Units: flows / movements.
| Disaster Internal Displacements (Raw)       | Total internal displacements (not rounded), disasters, over the reporting year. Units: flows / movements.
| Disaster Stock Displacement                 | Total number of IDPs (rounded, national level), disasters, end of reporting year. Units: People.
| Disaster Stock Displacement (Raw)           | Total number of IDPs (not rounded), disasters, end of reporting year. Units: People.

This dataset provides contextual information and analysis documented by IDMC analysts. Captures flags related to methodology, caveats, sources, and challenges identified for each metric, reporting year, and country.

| Field                   | Description |
|-------------------------|-------------|
| ISO3                    | ISO 3166-1 alpha-3 code. AB9 = Abyei Area.
| Year                    | Year for which displacement data are reported.
| Figure cause            | Trigger of displacement: Conflict or Disaster.
| Figure category         | Type of metric: Internal Displacements (flows) or IDPs (stocks).
| Description             | Contextual information including sources, data limitations, methodology, and caveats.
| Figures                 | Total number of internal displacements or IDPs.
| Figures rounded         | Rounded figures matching values reported in the Global Report on Internal Displacement (GRID).

Sex and Age Disaggregated Data (SADD) is often scarce. IDMC employs UN Population Estimates and Projections to break down internally displaced people by sex and age. Methodology and limitations: https://www.internal-displacement.org/monitoring-tools

| Field     | Description |
|-----------|-------------|
| ISO3      |ISO 3166-1 alpha-3 code. AB9 = Abyei Area.
| Country	| Short name of the country or territory.
| Year	    | Year for which displacement figures are reported.
| Sex	    | Female / Male / Both Sexes (UN DESA classification).
| Cause	    | Trigger of displacement: Conflict or Disaster.
| Age 0-4	| Newborns to 4 years old.
| Age 5-11	| Children aged 5 to 11.
| Age 12-17	| Adolescents aged 12 to 17.
| Age 18-59	| Adults aged 18 to 59.
| Age 60+	| Population aged 60 and older.
