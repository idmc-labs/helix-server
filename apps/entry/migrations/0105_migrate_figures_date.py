import gzip
import os
import csv
import logging
from datetime import datetime, timedelta

from django.db import migrations

from helix.managers import BulkUpdateManager
from apps.entry.models import Figure as FigureModel

logger = logging.getLogger(__name__)

def update_figure_dates(apps, _):
    Figure = apps.get_model('entry', 'Figure')
    bulk_mgr = BulkUpdateManager(['start_date', 'end_date'])

    file_path = os.path.join(
        os.path.dirname(__file__),
        'correct_figures_dates.csv.gz',
    )

    with gzip.open(file_path, 'rt', encoding='utf-8') as fp:
        csv_reader = csv.DictReader(fp, fieldnames=['id', 'old_id', 'start_date', 'end_date', 'category', 'type'])
        # Skip the csv header
        next(csv_reader)

        for row in csv_reader:
            figure_queryset = Figure.objects.filter(old_id=row['old_id'])

            # NOTE: Check if figure exist or not
            if not figure_queryset.exists():
                logger.warning(f"Skipped: Figure ({row['old_id']}) not found.")
                continue

            figure_count = figure_queryset.count()

            # NOTE: We should can get 2 figures with the same old_id in cases of
            # partially added figures in Helix 1.0
            if figure_count == 2:
                flow_figures_count = 0
                stock_figures_count = 0
                for figure_instance in figure_queryset.iterator():
                    if figure_instance.category == FigureModel.FIGURE_CATEGORY_TYPES.IDPS:
                        stock_figures_count += 1
                    elif figure_instance.category == FigureModel.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
                        flow_figures_count += 1

                if flow_figures_count == 1 and stock_figures_count == 1:
                    logger.warning(f"Skipped: Figure ({row['old_id']} has 2 figures with different categories.")
                    continue
            elif figure_count > 2:
                logger.warning(f"Skipped: Figure ({row['old_id']} has {figure_count} figures.")
                continue

            for figure_instance in figure_queryset.iterator():
                update_needed = False

                start_end_date_inconsistent = (
                    figure_instance.start_date
                    and figure_instance.end_date
                    and figure_instance.start_date > figure_instance.end_date
                )

                if row['start_date']:
                    correct_start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                    if correct_start_date == figure_instance.start_date:
                        # NOTE: No need to migrate the start_date
                        pass
                    elif abs(figure_instance.start_date - correct_start_date) == timedelta(days=1):
                        figure_instance.start_date = correct_start_date
                        update_needed = True
                    else:
                        logger.warning(f"Flag: For figure ({row['old_id']}), delta between actual start_date ({figure_instance.start_date}) and the correct start_date ({row['start_date']}) is greater than 1")

                if row['end_date']:
                    correct_end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date()
                    if correct_end_date == figure_instance.end_date:
                        # NOTE: No need to migrate the end_date
                        pass
                    elif abs(figure_instance.end_date - correct_end_date) == timedelta(days=1):
                        figure_instance.end_date = correct_end_date
                        update_needed = True
                    else:
                        logger.warning(f"Flag: For figure ({row['old_id']}), delta between actual end_date ({figure_instance.end_date}) and the correct end_date ({row['end_date']}) is greater than 1")

                # NOTE: Logging if the start date is greater than the end date
                if not start_end_date_inconsistent and figure_instance.start_date and figure_instance.end_date and figure_instance.start_date > figure_instance.end_date:
                    logger.warning(f"Skipped: For figure ({row['old_id']}), start_date ({figure_instance.start_date}) is greater than end_date ({figure_instance.end_date})")
                    continue

                if update_needed:
                    bulk_mgr.add(figure_instance)

    bulk_mgr.done()
    logger.info(f"Bulk update summary: {bulk_mgr.summary()}")

class Migration(migrations.Migration):

    dependencies = [
        ('entry', '0104_auto_20250331_1109'),
    ]

    operations = [
        migrations.RunPython(
            update_figure_dates,
            reverse_code=migrations.RunPython.noop
        ),
    ]
