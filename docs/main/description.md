<h2 id="introduction">Introduction</h2>

The Internal Displacement Monitoring Centre (IDMC) offers APIs that provide direct access to its primary data products: the **Global Internal Displacement Database (GIDD)** and the **Internal Displacement Updates (IDU)**. 
Through the API, users can retrieve datasets that include annual estimates, event-level data, and geospatial disaggregation. This documentation outlines how to access the API, retrieve data, and understand its structure and limitations. It also provides technical guidance on embedding widgets, using geospatial data, and integrating IDMC’s datasets into your workflows. For questions or technical issues contact [ch.datainfo@idmc.ch](mailto:ch.datainfo@idmc.ch).

### Table of Contents

- [Introduction](#introduction)
- [Overview of IDMC's Core Datasets](#overview)
- [Definitions](#definitions)
- [How to Create a Token to Access the APIs](#access-api)
- [Widgets](#widgets)
- [General caveats and limitations of the datasets](#caveats-limitation)
- [Copyrights and citation of the data](#copyright)
- [Citation](#citation)
- [Support](#support)

<h2 id="overview">Overview of IDMC's Core Datasets</h2>

IDMC provides two main datasets accessible via API:

1. **[Global Internal Displacement Database (GIDD):](https://www.internal-displacement.org/database/displacement-data/)**
    - The GIDD is an annual dataset that provides validated and peer-reviewed estimates of internal displacement resulting from conflict and disasters. Conflict-related displacement figures are reported at the national level by calendar year, while disaster-related displacement is recorded at the event level. Since 2023, the dataset includes additional disaggregation by location, displacement cause, and event.
    - The GIDD captures both population flows (new displacements during the year) and stocks (total number of people living in displacement at the end of the year), covering the period from 1 January to 31 December.
    - Additional methodological notes, caveats, and information on historical revisions are available through the Public Figure Analysis API, which complements the main dataset with detailed contextual insights.
    - This dataset is available since 2009 for conflict and 2008 for disaster induced displacement.
2. **[Internal Displacement Updates (IDU):](https://www.internal-displacement.org/internal-displacement-updates/)**
    - The IDU dataset is an event-based, near real-time resource updated on a daily basis. It captures new displacement events as they are identified through continuous monitoring of primary and secondary sources.
    - IDU provides the most current estimates of internal displacement population flows only. Figures are provisional and may be updated or revised as more accurate or complete information becomes available over time.

The GIDD and IDU serve different purposes: the GIDD offers historical consistency and comparability, while the IDU allows early detection and analysis of new events. Users are encouraged to consult both datasets depending on their use case.

<h2 id="definitions">Definitions</h2>

- **Internally displaced persons (IDPs)**: Defined according to the [1998 Guiding Principles on Internal Displacement](https://www.internal-displacement.org/internal-displacement/guiding-principles-on-internal-displacement/) as people or groups of people who have been forced or obliged to flee or to leave their homes or places of habitual residence in particular as a result of armed conflict or to avoid the effects of armed conflict, situations of generalized violence, violations of human rights, or natural or human-made disasters, and who have not crossed an international border.
- **Internal Displacements (flows)**: Represents the number of internal displacements or internal displacement population flows reported from January 1st to December 31st of a reporting year. This figure may include individuals who are displaced multiple times during the year by different events.
- **Total number of Internally Displaced Persons (IDPs) (stocks)**: Represents the total number of people living in situations of internal displacement as of the end of the reporting year, specifically on December 31st of each year.
- **Conflict displacement**: Refers to situations where people are forced to leave their homes or places of habitual residence as a result or in order to avoid the impact of armed conflict and other situations of violence including communal violence, criminal violence and civilian-state violence.
- **Disaster displacement**: Refers to situations where people are forced to leave their homes or places of habitual residence as a result or in anticipation of the negative impact of natural hazards.
- **Disaster**: A serious disruption of the functioning of a community or a society involving widespread human, material, economic, or environmental losses and impacts which exceeds the ability of the affected community or society to cope using its own resources.

<h2 id="access-api">How to Create a Token to Access the APIs</h2>

To access IDMC’s APIs, follow these steps

1. **Request Access**
2. Send an email to ch.datainfo@idmc.ch with a brief description of how you plan to use the data.
3. Please specify your use case by selecting one or more of the following categories:
    - Anticipatory action
    - Humanitarian response
    - Risk of displacement
    - Research or data analysis
    - Modelling
    - Data sharing on external platforms
    - Other (please specify)
4. **Receive Your API Key**
5. If your request is approved, you will receive an API key (referred to as client_id) via email.
6. Include the Key in API Requests
7. Use the client_id as a query parameter in all API calls. For example:
   ```bash
   GET https://helix-tools-api.idmcdb.org/external-api/gidd/displacements/?client_id=YOUR_API_KEY
   ```

> NOTE: API keys help IDMC monitor usage and ensure fair access.

<h2 id="widgets">Widgets</h2>

IDMC offers widgets that can be embedded into websites to display displacement data. These widgets are configurable and can be tailored to show specific data subsets.

<h3 id="conflict-widget">Conflict Widget</h3>

![Conflict Widget](https://s3-ap-southeast-1.amazonaws.com/tc-codimd/uploads/331ae676863e494e83598e717.png)

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

![Disaster Widget](https://s3-ap-southeast-1.amazonaws.com/tc-codimd/uploads/331ae676863e494e83598e718.png)

- Displays disaster events disaggregated by country, hazard type, and year.
- Use parameter `page=disaster-widget` to select this widget.
- **Parameters:**
    - iso3 (required)

<h3 id="idu-widget">IDU Widget</h3>

![IDU Widget](https://s3-ap-southeast-1.amazonaws.com/tc-codimd/uploads/331ae676863e494e83598e719.png)

- Shows IDU map data with filters for monthly queries and a carousel for latest updates.
- Use parameter `page=idu-map` to select this widget.
- **Parameters:**
    - iso3

<h3 id="gidd-widget">GIDD Widget</h3>

![GIDD Widget](https://s3-ap-southeast-1.amazonaws.com/tc-codimd/uploads/331ae676863e494e83598e71a.png)

- Shows the GIDD data with charts and filters.
- Use parameter `page=gidd` to select this widget.
- **Parameters:**
    - No parameters

<h2 id="caveats-limitation">General caveats and limitations of the datasets</h2>

- The IDU dataset provides preliminary estimates and is updated daily. It may not align perfectly with the annually consolidated GIDD dataset and does not undergo the same quality control process.
- When analyzing data with identical dates and locations, avoid summing figures to prevent overestimation unless these figures are labeled with role "Recommended Figure".
- Use the "Recommended Figure" over "Triangulation Figure" for the most accurate data.
- For spatial analysis, preprocess multi-location data to avoid double counting.

<h2 id="copyright">Copyrights and citation of the data</h2>

- **Non-Commercial Use:** Data is available under the Creative Commons Attribution-Non-Commercial-Share Alike 3.0 IGO license.
- **Attribution:** Proper attribution to IDMC is required when using the data.
- **Derived Works:** Must be shared under the same license terms.

<h2 id="citation">Citation</h2>

All derived work from IDMC data could cite IDMC following this example:

Internal Displacement Monitoring Centre. Global Internal Displacement Database. IDMC (2023). Available at: [https://www.internal-displacement.org/database/displacement-data/](https://www.internal-displacement.org/database/displacement-data/) (Accessed: [date of access]).

<h2 id="support">Support</h2>

For feedback or technical questions contact [ch.datainfo@idmc.ch](mailto:ch.datainfo@idmc.ch).

For additional tools and resources visit the [IDMC monitoring tools](https://www.internal-displacement.org/monitoring-tools/) page.
