import gzip
import os
import csv
import logging
from datetime import datetime, timedelta

from django.db import migrations
from django.conf import settings

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

    Figure = apps.get_model('entry', 'Figure')
    with gzip.open(file_path, 'rt', encoding='utf-8') as fp:
        csv_reader = csv.DictReader(fp, fieldnames=['type', 'id', 'old_id', 'start_date', 'end_date'])

        next(csv_reader)  # Skip headers
        for row in csv_reader:
            figure_queryset = Figure.objects.filter(old_id=row['old_id'])

            # NOTE: Check if figure exist or not
            if not figure_queryset.exists():
                logger.error(
                    f"For the figure old id {row['old_id']}, no figures found"
                )
                continue

            figure_count = figure_queryset.count()

            # NOTE: Checking for the figures containing same old_id
            if figure_count == 2:
                flow_figures_count = 0
                stock_figures_count = 0
                for figure_instance in figure_queryset.iterator():
                    if figure_instance.category == FigureModel.FIGURE_CATEGORY_TYPES.IDPS:
                        stock_figures_count += 1
                    elif figure_instance.category == FigureModel.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT:
                        flow_figures_count += 1

                if flow_figures_count == 1 and stock_figures_count == 1:
                    logger.error(
                        f"For the figure id {figure_instance.id}, Got {flow_figures_count} flows and {stock_figures_count} stocks"
                    )
                    continue
            elif figure_count > 2:
                logger.error(
                    f"We expected only 2 figures but got {figure_count}"
                )
                continue

            for figure_instance in figure_queryset.iterator():
                update_needed = False
                if row['start_date']:
                    correct_start_date = datetime.strptime(row['start_date'], '%Y-%m-%d').date()
                    if correct_start_date == figure_instance.start_date:
                        # NOTE: No need to migrate the start_date
                        pass
                    elif abs(figure_instance.start_date - correct_start_date) == timedelta(days=1):
                        figure_instance.start_date = correct_start_date
                        update_needed = True
                    else:
                        logger.warning(
                            f"The difference between the actual start date and the correct start date is not 1 day for figure old id {row['old_id']}. "
                            f"Expected {row['start_date']} but found {figure_instance.start_date}. Skipping..."
                        )

                # Update End date                
                if row['end_date']:
                    correct_end_date = datetime.strptime(row['end_date'], '%Y-%m-%d').date()
                    if correct_end_date == figure_instance.end_date:
                        # NOTE: No need to migrate the end_date
                        pass
                    elif abs(figure_instance.end_date - correct_end_date) == timedelta(days=1) and figure_instance.start_date <= correct_end_date:
                        # NOTE: Check if the correct end date is before the start date
                        figure_instance.end_date = correct_end_date
                        update_needed = True
                    else:
                        logger.warning(
                            f"The difference between the actual end date and the correct end date is not 1 day for figure old id {row['old_id']}. "
                            f"Expected {row['end_date']} but found {figure_instance.end_date}. Skipping..."
                        )

                    # NOTE: Logging if the start date is greater than the end date
                    if figure_instance.start_date > correct_end_date:
                        logger.error(
                            f"The start date is greater than the end date for figure old id {row['old_id']}. "
                            f"Start date: {figure_instance.start_date}, End date: {correct_end_date}. Skipping..."
                        )
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