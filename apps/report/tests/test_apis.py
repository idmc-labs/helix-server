from apps.users.enums import USER_ROLE
from apps.report.models import ReportSignOff
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


class TestReportSignOff(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create(
            created_by=self.admin
        )
        self.mutation = '''
        mutation SignOffReport($id: ID!) {
          signOffReport(id: $id) {
            errors
            ok
            result {
              isSignedOff
              id
              signOffs {
                results {
                  createdBy {
                    email
                  }
                  snapshot
                  fullReport
                }
              }
            }
          }
        }
        '''
        self.variables = {
            'id': str(self.report.id),
        }

    def test_valid_report_sign_off_and_retrieval(self):
        user = create_user_with_role(USER_ROLE.IT_HEAD.name)
        self.force_login(user)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['signOffReport']['result']['isSignedOff'], True)
        self.assertEqual(content['data']['signOffReport']['result']['id'], str(self.report.id))
        self.assertEqual(len(content['data']['signOffReport']['result']['signOffs']['results']), 1)
        # resign-off should create another signedoff report instance
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        assert ReportSignOff.objects.count() == 2
        self.assertEqual(len(content['data']['signOffReport']['result']['signOffs']['results']), 2, content['data'])

    def test_invalid_report_signoff(self):
        editor = create_user_with_role(USER_ROLE.MONITORING_EXPERT_EDITOR.name)
        self.force_login(editor)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])

        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()
        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])


class TestReportApprove(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.report = ReportFactory.create(
            created_by=self.admin
        )
        self.mutation = '''
        mutation ApproveReport($id: ID!, $approve: Boolean!) {
          approveReport(id: $id, approve: $approve) {
            ok
            errors
            result {
            approvers {
              results {
                  createdBy {
                    email
                    id
                  }
                  isApproved
                }
              }
            }
          }
        }
        '''
        self.variables = {
            'id': str(self.report.id),
            'approve': True,
        }

    def test_valid_report_approval(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(user)
        response = self.query(
            self.mutation,
            variables=self.variables
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['approveReport']['result']['approvers']['results'][0]['createdBy']['email'],
                         user.email)

    def test_invalid_report_approval_by_guest(self):
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)
        response = self.query(
            self.mutation,
            variables=self.variables
        )
        content = response.json()

        self.assertIn(PERMISSION_DENIED_MESSAGE, content['errors'][0]['message'])
