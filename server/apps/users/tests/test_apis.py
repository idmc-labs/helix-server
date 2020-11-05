import json

from django.contrib.auth.tokens import default_token_generator
from djoser.utils import encode_uid

from apps.users.roles import MONITORING_EXPERT_EDITOR, ADMIN, IT_HEAD, MONITORING_EXPERT_REVIEWER
from utils.factories import EntryFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestLogin(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.login_query = '''
            mutation MyMutation ($email: String!, $password: String!){
                login(data: {email: $email, password: $password}) {
                    errors {
                        field
                        messages
                    }
                    result {
                        email
                        role
                    }
                }
            }
        '''
        self.me_query = '''
            query MeQuery {
                me {
                    email
                    role
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
        self.assertIsNotNone(content['data']['login']['result'])
        self.assertIsNotNone(content['data']['login']['result']['email'])

        response = self.query(
            self.me_query,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['me']['email'], self.user.email)
        self.assertEqual(content['data']['me']['role'], self.user.role)

    def test_invalid_email(self):
        response = self.query(
            self.login_query,
            variables={'email': 'random@mail.com', 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('nonFieldErrors', [each['field'] for each in content['data']['login']['errors']])
        self.assertIsNone(content['data']['login']['result'])

    def test_invalid_password(self):
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': 'randompass'},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('nonFieldErrors', [each['field'] for each in content['data']['login']['errors']])

    def test_invalid_inactive_user_login(self):
        self.user.is_active = False
        self.user.save()
        response = self.query(
            self.login_query,
            variables={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('nonFieldErrors', [each['field'] for each in content['data']['login']['errors']])


class TestRegister(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.register = '''
            mutation Register ($input: RegisterInputType!){
                register(data: $input) {
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
            'password': 'admin123',
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
            mutation Activate ($input: ActivateInputType!) {
                activate(data: $input) {
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
        self.assertIn('nonFieldErrors', [each['field'] for each in content['data']['activate']['errors']])

    def test_invalid_activation_token(self):
        self.input.update(dict(token='random-token'))
        response = self.query(
            self.activate,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIn('nonFieldErrors', [each['field'] for each in content['data']['activate']['errors']])


class TestLogout(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.login_query = '''
            mutation MyMutation ($email: String!, $password: String!){
                login(data: {email: $email, password: $password}) {
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


class TestUserSchema(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.reviewer_q = '''
        query MyQuery {
          me {
            email
            reviewEntries(page: 1, pageSize: 10) {
              totalCount
              results {
                id
                articleTitle
              }
            }
          }
        }
        '''

    def test_fetch_reviews_to_be_reviewed(self):
        e1 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        e2 = create_user_with_role(MONITORING_EXPERT_EDITOR)
        entry = EntryFactory.create(created_by=e1)
        entry.reviewers.set([e1, e2])
        entry2 = EntryFactory.create(created_by=e1)
        entry2.reviewers.set([e2])
        self.assertEqual(entry.reviewers.count(), 2)

        self.force_login(e1)
        response = self.query(self.reviewer_q)
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['me']['email'], e1.email)
        self.assertIn(entry, e1.review_entries.all())
        self.assertEqual(content['data']['me']['reviewEntries']['totalCount'], 1)
        self.assertEqual(content['data']['me']['reviewEntries']['results'][0]['id'], str(entry.id))

        self.force_login(e2)
        response = self.query(self.reviewer_q)
        content = json.loads(response.content)
        self.assertResponseNoErrors(response)
        self.assertIn(entry2, e2.review_entries.all())
        self.assertEqual(content['data']['me']['reviewEntries']['totalCount'], 2)
        self.assertListEqual([int(each['id']) for each in content['data']['me']['reviewEntries']['results']],
                             [entry.id, entry2.id])


class TestUserListSchema(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.users_q = '''
            query MyQuery($roles: [String!]) {
              users(roleIn: $roles) {
                results {
                  id
                  role
                }
              }
            }
        '''

    def test_filter_users(self):
        ue = create_user_with_role(MONITORING_EXPERT_EDITOR)
        ur = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        ua = create_user_with_role(ADMIN)
        ui = create_user_with_role(IT_HEAD)

        roles = ['admin', 'editor']
        response = self.query(
            self.users_q,
            variables={"roles": roles},
        )

        content = response.json()
        print(content)
        self.assertResponseNoErrors(response)
        self.assertEqual(sorted([int(each['id']) for each in content['data']['users']['results']]),
                         sorted([ue.id, ua.id]))

        roles = ['reviewer', 'editor']
        response = self.query(
            self.users_q,
            variables={"roles": roles},
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(sorted([int(each['id']) for each in content['data']['users']['results']]),
                         sorted([ur.id, ue.id]))

