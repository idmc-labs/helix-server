from django.db import migrations

# The existing btree on idmc_short_name serves ordering, not a leading-wildcard LIKE.
INDEXES = [
    (
        "country_idmc_short_name_trgm_idx",
        "CREATE INDEX IF NOT EXISTS country_idmc_short_name_trgm_idx ON country_country "
        "USING gin (UPPER(helix_unaccent(idmc_short_name)::text) gin_trgm_ops);",
    ),
    (
        "country_iso3_trgm_idx",
        "CREATE INDEX IF NOT EXISTS country_iso3_trgm_idx ON country_country "
        "USING gin (UPPER(helix_unaccent(iso3)::text) gin_trgm_ops);",
    ),
]


class Migration(migrations.Migration):
    dependencies = [
        ("country", "0023_auto_20260603_0608"),
        ("common", "0001_helix_unaccent"),
    ]
    operations = [migrations.RunSQL(sql, f"DROP INDEX IF EXISTS {name};") for name, sql in INDEXES]
