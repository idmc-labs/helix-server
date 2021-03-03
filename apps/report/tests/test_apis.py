from apps.users.enums import USER_ROLE
from apps.report.models import ReportSignOff
from utils.factories import (
    CountryFactory,
    ReportFactory,
    ReportCommentFactory,
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
            approvals {
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
        self.assertEqual(content['data']['approveReport']['result']['approvals']['results'][0]['createdBy']['email'],
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


class TestReportComment(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.mutation = '''
        mutation MyMutation($input: ReportCommentCreateInputType!) {
          createReportComment(data: $input) {
            ok
            result {
              id
              createdBy { email }
            }
          }
        }
        '''
        self.update_mutation = '''
        mutation MyMutation($input: ReportCommentUpdateInputType!) {
          updateReportComment(data: $input) {
            ok
            result {
              id
              createdBy { email }
            }
          }
        }
        '''

        self.report = ReportFactory.create()
        self.input = dict(
            report=str(self.report.id),
            body='lol'
        )

    def test_valid_commenting(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(user)
        response = self.query(
            self.mutation,
            input_data=self.input,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['createReportComment']['ok'], content)
        self.assertTrue(content['data']['createReportComment']['result']['createdBy']['email'],
                        user.email)

    def test_valid_comment_update(self):
        user = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        comment = ReportCommentFactory.create(
            created_by=user
        )
        input_data = dict(
            body='blaaa',
            id=str(comment.id),
        )
        self.force_login(user)
        response = self.query(
            self.update_mutation,
            input_data=input_data,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['updateReportComment']['ok'], content)
        self.assertTrue(content['data']['updateReportComment']['result']['createdBy']['email'],
                        user.email)

        # different user
        user2 = create_user_with_role(USER_ROLE.MONITORING_EXPERT_REVIEWER.name)
        self.force_login(user2)
        response = self.query(
            self.update_mutation,
            input_data=input_data,
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['updateReportComment']['ok'], content)
