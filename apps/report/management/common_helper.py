from types import SimpleNamespace

from django.core.management.base import BaseCommand

from apps.users.enums import USER_ROLE
from apps.users.utils import HelixInternalBot
from helix.schema import schema
from utils.common import RuntimeProfile


class BaseReportCommand(BaseCommand):
    """
    Common command handler for GraphQL report generation.
    """

    bot = HelixInternalBot()
    context = SimpleNamespace(user=bot.user, request=SimpleNamespace(user=bot.user))

    mutation_string = """
            mutation CreateReport($report: ReportCreateInputType!) {
            createReport(data: $report) {
                result {
                    id
                    name
                }
                errors
                ok
            }
        }
        """

    def handle_report_generation(self, variables, runtime_label="report_generation"):
        with RuntimeProfile(runtime_label):
            with self.bot.temporary_role(USER_ROLE.ADMIN):
                response = schema.execute(
                    self.mutation_string,
                    variables=variables,
                    context_value=self.context,
                )

        return self._parse_response(response)

    def _parse_response(self, response):
        if response.errors:
            for error in response.errors:
                self.stderr.write(self.style.ERROR(f"GraphQL Error: {error}"))
            return False
        data = response.data["createReport"]
        if data.get("ok"):
            self.stdout.write(self.style.SUCCESS("Operation completed successfully."))
            return True
        else:
            self.stderr.write(self.style.ERROR(f"Mutation Error: {data['errors']}"))
            return False
