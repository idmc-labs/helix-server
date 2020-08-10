import json

from utils.tests import HelixGraphQLTestCase


class TestLogin(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.login_query = '''
            mutation MyMutation ($email: String!, $password: String!){
                login(input: {email: $email, password: $password}) {
                    errors {
                        field
                        messages
                    }
                }
            }
        '''

    def test_valid_login(self):
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['login']['errors'])

    def test_invalid_email(self):
        response = self.query(
            self.login_query,
            variables={'email': 'random@mail.com', 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('non_field_errors', [each['field'] for each in content['data']['login']['errors']])

    def test_invalid_password(self):
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': 'randompass'},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('non_field_errors', [each['field'] for each in content['data']['login']['errors']])

    def test_invalid_inactive_user_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('non_field_errors', [each['field'] for each in content['data']['login']['errors']])
