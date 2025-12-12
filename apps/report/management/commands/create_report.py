from datetime import date
from itertools import product

from django.db import close_old_connections, transaction

from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    REPORT_CANDIDATES = {
        "ND": "NEW_DISPLACEMENT",
        "S": "IDPS",
    }
    help = (
        """Generate reports with parameters through arguments"""
        """If any optional argument is not provided, default values will be used."""
        """
        Example usage: python manage.py create_report
            --report-year 2023
            --country-code USA
            --displacement-cause CONFLICT
        """
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-year",
            "-y",
            type=int,
            help="The year for which to generate the GRID report.",
            required=True,
        )
        parser.add_argument(
            "--displacement-cause",
            "-cause",
            type=str,
            help="Cause of the displacement",
            required=False,
        )
        parser.add_argument(
            "--country-code",
            "-cc",
            type=str,
            help=(
                "Country code(ISO3) to filter the report generation."
                "If not provided, the report will include all countries."
                "ISO3 codes can be found here: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3"
                "For example, 'USA' for United States, 'NEP' for Nepal."
            ),
            required=False,
        )

    def get_countries(self, iso3_code, start_date, end_date, crisis_values):
        """Helper function to get countries."""
        if iso3_code:
            qs = Country.objects.filter(iso3__iexact=iso3_code)
        else:
            qs = Country.objects.filter(
                events__start_date__gte=start_date,
                events__end_date__lte=end_date,
                events__crisis__crisis_type__in=crisis_values,
            ).distinct()

        return qs.values(
            "name",
            "iso3",
            "id",
        )

    def process_single_report(self, task_data):
        close_old_connections()

        country, crisis_type, candidate, report_year, start_date, end_date = task_data

        variables = {
            "report": {
                "name": f"GRID {report_year} - {country['name']} ({candidate}) - {crisis_type[0]}",
                "giddReportYear": report_year,
                "filterFigureEndBefore": end_date.strftime("%Y-%m-%d"),
                "filterFigureStartAfter": start_date.strftime("%Y-%m-%d"),
                "filterFigureCountries": [int(country["id"])],
                "filterFigureCategories": [self.REPORT_CANDIDATES[candidate]],
                "filterFigureRoles": ["RECOMMENDED"],
            }
        }
        try:
            with transaction.atomic():
                self.handle_report_generation(variables)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Report generation failed variables: {variables}, error: {e}"))

    def handle(self, *args, **kwargs):
        report_year = kwargs["report_year"]
        iso3_country_code = kwargs.get("country_code")
        cause = kwargs.get("displacement_cause")

        start_date = date(report_year, 1, 1)
        end_date = date(report_year, 12, 31)

        valid_crisis_mapping = {c.name: c.value for c in Crisis.CRISIS_TYPE if c.name != "OTHER"}
        if cause:
            cause = cause.upper()
            if cause not in valid_crisis_mapping:
                self.stderr.write(self.style.ERROR(f"Invalid crisis type: {cause}"))
                return
            filtered_crisis = {cause: valid_crisis_mapping[cause]}
        else:
            filtered_crisis = valid_crisis_mapping

        countries = list(self.get_countries(iso3_country_code, start_date, end_date, filtered_crisis.values()))

        if not countries:
            self.stderr.write(self.style.ERROR("No countries found for the given filters."))
            return

        tasks = product(
            countries, filtered_crisis.keys(), self.REPORT_CANDIDATES.keys(), [report_year], [start_date], [end_date]
        )
        for task in tasks:
            self.stdout.write(self.style.NOTICE(f"Processing report with data: {task}"))
            self.process_single_report(task)
