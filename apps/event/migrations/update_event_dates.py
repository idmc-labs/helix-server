import csv
import gzip
import os
import logging
from datetime import datetime, timedelta

from django.db import migrations

from helix.managers import BulkUpdateManager

logger = logging.getLogger(__name__)

def update_event_dates(apps, _):
    Event = apps.get_model('event', 'Event')
    bulk_mgr = BulkUpdateManager(['start_date', 'end_date'])

    file_path = os.path.join(
        os.path.dirname(__file__),
        'correct_events_dates.csv.gz',
    )

    with gzip.open(file_path, 'rt', encoding='utf-8') as fp:
        reader = csv.DictReader(fp, fieldnames=['id', 'old_id', 'start_date', 'end_date'])
        # Skip the csv header
        next(reader)

        for row in reader:
            event = Event.objects.filter(old_id=row['old_id']).first()

            if not event:
                logger.error(f"Skipped: Event ({row['old_id']}) not found.")
                continue

            update_needed = False

            # Update start date
            if row['start_date']:
                correct_start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                if event.start_date == correct_start_date:
                    # NOTE: No need to migrate the start_date
                    pass
                elif abs(event.start_date - correct_start_date) == timedelta(days=1):
                    event.start_date = correct_start_date
                    update_needed = True
                else:
                    logger.warning(f"Flag: For event ({row['old_id']}), delta between actual start_date ({event.start_date}) and the correct start_date ({row['start_date']}) is greater than 1")

            # Update end date
            if row['end_date']:
                correct_end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date()
                if event.end_date == correct_end_date:
                    # NOTE: No need to migrate the end_date
                    pass
                elif abs(event.end_date - correct_end_date) == timedelta(days=1):
                    event.end_date = correct_end_date
                    update_needed = True
                else:
                    logger.warning(f"Flag: For event ({row['old_id']}), delta between actual end_date ({event.end_date}) and the correct end_date ({row['end_date']}) is greater than 1")

            if update_needed:
                bulk_mgr.add(event)
                logger.warning(f"Processed: Event ({row['old_id']}) was updated.")
            else:
                logger.warning(f"Skipped: Event ({row['old_id']}) was not updated.")

    bulk_mgr.done()
    logger.info(f"Bulk update summary: {bulk_mgr.summary()}")

class Migration(migrations.Migration):

    dependencies = [
        ('event', '0001_auto_20240326_0824'),
    ]

    operations = [
        migrations.RunPython(
            update_event_dates,
            reverse_code=migrations.RunPython.noop
        ),
    ]
