from django.db import migrations


def rename_to_trigger(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="hulk", model="hulkbulkimport").first()
    if ct is None:
        return
    Permission.objects.filter(
        content_type=ct,
        codename="bulk_import_hulkbulkimport",
    ).update(codename="trigger_hulkbulkimport")


def rename_to_bulk_import(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    ct = ContentType.objects.filter(app_label="hulk", model="hulkbulkimport").first()
    if ct is None:
        return
    Permission.objects.filter(
        content_type=ct,
        codename="trigger_hulkbulkimport",
    ).update(codename="bulk_import_hulkbulkimport")


class Migration(migrations.Migration):

    dependencies = [
        ('hulk', '0002_hulkbulkimport_celery_task_id'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='hulkbulkimport',
            options={
                'permissions': (('trigger_hulkbulkimport', 'Can trigger hulk bulk import'),),
            },
        ),
        migrations.RunPython(rename_to_trigger, rename_to_bulk_import),
    ]
