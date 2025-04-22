This dataset provides contextual information and analysis documented by IDMC analysts. It captures flags related to methodology, caveats, sources, and challenges identified for each metric, reporting year, and country.

**Fields description:**
| Label (Excel file)      | API field name (JSON)      | Definition |
|-------------------------|----------------------------|------------|
| ISO3                    | iso3                       | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Year                    | year                       | Indicates the year for which displacement data are reported. |
| Figure cause            | Figure_Cause_Name          | Identifies the trigger of displacement such as conflict or disasters. |
| Figure category         | Figure_Category_Name       | Categorizes the type of displacement metric. It details values for "Internal Displacements" (internal displacement flows) and Total Number of IDPs, "Total number of IDPs" as defined earlier in this document. |
| Description             | description                | Provides contextual information about the data including sources and data limitations. It is essential for representing the analysis conducted by IDMC analysts. This field also details the methodology used, descriptions of sources, and outlines any caveats and challenges identified with the displacement figures reported. |
| Figures                 | figures                    | Represents the total number of internal displacements or IDPs. For internal displacements, units are recorded as 'internal displacement flows' or 'internal displacement movements.' For the total number of IDPs, units reflect the total number of people living in displacement. |
| Figures rounded         | figures_rounded            | Displays rounded figures to provide a simplified view of the data that matches the figures reported in the Global Report on Internal Displacement (GRID). |
