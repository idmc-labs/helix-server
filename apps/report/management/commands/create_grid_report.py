from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    help = """
        Generate GRID report for a specified year(s).
        Example usage: python manage.py create_grid_report
            --report-years 2023 2024
        """

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-years",
            nargs="+",
            type=int,
            required=True,
            help="Space separated list of years. E.g. to create GRID 2024 and GRID 2025, use '--report-year 2023 2024'",
        )

    def handle(self, *args, **options):
        grid_report_years = sorted(set(options["report_years"]))
        for year in grid_report_years:
            variables = {
                "report": {
                    "isGiddReport": True,
                    "name": f"GRID {year + 1}",
                    "giddReportYear": year,
                }
            }
            try:
                self.handle_report_generation(variables, "generic_grid_report")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Report generation failed variables: {variables}, error: {e}"))
