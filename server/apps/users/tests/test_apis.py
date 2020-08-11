import json

from django.contrib.auth.tokens import default_token_generator
from djoser.utils import encode_uid

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
        self.me_query = '''
            query MeQuery {
                me {
                    email
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

        response = self.query(
            self.me_query,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['me']['email'], self.user.email)

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


class TestRegister(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.register = '''
            mutation Register ($input: RegisterMutationInput!){
                register(input: $input) {
                    errors {
                        field
                        messages
                    }
                }
            }
        '''
        self.input = {
            'email': 'admin@email.com',
            'username': 'test',
            'password1': 'admin123',
            'password2': 'admin123'
        }

    def test_valid_registration(self):
        response = self.query(
            self.register,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['register']['errors'])

    def test_invalid_user_already_exists(self):
        self.user = self.create_user()

        self.input.update(dict(email=self.user.email))
        response = self.query(
            self.register,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNotNone(content['data']['register']['errors'])
        self.assertIn('email', [each['field'] for each in content['data']['register']['errors']])


class TestActivate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.activate = '''
            mutation Activate ($input: ActivateMutationInput!) {
                activate(input: $input) {
                    errors {
                        field
                        messages
                    }
                }
            }
        '''
        self.input = {
            'uid': encode_uid(self.user.pk),
            'token': default_token_generator.make_token(self.user)
        }

    def test_valid_activation(self):
        response = self.query(
            self.activate,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['activate']['errors'])

    def test_invalid_activation_uid(self):
        self.input.update(dict(uid='random'))
        response = self.query(
            self.activate,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('non_field_errors', [each['field'] for each in content['data']['activate']['errors']])

    def test_invalid_activation_token(self):
        self.input.update(dict(token='random-token'))
        response = self.query(
            self.activate,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('non_field_errors', [each['field'] for each in content['data']['activate']['errors']])


class TestLogout(HelixGraphQLTestCase):
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
        self.me_query = '''
            query MeQuery {
                me {
                    email
                }
            }
        '''
        self.logout_query = '''
            mutation Logout {
                logout {
                    ok
                }
            }
        '''

    def test_valid_logout(self):
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['login']['errors'])

        response = self.query(
            self.me_query,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['me']['email'], self.user.email)

        response = self.query(
            self.logout_query,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)

        response = self.query(
            self.me_query,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['me'], None)
