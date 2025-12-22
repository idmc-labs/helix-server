from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    help = "Generate GRID report for a specified year(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--grid-report-year",
            "-y",
            nargs="+",
            type=int,
            required=True,
            help="Space separated list of years, e.g. -y 2023 2024",
        )

    def handle(self, *args, **options):
        grid_report_years = sorted(set(options["grid_report_year"]))
        for year in grid_report_years:
            variables = {
                "report": {
                    "isGiddReport": True,
                    "name": f"GRID {year + 1}",
                    "giddReportYear": year,
                }
            }
            self.handle_report_generation(variables, "generic_grid_report")
