## API documentation
### Introduction
IDMC provides APIs to make the data in our Global Internal Displacement Database (GIDD) and Internal Displacement Updates (IDU) directly available to developers and analysts. This page has detailed descriptions of the databases and how to use the APIs. For feedback or technical questions contact [ch.datainfo@idmc.ch](mailto:ch.datainfo@idmc.ch).

Our API documentation also includes widgets that allow users to embed data visualization products directly into their websites. Additionally, users can access datasets with various levels of geospatial disaggregation, along with contextual information detailing the sources, methodologies, and caveats associated with the figures reported by IDMC in the GIDD.

### Table of Contents
- [Overview](#overview)
- [IDMC's main data products](#data-products)
- [Definitions](#definitions)
- [Accessing the API](#access-api)
- [Authentication](#authentication)

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

API requests require authentication through a `client_id` parameter. This parameter must be included in every request to access the data.
