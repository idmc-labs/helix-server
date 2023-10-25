from django.db import migrations
from django.db.models import Count

def delete_events_with_empty_figure(apps, _):
    Event = apps.get_model('event', 'Event')
    Figure = apps.get_model('entry', 'Figure')
    event_ids = [
        15775,
        15776,
        15777,
        15779,
        15780,
        15781,
        15782,
        15783,
        15784,
        15785,
        15786,
        15788,
        15789,
        15790,
        15792,
        15793,
        15794,
        15795,
        15796,
        15797,
        15798,
        15799,
        15800,
        15801,
        15940,
        15941,
    ]

    event_qs = Event.objects.filter(id__in=event_ids).annotate(
        figures_count=Count('figures')
    )

    empty_events = event_qs.filter(figures_count__lte=0)
    resp = empty_events.delete()
    print(f'Deleted {resp} when deleting events')

    non_empty_events = event_qs.filter(figures_count__gt=0)
    print(f'Skipped deleting {non_empty_events.count()} non-empty events')


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0031_fix_drought_and_cold_wave_data_migration'),
    ]

    operations = [
        migrations.RunPython(delete_events_with_empty_figure, reverse_code=migrations.RunPython.noop),
    ]
