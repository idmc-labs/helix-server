This dataset provides the most up-to-date estimates of new occurrences of internal displacement triggered by conflicts and disasters. It encompasses data on internal displacements (or population movements) which are obtained through event-based monitoring. The IDU figures are likely to change over time as more information is available. Curated figures are published as part of the GIDD dataset.

| Field                         | Description |
|-------------------------------|-------------|
| ID                            | IDMC figure unique identifier. |
| Country / Territory           | Short name of the country or territory. |
| ISO3                          | Represents the ISO 3166-1 alpha-3 code. The code 'AB9' is assigned to the Abyei Area. |
| Latitude                      | Geographic coordinate in decimal degrees (latitude). |
| Longitude                     | Geographic coordinate in decimal degrees (longitude). |
| Centroid                      | Geographical center point of the data's location. |
| Role                          | The field of data delineates the most reliable figure accessible as determined by the primary data source, the methodology employed in data collection, the scope of coverage, and the promptness of the reported information. This framework is essential in understanding two key types of figures: Recommended Figure: This is the figure that has been identified with the highest level of confidence or robustness to represent the population flow. It is selected based on thorough evaluation and is recommended for inclusion in our official estimates for a specific event. Such figures are crucial as they can be aggregated to facilitate detailed analysis. The role of a figure can change over time. As new data becomes available, a figure that was once a “Recommended Figure” may become outdated and be reclassified as a “Triangulation Figure”. Triangulation Figure: For the purposes of the IDU dataset, these entries represent often the first estimates of the magnitude of a displacement situation. These are provisional estimates reflect various updates regarding displacement situations. They are utilized until a more solid or robust estimate becomes available, especially as more data is gathered by local primary data sources. |
| Displacement type             | Identifies the trigger of displacement such as conflict or disasters. |
| Qualifier                     | Indicates the level of uncertainty or accuracy associated with the figure. |
| Figure                        | Total number of internal displacements (flows). |
| Displacement date             | Initial date when the displacement flow began. |
| Displacement start date       | Approximate date when the displacement flow started. |
| Displacement end date         | Approximate date when the displacement flow ended. |
| Year                          | Year in which the displacement occurred. |
| Event ID                      | Unique identifier for events as assigned by IDMC. |
| Event name                    | This field includes the event's coded name, which is based on the country, type of hazard, location, and start date. It also incorporates the common or official name of the event, when available. |
| Event codes (Code:Type)       | Unique codes such as the GLIDE number and other database-specific codes used to identify and track specific events across various databases. |
| Event codes types             | Types of unique codes such as the GLIDE number and other database-specific identifiers used to track events. |
| Event start date              | Event or hazard start date. |
| Event end date                | Event or hazard end date. |
| Category                      | Natural Hazard category that triggered displacement based on the IRDR Peril Classification and Hazard Glossary. |
| Sub category                  | Hazard category based on the CRED EM-DAT classification. |
| Type                          | Hazard type as categorized by CRED EM-DAT. |
| Sub-Type                      | Specific sub-type of the hazard based on CRED EM-DAT. |
| Standard popup text           | Standard text from the IDMC website for the data entry. |
| Standard info text            | Additional standard information provided by IDMC. |
| Old id                        | Legacy identifier for the data entry. |
| Sources                       | This field lists the names of the primary data providers or the original sources for the internal displacement data reported by IDMC. |
| Source url                    | URL of the source reported. |
| Locations name                | This field indicates the names of locations where displacement incidents have been reported. It's important to note that this field may exhibit a many-to-one relationship, signifying that multiple location names could be associated with a single reported figure, preventing disaggregation by individual location. This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) software may interpret these multi-point entities as single data points, potentially leading to the inadvertent double-counting of figures. To mitigate this issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of locations or distributing the "Total figures" values based on a weighting factor such as population density. This ensures a more accurate representation of the displacement data across individual locations and prevents duplication of figures during analysis. |
| Locations coordinates         | This field contains geographic coordinates representing the reported locations. Please note that this field contains multipoints meaning that multiple locations may represent one figure. It's important to note that this field may exhibit a many-to-one relationship, signifying that multiple location names could be associated with a single reported figure, preventing disaggregation by individual location. This becomes particularly relevant in geospatial analysis, where Geographic Information System (GIS) software may interpret these multi-point entities as single data points, potentially leading to the inadvertent double-counting of figures. To mitigate this issue, it's advisable to preprocess the dataset by either dividing the total figure by the number of locations or distributing the "Total figures" values based on a weighting factor such as population density. This ensures a more accurate representation of the displacement data across individual locations and prevents duplication of figures during analysis. |
| Locations accuracy            | This field indicates the estimated precision of the reported locations. It serves as a clue to the likely administrative unit level (e.g. country, state, district) used for reporting. |
| Locations type                | This field specifies the type of displacement location within a reported event. It can indicate:<br>- **Origin:** The place where people were displaced from.<br>- **Destination:** The location where displaced people arrived.<br>- **Both:** In some cases, both origin and destination information might be included.<br>It's crucial to note that different locations reported for a single figure may pertain to both the origin and destination of displacement incidents. This distinction is particularly salient in geospatial analysis, where Geographic Information System (GIS) software may interpret these multi-point entities as singular data points, potentially resulting in inadvertent double-counting of figures. To mitigate this issue, it is recommended to preprocess the dataset prior to GIS analysis to ensure accurate representation and avoid duplication of figures. |
| Displacement occurred         | This field contains values that represent if preventive evacuations were reported. These evacuations are the result of existing early warning systems. |
| Created at                    | Date when the data entry was created. |

