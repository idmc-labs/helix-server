from apps.report.management.common_helper import BaseReportCommand


class Command(BaseReportCommand):
    help = "Generate GRID report for a specified year."

    def add_arguments(self, parser):
        parser.add_argument("--gridreport-year", "-y", type=int, required=True)
        parser.add_argument("--gridreport-name", "-name", type=str, default="")

    def handle(self, *args, **options):
        year = options["gridreport_year"]
        variables = {
            "report": {
                "isGiddReport": True,
                "name": options["gridreport_name"] or f"GRID {year + 1}",
                "giddReportYear": year,
            }
        }
        self.handle_report_generation(variables, "generic_grid_report")
