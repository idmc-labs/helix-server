from django.db import migrations

# The notification panel runs `WHERE recipient_id = ? ORDER BY created_at DESC` with no
# supporting index. A composite (recipient_id, created_at DESC) btree serves both the
# recipient filter and the newest-first ordering in one index scan.
SQL = (
    "CREATE INDEX IF NOT EXISTS notification_recipient_created_idx "
    "ON notification_notification (recipient_id, created_at DESC);"
)
DROP = "DROP INDEX IF EXISTS notification_recipient_created_idx;"


class Migration(migrations.Migration):
    dependencies = [
        ("notification", "0005_auto_20221229_0532"),
    ]
    operations = [migrations.RunSQL(SQL, DROP)]
