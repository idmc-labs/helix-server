import csv
import logging

from io import StringIO
from django.db import migrations
from django.conf import settings

from helix.managers import BulkUpdateManager

logger = logging.getLogger(__name__)

CSV_DATA = '''
id,migrated_start_date,correct_start_date,migrated_end_date,correct_end_date,change,new_id
217,2016-08-01,2016-08-01,2021-01-15,2016-08-01,end_changed,193.0
771,2017-06-01,2017-06-01,2022-05-11,2017-06-01,end_changed,
772,2017-06-01,2017-06-01,2019-06-30,2017-06-01,end_changed,636.0
1159,2017-08-01,2017-08-01,2021-07-23,2017-08-10,end_changed,881.0
1235,2017-09-01,2017-09-01,2020-02-18,2017-07-15,end_changed,1521.0
1240,2017-08-29,2017-08-29,2019-05-05,2017-09-07,end_changed,994.0
1241,2017-09-03,2017-09-03,2017-05-31,2017-09-08,end_changed,995.0
1245,2017-08-11,2017-08-11,2019-05-03,2017-09-27,end_changed,998.0
1263,2017-08-25,2017-08-25,2020-06-11,2017-10-20,end_changed,1012.0
2035,2016-07-24,2018-01-01,2016-08-13,2018-01-01,both_changed,3846.0
2408,2018-05-22,2018-05-22,2021-04-02,2018-05-22,end_changed,3823.0
3194,2018-07-01,2018-07-01,2019-01-18,2018-08-31,end_changed,3856.0
4644,2019-03-25,2019-03-25,2016-12-16,2019-03-26,end_changed,3849.0
5132,2019-03-15,2019-03-15,2020-08-05,2019-06-12,end_changed,3796.0
5203,2019-06-17,2019-06-17,2020-03-05,2019-06-27,end_changed,4111.0
5228,2019-04-15,2019-04-15,2017-11-05,2019-06-18,end_changed,4067.0
5266,2019-06-19,2019-06-19,2017-05-03,2019-06-27,end_changed,2263.0                         
'''

def update_event_dates(apps, _):

    reader = csv.DictReader(
        StringIO(CSV_DATA),
        fieldnames=['id', 'migrated_start_date', 'correct_start_date', 'migrated_end_date', 'correct_end_date', 'change', 'new_id'],
    )
    next(reader) # Skip the header

    Event = apps.get_model('event', 'Event')
    bulk_mgr = BulkUpdateManager(['start_date', 'end_date'])

    for row in reader:
        event = Event.objects.filter(old_id=row['id']).first()

        if not event:
            logger.warning(f"Event with old_id ({row['id']}) not found. Skipping update.")
            continue

        update_needed = False

        # Update start date
        if row['migrated_start_date'] == row['correct_start_date']:
            # NOTE: No need to migrate the start_date
            pass
        elif row['migrated_start_date'] != str(event.start_date):
            logger.error(
                f"Start date has been changed for event id {event.id}. "
                f"Expected: {row['migrated_start_date']}, But got {event.start_date}"
            )
        elif row['migrated_start_date'] == str(event.start_date):
            event.start_date = row['correct_start_date']
            update_needed = True

        # Update end date
        if row['migrated_end_date'] == row['correct_end_date']:
            # NOTE: No need to migrate the end_date
            pass
        elif row['migrated_end_date'] != str(event.end_date):
            logger.error(
                f"End date has been changed for event id {event.id}. "
                f"Expected: {row['migrated_end_date']}, But got {event.end_date}"
            )
        elif row['migrated_end_date'] == str(event.end_date):
            event.end_date = row['correct_end_date']
            update_needed = True

        if update_needed:
            bulk_mgr.add(event)

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
