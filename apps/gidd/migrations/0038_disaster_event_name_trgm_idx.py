from django.db import migrations

# No helix_unaccent wrap: the public GIDD filter uses a plain `event_name__icontains`,
# and the index expression must match that SQL exactly.
SQL = (
    "CREATE INDEX IF NOT EXISTS gidd_disaster_event_name_trgm_idx ON gidd_disaster "
    "USING gin (UPPER(event_name::text) gin_trgm_ops);"
)
DROP = "DROP INDEX IF EXISTS gidd_disaster_event_name_trgm_idx;"


class Migration(migrations.Migration):
    dependencies = [
        ("gidd", "0037_migrate_default_values"),
        ("common", "0001_helix_unaccent"),  # provides the pg_trgm extension
    ]
    operations = [migrations.RunSQL(SQL, DROP)]
