from django.db import migrations

# The index expression must match the search SQL exactly: UPPER(helix_unaccent(<col>)::text).
INDEXES = [
    (
        "event_event",
        "event_name_trgm_idx",
        "CREATE INDEX IF NOT EXISTS event_name_trgm_idx ON event_event "
        "USING gin (UPPER(helix_unaccent(name)::text) gin_trgm_ops);",
    ),
    (
        "entry_entry",
        "entry_article_title_trgm_idx",
        "CREATE INDEX IF NOT EXISTS entry_article_title_trgm_idx ON entry_entry "
        "USING gin (UPPER(helix_unaccent(article_title)::text) gin_trgm_ops);",
    ),
]


class Migration(migrations.Migration):
    dependencies = [
        ("entry", "0114_figure_event_cat_role_rec_idx"),
        # provides pg_trgm + the IMMUTABLE helix_unaccent() the expressions use
        ("common", "0001_helix_unaccent"),
    ]

    operations = [migrations.RunSQL(sql, f"DROP INDEX IF EXISTS {name};") for _table, name, sql in INDEXES]
