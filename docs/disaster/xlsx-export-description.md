**Fields description**:

| Label (Excel file)                  | API field name         | Definition |
|------------------------------------|-------------------------|------------|
| ISO3                               | iso3                    | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Country / Territory                | country_name            | Short name of the country or territory. |
| Year                               | year                    | Indicates the year for which displacement data are reported. |
| Event Name                         | event_name              | Common or official event name for the event if available. Otherwise events are coded based on the country type of hazard location and event start date. |
| Date of Event (Start)              | start_date              | Approximated start date of the event. |
|                           | start_date_accuracy     | This field describes the potential timeframe within which the event likely occurred. The values indicate the period around the date. |
|                           | end_date                | Approximated end date of the event. |
|                           | end_date_accuracy       | This field describes the potential timeframe within which the event likely ended. The values indicate the period around the date. |
| Disaster Internal Displacements    | new_displacement_rounded| Total number of internal displacements reported (rounded figures at national level) as a result of disasters over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements.' |
| Disaster Internal Displacements raw| new_displacement        | Total number of internal displacements reported (not rounded) as a result of disasters over the reporting year. Units are recorded as 'internal displacement flows' or 'internal displacement movements.' |
| Hazard Category                    | hazard_category         | Hazard category based on the CRED EM-DAT classification. |
| Hazard Type                        | hazard_type             | Hazard type as categorized by CRED EM-DAT. |
| Hazard Sub-Type                    | hazard_sub_type         | Specific sub-type of the hazard based on the CRED EM-DAT classification. |
| Event Codes (Code                  | event_codes             | Unique codes such as the GLIDE number and other database-specific codes used to identify and track specific events across various databases. |
| Event ID                           |                | Unique identifier for events as assigned by IDMC. |
| Displacement Occurred              |                | This field contains values that represent if preventive evacuations were reported. These evacuations are the result of existing early warning systems. |
