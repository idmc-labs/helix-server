from django.db import migrations

from apps.contrib.migrate_commands import merge_events as update_figures_and_merge_events


def merge_events(apps, schema_editor):
    data = {
        # data format: '17885': [17883, 17880, 17879, 17878]
        '17924': [17923]
    }
    if data == {}:
        return
    update_figures_and_merge_events(data, schema_editor)


def reverse_merge_events(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('event', 'change_violence_types_and_sub_types'),
    ]

    # operations = [
    #     migrations.RunPython(merge_events, reverse_code=migrations.RunPython.noop),
    # ]
    operations = [
        migrations.RunPython(merge_events, reverse_merge_events),
    ]
