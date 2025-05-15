This dataset provides the most up-to-date estimates of new occurrences of internal displacement triggered by conflicts and disasters. It encompasses data on internal displacements (or population movements) which are obtained through event-based monitoring. The IDU figures are likely to change over time as more information is available. Curated figures are published as part of the GIDD dataset.

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
