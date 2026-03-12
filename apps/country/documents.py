from collections import OrderedDict

headers = OrderedDict(
    # key="Key?", # this is not obvious
    country__region__name="Region name",
    country__idmc_short_name="Country",
    year="Year",
    size="AHHS",
    # reference_year="Reference Year", # this is not obvious
    data_source_category="Data Source Category",
    source="Source",
    source_link="Source Link",
    # gap_filling_method="Gap Filling Method", # this is not obvious
    notes="Note",
)

readme_data_raw = [
    ("ISO3", 'ISO 3166-1 alpha-3. The ISO3 "AB9" was assigned to the Abyei Area'),
    ("Country", "Country's or territory short name"),
    ("Region name", "IDMC regions"),
    ("Source", "Source of the household size"),
    ("Source Link", "Link of the source."),
    ("Year", "Year of displacement"),
    ("Size", "Average household size. This values are comapiled by IDMC from UN and national sources."),
    # ("Data Source Category", ""),
    # ("Note", ""),
]

README_DATA = [{"column_name": column_name, "description": description} for column_name, description in readme_data_raw]
# TODO: This is not final
