from datetime import date
from itertools import product

from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    REPORT_CANDIDATES = {
        "ND": "NEW_DISPLACEMENT",
        "S": "IDPS",
    }
    help = (
        "Generate reports with parameters through arguments"
        "If any optional argument is not provided, default values will be used."
        """
        Example usage: python manage.py create_report
            --report-year 2023 2024
            --country-code USA npl
            --displacement-cause CONFLICT
        """
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-year",
            "-y",
            type=int,
            nargs="+",
            help="The year(s) for which to generate the GRID report.",
            required=True,
        )
        parser.add_argument(
            "--country-code",
            "-cc",
            type=str.upper,
            nargs="+",
            help=(
                "Country code(s)(ISO3) to filter the report generation."
                "ISO3 codes can be found here: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3"
                "For example, 'USA' for United States, 'NPL' for Nepal."
            ),
            required=True,
        )
        parser.add_argument(
            "--displacement-cause",
            "-cause",
            type=str.upper,
            help="Cause of the displacement",
            required=False,
        )

    def process_single_report(self, task_data):
        country, crisis_type, candidate, report_years = task_data

        for report_year in report_years:
            start_year = date(report_year, 1, 1)
            end_year = date(report_year, 12, 31)
            variables = {
                "report": {
                    "name": f"GRID {report_year} - {country['name']} ({candidate}) - {crisis_type[0]}",
                    "giddReportYear": report_year,
                    "filterFigureEndBefore": end_year,
                    "filterFigureStartAfter": start_year,
                    "filterFigureCountries": [int(country["id"])],
                    "filterFigureCategories": [self.REPORT_CANDIDATES[candidate]],
                    "filterFigureRoles": ["RECOMMENDED"],
                    "isPublic": True,
                }
            }
            try:
                self.handle_report_generation(variables)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Report generation failed variables: {variables}, error: {e}"))

    def handle(self, *args, **kwargs):
        report_years = kwargs["report_year"]
        iso3_country_codes = set(kwargs["country_code"])
        cause = kwargs.get("displacement_cause")

        valid_crisis_mapping = {c.name: c.value for c in Crisis.CRISIS_TYPE if c.name != "OTHER"}
        if cause:
            if cause not in valid_crisis_mapping:
                self.stderr.write(
                    self.style.ERROR(
                        f"Invalid crisis type: [{cause}]; valid types are: [{', '.join(valid_crisis_mapping.keys())}]"
                    )
                )
                return
            filtered_crisis = {cause: valid_crisis_mapping[cause]}
        else:
            filtered_crisis = valid_crisis_mapping

        countries = list(Country.objects.filter(iso3__in=iso3_country_codes).values("name", "iso3", "id"))

        if not countries:
            self.stderr.write(self.style.ERROR("No countries found for the given filters."))
            return

        non_existent_countries = iso3_country_codes - {c["iso3"] for c in countries}
        if non_existent_countries:
            self.stderr.write(
                self.style.ERROR(
                    f"The following country code(s) are invalid: [{', '.join(non_existent_countries)}]; will be skipped."
                )
            )

        tasks = product(countries, filtered_crisis.keys(), self.REPORT_CANDIDATES.keys(), [report_years])
        for task in tasks:
            self.stdout.write(self.style.NOTICE(f"Processing report with data: {task}"))
            self.process_single_report(task)
