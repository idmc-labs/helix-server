import csv
import logging
from django.core.management.base import BaseCommand

from utils.error_types import mutation_is_not_valid
from apps.report.models import Report
from apps.report.serializers import ReportSerializer

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = "Update report pfa visibility"

    def add_arguments(self, parser):
        parser.add_argument('reports')

    def handle(self, *args, **kwargs):
        reports_file = kwargs['reports']

        with open(reports_file, 'r') as reports_csv_file:
            reader = csv.DictReader(reports_csv_file)

            ids = [report['id'] for report in reader]

        reports_to_enable_pfa = Report.objects.filter(
            id___in=ids,
        )

        success = 0
        for report in reports_to_enable_pfa:
            serializer = ReportSerializer(instance=report, data={'is_pfa_visible_in_gidd': True})
            if errors := mutation_is_not_valid(serializer):
                print(errors)
                continue
            serializer.save()
            success += 1

        print(f'Updated {success} reports\' visibility in GIDD')
