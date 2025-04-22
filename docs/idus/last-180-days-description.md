**Parameters:** This end point does not have parameters

**Fields description**:

| Label | API field name | Definition |
|-------|----------------|------------|
| Id | id | IDMC figure unique identifier. |
| Country | country | Short name of the country or territory. |
| Iso3 | iso3 | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Latitude | latitude | Geographic coordinate in decimal degrees (latitude). |
| Longitude | longitude | Geographic coordinate in decimal degrees (longitude). |
| Centroid | centroid | Geographical center point of the data's location. |
| Role | role | The field of data delineates the most reliable figure accessible as determined by the primary data source, the methodology employed in data collection, the scope of coverage, and the promptness of the reported information. This framework is essential in understanding two key types of figures:<br>**Recommended Figure:** This is the figure that has been identified with the highest level of confidence or robustness to represent the population flow. It is selected based on thorough evaluation and is recommended for inclusion in our official estimates for a specific event. Such figures are crucial as they can be aggregated to facilitate detailed analysis. The role of a figure can change over time. As new data becomes available, a figure that was once a "Recommended Figure" may become outdated and be reclassified as a "Triangulation Figure".<br>**Triangulation Figure:** For the purposes of the IDU dataset, these entries represent often the first estimates of the magnitude of a displacement situation. These are provisional estimates reflect various updates regarding displacement situations. They are utilized until a more solid or robust estimate becomes available, especially as more data is gathered by local primary data sources. |
| Displacement_type | displacement_type | Identifies the trigger of displacement such as conflict or disasters. |
| Conflict | conflict | New displacements due to conflict and violence (Color code: #EF7D04). |
| Disasters | disasters | New displacements due to natural hazards (Color code: #008ECA). |
| Qualifier | qualifier | Indicates the level of uncertainty or accuracy associated with the figure. |
| Figure | figure | Total number of internal displacements (flows). |
| Displacement_date | displacement_date | Initial date when the displacement flow began. |
| Displacement_Start_date | displacement_start_date | Approximate date when the displacement flow started. |
| Displacement_end_date | displacement_end_date | Approximate date when the displacement flow ended. |
| Year | year | Year in which the displacement occurred. |
| Event_id | event_id | Unique identifier for events as assigned by IDMC. |
| Event_name | event_name | This field includes the event's coded name which is based on the country, type of hazard, location, and start date. It also incorporates the common or official name of the event when available. |
| Event_start_date | event_start_date | Date when the event or hazard began. |
| Event_end_date | event_end_date | Date when the event or hazard concluded. |
| Category | category | Natural Hazard category that triggered displacement based on the IRDR Peril Classification and Hazard Glossary. |
| Subcategory | subcategory | Hazard category based on the CRED EM-DAT classification. |
| Type | type | Hazard type as categorized by CRED EM-DAT. |
| Subtype | subtype | Specific sub-type of the hazard based on the CRED EM-DAT. |
| Standard_popup_text | standard_popup_text | Standard text from the IDMC website for the data entry. |
| Standard_info_text | standard_info_text | Additional standard information provided by IDMC. |
| Old_Id | old_id | Legacy identifier for the data entry. |
| Sources | sources | This field lists the names of the primary data providers or the original sources for the internal displacement data reported by IDMC. |
| Source_url | source_url | URL of the source reported. |
| Locations_name | locations_name | This field indicates the names of locations where displacement incidents have been reported. It's important to note that this field may exhibit a many-to-one relationship signifying that multiple location names could be associated with a single reported figure preventing disaggregation by individual location. This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) software may interpret these multi-point entities as single data points, potentially leading to the inadvertent double-counting of figures. To mitigate this issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of locations or distributing the "Total figures" values based on a weighting factor such as population density. This ensures a more accurate representation of the displacement data across individual locations and prevents duplication of figures during analysis. |
| Locations_coordinates | locations_coordinates | This field contains geographic coordinates representing the reported locations. Please note that this field contains multipoints, meaning that multiple locations may represent one figures. It's important to note that this field may exhibit a many-to-one relationship signifying that multiple location names could be associated with a single reported figure preventing disaggregation by individual location. This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) software may interpret these multi-point entities as single data points, potentially leading to the inadvertent double-counting of figures. To mitigate this issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of locations or distributing the "Total figures" values based on a weighting factor such as population density. This ensures a more accurate representation of the displacement data across individual locations and prevents duplication of figures during analysis. |
| Locations_accuracy | locations_accuracy | This field indicates the estimated precision of the reported locations. It serves as a clue to the likely administrative unit level (e.g. country, state, district) used for reporting. |
| Locations_type | locations_type | This field specifies the type of displacement location within a reported event. It can indicate:<br>**Origin:** The place where people were displaced from.<br>**Destination:** The location where displaced people arrived.<br>**Both:** In some cases both origin and destination information might be included.<br>It's crucial to note that different locations reported for a single figure may pertain to both the origin and destination of displacement incidents. This distinction is particularly salient in geospatial analysis where Geographic Information System (GIS) software may interpret these multi-point entities as singular data points potentially resulting in inadvertent double-counting of figures. To mitigate this issue, it is recommended to preprocess the dataset prior to GIS analysis to ensure accurate representation and avoid duplication of figures. |
| Displacement_occurred | displacement_occurred | This field contains values that represent if preventive evacuations were reported. These evacuations are the result of existing early warning systems. |
| Created_at | created_at | Date when the data entry was created. |
