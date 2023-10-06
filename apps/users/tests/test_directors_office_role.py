from utils.factories import ReportFactory
from utils.permissions import PERMISSION_DENIED_MESSAGE
from utils.tests import HelixGraphQLTestCase, create_user_with_role
from apps.users.enums import USER_ROLE


class TestDirectorsOfficeRole(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.directors_office_user = create_user_with_role(USER_ROLE.DIRECTORS_OFFICE.name)
        self.report = ReportFactory.create(
            name='GRID Report Test',
            is_public=True,
            created_by=self.admin
        )

        self.create_report_mutation = '''mutation MyMutation($input: ReportCreateInputType!) {
            createReport(data: $input) {
                result {
                    id
                    name
                    isPublic
                }
                ok
                errors
            }
        }'''

        self.report_update_mutation = '''
          mutation MyMutation($input: ReportUpdateInputType!) {
            updateReport(data: $input) {
              ok
              errors
              result {
                id
                name
                isPublic
              }
            }
          }
        '''

        self.report_delete_mutation = """
            mutation MyMutation($id: ID!) {
                deleteReport(id: $id) {
                    ok
                    errors
                }
            }
        """

        self.approve_report_mutation = '''
        mutation MyMutation($id: ID!, $approve: Boolean!) {
            approveReport(id: $id, approve: $approve) {
                ok
                errors
            }
        }'''

        self.sign_off_report_mutation = '''
        mutation MyMutation($id: ID!, $includeHistory: Boolean) {
            signOffReport(id: $id, includeHistory: $includeHistory) {
                ok
                errors
            }
        }'''

        self.create_comment_in_report_mutation = '''
        mutation MyMutation($input: ReportCommentCreateInputType!) {
            createReportComment(data: $input) {
                ok
                errors
            }
        }'''

        self.input = {
            'name': 'Test Report',
            'isPublic': True
        }

    def test_directors_office_user_can_create_update_delete_report(self):
        self.force_login(self.directors_office_user)
        # Test director's office can create report
        response = self.query(
            self.create_report_mutation,
            input_data=self.input,
        )
        error_message = response.json()['errors'][0]['message']
        self.assertEqual(error_message, PERMISSION_DENIED_MESSAGE)

        self.force_login(self.admin)
        # Let's create a report using admin account
        response = self.query(
            self.create_report_mutation,
            input_data=self.input,
        )
        content = response.json()['data']['createReport']
        self.assertTrue(content['ok'])
        self.assertEqual(content['result']['name'], self.input['name'])
        self.assertEqual(content['result']['isPublic'], self.input['isPublic'])

        self.force_login(self.directors_office_user)
        # Test can update report
        report_id = content['result']['id']
        update_data = {
            'id': report_id,
            'name': 'Report updated',
        }
        response = self.query(
            self.report_update_mutation,
            input_data=update_data,
        )
        content = response.json()['data']['updateReport']
        self.assertTrue(content['ok'])
        self.assertEqual(content['result']['name'], update_data['name'])

        # Test can delete report
        response = self.query(
            self.report_delete_mutation,
            variables={'id': report_id}
        )
        error_message = response.json()['errors'][0]['message']
        self.assertEqual(error_message, PERMISSION_DENIED_MESSAGE)

    def test_directors_office_user_should_not_call_other_mutations(self):
        self.force_login(self.directors_office_user)
        # Test approve report
        response = self.query(
            self.approve_report_mutation,
            variables={
                'id': str(self.report.id),
                'approve': True,
            },
        )
        error_message = response.json()['errors'][0]['message']
        self.assertEqual(error_message, PERMISSION_DENIED_MESSAGE)

        # Test sign off report
        response = self.query(
            self.sign_off_report_mutation,
            variables={
                'id': str(self.report.id),
                'includeHistory': True,
            },
        )
        error_message = response.json()['errors'][0]['message']
        self.assertEqual(error_message, PERMISSION_DENIED_MESSAGE)

        # Test comment in report
        response = self.query(
            self.create_comment_in_report_mutation,
            input_data={
                'report': str(self.report.id),
                'body': 'test comment',
            },
        )
        error_message = response.json()['errors'][0]['message']
        self.assertEqual(error_message, PERMISSION_DENIED_MESSAGE)
