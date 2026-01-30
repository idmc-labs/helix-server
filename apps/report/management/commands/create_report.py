import typing
from datetime import date
from itertools import product

from apps.country.models import Country
from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    help = """
        Generate reports with parameters through arguments
        If any optional argument is not provided, default values will be used.
        Example usage: python manage.py create_report
            --report-years 2023 2024
            --country-iso3-codes USA npl
            --displacement-causes CONFLICT
            --categories NEW_DISPLACEMENT
        """

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-years",
            type=int,
            nargs="+",
            help="Space separated list of years. E.g. '--report-year 2023 2024'",
            required=True,
        )
        parser.add_argument(
            "--country-iso3-codes",
            type=str.upper,
            nargs="+",
            help=(
                "Country ISO3 codes to include during report generation. "
                "ISO3 codes can be found here: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3 "
                "E.g. 'USA' for United States, 'NPL' for Nepal."
            ),
        )
        parser.add_argument(
            "--displacement-causes",
            type=str.upper,
            nargs="+",
            help="Displacement causes to include during report generation.",
        )

        parser.add_argument(
            "--categories",
            type=str.upper,
            nargs="+",
            help="Categories to include during report generation.",
        )

    REPORT_CATEGORIES_LABEL: typing.Dict[str, str] = {
        "NEW_DISPLACEMENT": "ND",
        "IDPS": "S",
    }
    REPORT_CAUSES_LABEL: typing.Dict[str, str] = {
        "CONFLICT": "C",
        "DISASTER": "D",
    }

    def handle(self, *args, **kwargs):
        all_countries: typing.List[dict] = list(Country.objects.values("name", "iso3", "id"))
        all_countries_iso3: typing.List[str] = [country["iso3"].upper() for country in all_countries]
        all_countries_map: typing.Dict[str, dict] = {country["iso3"]: country for country in all_countries}

        report_years: typing.List[int] = kwargs.get("report_years") or []
        country_iso3_codes: typing.Set[str] = set(kwargs.get("country_iso3_codes") or all_countries_iso3)

        causes: typing.Set[str] = set(kwargs.get("displacement_causes") or self.REPORT_CAUSES_LABEL.keys())
        categories: typing.Set[str] = set(kwargs.get("categories") or self.REPORT_CATEGORIES_LABEL.keys())

        invalid_categories = categories - set(self.REPORT_CATEGORIES_LABEL.keys())
        if invalid_categories:
            self.stderr.write(self.style.ERROR(f"These categories are invalid: {invalid_categories}"))
            # FIXME: How to return proper error code
            return 1

        invalid_causes = causes - set(self.REPORT_CAUSES_LABEL.keys())
        if invalid_causes:
            self.stderr.write(self.style.ERROR(f"These displacement causes are invalid: {invalid_causes}"))
            # FIXME: How to return proper error code
            return 1

        invalid_country_iso3_codes = country_iso3_codes - set(all_countries_iso3)
        if invalid_country_iso3_codes:
            self.stderr.write(self.style.ERROR(f"These country iso3 codes are invalid: {invalid_country_iso3_codes}"))
            # FIXME: How to return proper error code
            return 1
        countries = [all_countries_map[country_iso3_code] for country_iso3_code in country_iso3_codes]

        tasks = product(countries, causes, categories, report_years)
        for task in tasks:
            country, cause, category, report_year = task
            start_year = date(report_year, 1, 1)
            end_year = date(report_year, 12, 31)

            name = (
                f"GRID {report_year + 1} - {country['name']} ({self.REPORT_CATEGORIES_LABEL[category]}) "
                f"- {self.REPORT_CAUSES_LABEL[cause]}"
            )
            variables = {
                "report": {
                    "name": name,
                    "filterFigureEndBefore": end_year,
                    "filterFigureStartAfter": start_year,
                    "filterFigureCountries": [int(country["id"])],
                    "filterFigureCategories": [category],
                    "filterFigureCrisisTypes": [cause],
                    "filterFigureRoles": ["RECOMMENDED"],
                    "isPublic": True,
                }
            }
            try:
                self.handle_report_generation(variables)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Report generation failed variables: {variables}, error: {e}"))
