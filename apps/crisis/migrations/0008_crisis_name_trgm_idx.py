from django.db import migrations

# The index expression must match the search SQL: UPPER(HELIX_UNACCENT(name)::text).
SQL = (
    "CREATE INDEX IF NOT EXISTS crisis_name_trgm_idx ON crisis_crisis "
    "USING gin (UPPER(helix_unaccent(name)::text) gin_trgm_ops);"
)
DROP = "DROP INDEX IF EXISTS crisis_name_trgm_idx;"


class Migration(migrations.Migration):
    dependencies = [
        ("crisis", "0007_crisis_crisis_created_at_desc_idx"),
        ("common", "0001_helix_unaccent"),  # provides IMMUTABLE helix_unaccent() + pg_trgm
    ]
    operations = [migrations.RunSQL(SQL, DROP)]
