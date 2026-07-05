from django.db import migrations

# event_event.name already has a trigram index; this covers the event_code leg.
SQL = (
    "CREATE INDEX IF NOT EXISTS event_code_trgm_idx ON event_eventcode "
    "USING gin (UPPER(helix_unaccent(event_code)::text) gin_trgm_ops);"
)
DROP = "DROP INDEX IF EXISTS event_code_trgm_idx;"


class Migration(migrations.Migration):
    dependencies = [
        ("event", "0035_event_event_created_at_desc_idx"),
        ("common", "0001_helix_unaccent"),
    ]
    operations = [migrations.RunSQL(SQL, DROP)]