Figures from the IDU may differ from GIDD estimates.

### Caveats and Limitations

- These figures depict reported internal displacement flows and may change as displacement situations evolve and more information emerges. For curated and validated estimates refer to the Global Internal Displacement Database (GIDD) accessible at GIDD: https://www.internal-displacement.org/database/displacement-data/. The IDU dataset provides the most recent updates on internal displacement events (population flows).
- **Important considerations:** When analyzing the IDU data, it's imperative to exercise caution in certain situations. Specifically, if multiple IDU entries share identical flow dates, eventID, and locations, we advise against summing up the figures. This is because such data might represent varying estimates of population flows rather than distinct population movements. This distinction is crucial to avoid misinterpretation of the data and ensure accurate representation of displacement situations. Hence, please include the following preprocessing considerations per event, i.e. after grouping the figures per "eventID", in the analysis:
    - **Prioritization of figures:** For any given event with multiple updates, it is imperative to utilize the “Recommended figure” over “Triangulation figure” whenever these are available. This approach ensures the most accurate reflection of the total number of internal displacements resulting from the event.
    - **Aggregating recommended figures:** When encountering multiple recommended figures, per event aggregation is possible even if they come from different locations with identical flow, as these figures represent disaggregated data. Figures pertaining to the same location can also be aggregated. Such cases are often reported when the names of settlements cannot be located in IDMC geocoders. In these scenarios, analysts will refer to the last well-known higher administrative unit, although the data actually describes disaggregated figures within this higher unit. In these instances, the “Standard_popup_text” field will include the settlement name.
    - **Triangulation figures with same locations:** In the absence of recommended figures and when multiple triangulation figures exist for the same location for an event, only the most recently updated figure should be used. This recommendation is made to avoid the risk of double counting and is based on the assumption that the latest update offers a more comprehensive estimate than earlier ones.
    - **Triangulation figures with different locations:** For an event, in the absence of recommended figures and the presence of multiple triangulation figures sharing the same flow dates but referring to different locations, these figures are to be combined. This method enables the representation of the total number of internal displacements arising from an event across various locations.


### Code sample to read and export the IDU API as a geojson file for GIS applications

1. Create and save the Python script in a file, navigate to its directory in a terminal, run it with `python export_geojson.py`, and check for the `IDMC_IDU.geojson` output.
   ```python
   import requests
   import json

   # URL of the JSON API
   url = "LINK TO THE API END POINT"

   response = requests.get(url).json()  # Assumes successful response and valid JSON

   geojson = {
       "type": "FeatureCollection",
       "features": [{
           "type": "Feature",
           "properties": {k: v for k, v in item.items() if k != "latitude" and k != "longitude"},
           "geometry": {"type": "Point", "coordinates": [item["longitude"], item["latitude"]]}
       } for item in response]
   }

   # Define the path where you want to save the file
   # Adjust the path as needed for your specific requirements
   file_path = "C:\\path\\to\\your\\folder\\IDMC_IDU.geojson"  # Update this path for windows environments
   # file_path = "/path/to/your/folder/displacements.geojson"  # Update this path for Linux/MacOS environments


   with open(file_path, "w") as f:
       f.write(json.dumps(geojson, indent=4))

   print("GeoJSON file created successfully.")
   ```
2. For QGIS, drag and drop the file into QGIS.
3. For ArcGIS Pro, use the JSON to Features tool to read the geojson file and open it as a shapefile.
