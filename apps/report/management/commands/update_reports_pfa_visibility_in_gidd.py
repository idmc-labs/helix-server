import csv
import logging
from django.db import transaction
from django.core.management.base import BaseCommand

from utils.error_types import mutation_is_not_valid
from apps.report.models import Report
from apps.report.serializers import ReportSerializer, check_is_pfa_visible_in_gidd

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Update report pfa visibility"

    def add_arguments(self, parser):
        parser.add_argument('reports')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        reports_file = kwargs['reports']

        with open(reports_file, 'r') as reports_csv_file:
            reader = csv.DictReader(reports_csv_file)

            ids = [report['id'] for report in reader]

        reports_to_enable_pfa = Report.objects.filter(
            id__in=ids,
        )

        success = 0
        for report in reports_to_enable_pfa:
            if errors := check_is_pfa_visible_in_gidd(report):
                print('Could not update is_pfa_visible_in_gidd for report', report.id)
                print(errors)
            else:
                report.is_pfa_visible_in_gidd = True
                report.save()
                print('Updated is_pfa_visible_in_gidd for report', report.id)
                success += 1

        print(f'Updated {success} reports\' visibility in GIDD')
