<h2 id="introduction">Introduction</h2>

IDMC provides APIs to make the data in our Global Internal Displacement Database (GIDD) and Internal Displacement Updates (IDU) directly available to developers and analysts. This page has detailed descriptions of the databases and how to use the APIs. For feedback or technical questions contact [ch.datainfo@idmc.ch](mailto:ch.datainfo@idmc.ch).

Our API documentation also includes widgets that allow users to embed data visualization products directly into their websites. Additionally, users can access datasets with various levels of geospatial disaggregation, along with contextual information detailing the sources, methodologies, and caveats associated with the figures reported by IDMC in the GIDD.

### Table of Contents

- [Introduction](#introduction)
- [Overview](#overview)
- [IDMC's main data products](#data-products)
- [Definitions](#definitions)
- [Accessing the API](#access-api)
- [Authentication](#authentication)
- [Caveats and limitations of the IDU dataset](#caveats)
- [Code sample to read and export the IDU API as a geojson file for GIS applications](#code-sample)
- [Widgets](#widgets)
- [General caveats and limitations of the datasets](#caveats-limitation")
- [Copy rights and citation of the data](#copyright")
- [Citation](#citation")
- [Support](#support")

<h2 id="overview">Overview of IDMC and the Global Internal Displacement Database (GIDD)</h2>

IDMC established the Global Internal Displacement Database (GIDD) which stands as the only harmonised global repository for data on internal displacement due to conflicts and disasters since 2008. IDMC work focuses on aggregating, curating, analyzing, and standardizing data from a diverse array of sources including United Nations agencies, governmental entities, and non-governmental organizations (NGOs).

While IDMC does not collect primary data directly, it leverages data from these primary collectors and various secondary sources such as media outlets to fill data gaps and provide a holistic view of internal displacement worldwide. Data from different formats, languages, and terminologies are harmonized and meticulously processed. Each figure reported in the GIDD undergoes a rigorous quality control process involving consultations and partnerships with primary data providers and key stakeholders in the monitored countries’ data ecosystems. Furthermore, our analysis and figures are regularly reviewed with different UN partners to ensure transparency and consistency in our reporting methodologies.

<h2 id="data-products">IDMC's main data products</h2>

IDMC offers two primary data products: the Global Internal Displacement Database (GIDD) and the Internal Displacement Updates (IDU) each catering to distinct needs and audiences:

- **[Global Internal Displacement Database (GIDD):](https://www.internal-displacement.org/database/displacement-data/)** This database is the product of an annual process that involves collecting, harmonizing, and validating data followed by a thorough peer review. We engage with primary data providers and relevant actors at various levels—national, regional, and global. Published annually, the GIDD has been acknowledged by several UN resolutions for its significance. The GIDD data is detailed by country and year for conflict-induced displacement, while disaster-induced displacement is recorded at the event level. Additional disaggregated data is also available since 2023.
- **[Internal Displacement Updates (IDU):](https://www.internal-displacement.org/internal-displacement-updates/)** IDMC's IDU offers preliminary, timely, and detailed insights into new displacement events reflecting our ongoing daily monitoring efforts. This event-based dataset provides initial snapshots of displacement trends which may later be refined and consolidated in the GIDD. It's important to note that these figures do not undergo the same level of quality control as the GIDD data, as the IDU data reflects timely updates that are subject to change as more information becomes available following a displacement event.
For further details on IDMC's methodology please visit our website or our [monitoring tools page](https://www.internal-displacement.org/monitoring-tools/).

This documentation will guide you through accessing and making the most of IDMC’s APIs, helping you to effectively integrate and utilize our data in your applications and analyses.

<h2 id="definitions">Definitions</h2>

- **Internally displaced persons (IDPs)**: Defined according to the [1998 Guiding Principles on Internal Displacement](https://www.internal-displacement.org/internal-displacement/guiding-principles-on-internal-displacement/) as people or groups of people who have been forced or obliged to flee or to leave their homes or places of habitual residence in particular as a result of armed conflict or to avoid the effects of armed conflict, situations of generalized violence, violations of human rights, or natural or human-made disasters, and who have not crossed an international border.
- **Internal Displacements (flows)**: Represents the number of internal displacements or internal displacement population flows reported from January 1st to December 31st of a reporting year. This figure may include individuals who are displaced multiple times during the year by different events.
- **Total number of Internally Displaced Persons (IDPs) (stocks)**: Represents the total number of people living in situations of internal displacement as of the end of the reporting year, specifically on December 31st of each year.
- **Conflict displacement**: Refers to situations where people are forced to leave their homes or places of habitual residence as a result or in order to avoid the impact of armed conflict and other situations of violence including communal violence, criminal violence and civilian-state violence.
- **Disaster displacement**: Refers to situations where people are forced to leave their homes or places of habitual residence as a result or in anticipation of the negative impact of natural hazards.
- **Disaster**: A serious disruption of the functioning of a community or a society involving widespread human, material, economic, or environmental losses and impacts which exceeds the ability of the affected community or society to cope using its own resources.

<h2 id="access-api">Accessing the API</h2>

In order to access the APIs, please request an API key by emailing [ch.datainfo@idmc.ch](mailto:ch.datainfo@idmc.ch). Briefly describe your intended use case for the data in your email. You will receive an API key via email.

<h2 id="authentication">Authentication</h2>

API requests require authentication through a `client_id` parameter (your API key). This parameter must be included in every request to access the data.

```bash 
GET https://helix-tools-api.idmcdb.org/external-api/gidd/displacements/?client_id=YOUR_API_KEY
```

<h2 id="caveats">Caveats and limitations of the IDU dataset</h2>

- These figures depict reported internal displacement flows and may change as displacement situations evolve and more information emerges. For curated and validated estimates refer to the Global Internal Displacement Database (GIDD) accessible at GIDD: https://www.internal-displacement.org/database/displacement-data/. The IDU dataset provides the most recent updates on internal displacement events (population flows).
- **Important considerations:** When analyzing the IDU data, it's imperative to exercise caution in certain situations. Specifically, if multiple IDU entries share identical flow dates, eventID, and locations, we advise against summing up the figures. This is because such data might represent varying estimates of population flows rather than distinct population movements. This distinction is crucial to avoid misinterpretation of the data and ensure accurate representation of displacement situations. Hence, please include the following preprocessing considerations per event, i.e. after grouping the figures per "eventID", in the analysis:
    - **Prioritization of figures:** For any given event with multiple updates, it is imperative to utilize the “Recommended figure” over “Triangulation figure” whenever these are available. This approach ensures the most accurate reflection of the total number of internal displacements resulting from the event.
    - **Aggregating recommended figures:** When encountering multiple recommended figures, per event aggregation is possible even if they come from different locations with identical flow, as these figures represent disaggregated data. Figures pertaining to the same location can also be aggregated. Such cases are often reported when the names of settlements cannot be located in IDMC geocoders. In these scenarios, analysts will refer to the last well-known higher administrative unit, although the data actually describes disaggregated figures within this higher unit. In these instances, the “Standard_popup_text” field will include the settlement name.
    - **Triangulation figures with same locations:** In the absence of recommended figures and when multiple triangulation figures exist for the same location for an event, only the most recently updated figure should be used. This recommendation is made to avoid the risk of double counting and is based on the assumption that the latest update offers a more comprehensive estimate than earlier ones.
    - **Triangulation figures with different locations:** For an event, in the absence of recommended figures and the presence of multiple triangulation figures sharing the same flow dates but referring to different locations, these figures are to be combined. This method enables the representation of the total number of internal displacements arising from an event across various locations.

<h2 id="widgets">Widgets</h2>

IDMC offers widgets that can be embedded into websites to display displacement data. These widgets are configurable and can be tailored to show specific data subsets.


<h3 id="conflict-widget">Conflict Widget</h3>

- Visualizes internal displacements and the total number of IDPs by country and year.
- Use parameter `page=conflict-widget` to select this widget
- **Parameters:**
    - iso3 (required)

#### Example usage

```bash
https://release-website-components.idmcdb.org/?page=conflict-widget&iso3=AFG&clientCode=YOUR_API_KEY
```

To integrate a widget, include the provided HTML snippet into your webpage.

```htmlbars
<div class="container">
    <iframe 
        src="https://release-website-components.idmcdb.org/?page=conflict-widget&iso3=AFG&clientCode=YOUR_API_KEY" 
        title="Conflict Widget for Afghanistan" 
        allowfullscreen
    >
    </iframe>
</div>
```

<h3 id="disaster-widget">Disaster Widget</h3>

- Displays disaster events disaggregated by country, hazard type, and year.
- Use parameter `page=disaster-widget` to select this widget
- **Parameters:**
    - iso3 (required)

<h3 id="idu-widget">IDU Widget</h3>

- Shows IDU map data with filters for monthly queries and a carousel for latest updates.
- Use parameter `page=idu-map` to select this widget
- **Parameters:**
    - iso3

<h3 id="gidd-widget">GIDD Widget</h3>

- Shows the GIDD data with charts and filters.
- Use parameter `page=gidd` to select this widget
- **Parameters:**
    - No parameters


<h2 id="code-sample">Code sample to read and export the IDU API as a geojson file for GIS applications</h2>

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


<h2 id="caveats-limitation">General caveats and limitations of the datasets</h2>

- The IDU dataset provides preliminary estimates and is updated daily. It may not align perfectly with the annually consolidated GIDD dataset and does not undergo the same quality control process.
- When analyzing data with identical dates and locations, avoid summing figures to prevent overestimation unless these figures are labeled with role "Recommended Figure".
- Use the "Recommended Figure" over "Triangulation Figure" for the most accurate data.
- For spatial analysis, preprocess multi-location data to avoid double counting.

<h2 id="copyright">Copy rights and citation of the data</h2>

- **Non-Commercial Use:** Data is available under the Creative Commons Attribution-Non-Commercial-Share Alike 3.0 IGO license.
- **Attribution:** Proper attribution to IDMC is required when using the data.
- **Derived Works:** Must be shared under the same license terms.

<h2 id="citation">Citation</h2>

All derived work from IDMC data could cite IDMC following this example:

Internal Displacement Monitoring Centre. Global Internal Displacement Database. IDMC (2023). Available at: https://www.internal-displacement.org/database/displacement-data/ (Accessed: [date of access]).

<h2 id="support">Support</h2>

For feedback or technical questions contact ch.datainfo@idmc.ch.

For additional tools and resources visit the IDMC monitoring tools page.
