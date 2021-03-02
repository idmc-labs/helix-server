from apps.users.enums import USER_ROLE
from utils.factories import (
    CountryFactory,
    ReportFactory,
)
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestCreateReport(HelixGraphQLTestCase):
    def setUp(self) -> None:
        countries = CountryFactory.create_batch(2)
        self.mutation = '''mutation MyMutation($input: ReportCreateInputType!) {
            createReport(data: $input) {
                result {
                    name
                    figureStartAfter
                    figureEndBefore
                    eventCountries {
                        id
                    }
                }
                ok
                errors
            }
        }'''
        self.input = {
            "name": "disss",
            "figureStartAfter": "2020-01-01",
            "figureEndBefore": "2020-07-01",
            "eventCountries": [str(each.id) for each in countries],
        }

    def test_valid_report_creation(self) -> None:
        admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createReport']['ok'], content)
        self.assertEqual(content['data']['createReport']['result']['name'], self.input['name'])
        self.assertEqual(len(content['data']['createReport']['result']['eventCountries']),
                         len(self.input['eventCountries']))

    def test_invalid_report_creation_by_guest(self) -> None:
        reviewer = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(reviewer)
        response = self.query(
            self.mutation,
            input_data=self.input
        )

        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestReportComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create()
        self.report.create
