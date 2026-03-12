readme_data_raw = [
    ("Region Name", "IDMC regions"),
    ("Country", "Country's or territory short name"),
    ("Year", "Year of displacement"),
    ("AHHS", "Average household size. This values are comapiled by IDMC from UN and national sources."),
    ("Reference Year", "Year of data reference"),
    ("Data Source Category", "Data Source Category"),
    ("Source", "Source of the household size"),
    ("Source Link", "Link of the source."),
    ("Gap Filling Method", "Gap Filling Method"),
    ("Notes", "Notes"),
]

README_DATA = [{"column_name": column_name, "description": description} for column_name, description in readme_data_raw]
# TODO: This is not final
