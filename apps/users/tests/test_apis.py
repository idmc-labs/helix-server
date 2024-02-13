import json

from django.contrib.auth.tokens import default_token_generator
from django.test import override_settings
from djoser.utils import encode_uid
import mock

from apps.users.enums import USER_ROLE
from apps.users.models import User
from utils.factories import UserFactory
from utils.tests import (
    HelixGraphQLTestCase,
    create_user_with_role,
    HelixAPITestCase
)


class TestLogin(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.login_query = '''
            mutation MyMutation ($email: String!, $password: String!){
                login(data: {email: $email, password: $password}) {
                    errors
                    result {
                        email
                    }
                }
            }
        '''
        self.login_query2 = '''
            mutation MyMutation ($input: LoginInputType!){
                login(data: $input) {
                    errors
                    ok
                    captchaRequired
                    result {
                        email
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
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        self.force_login(guest)

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

    @override_settings(
        MAX_LOGIN_ATTEMPTS=1,
        MAX_CAPTCHA_LOGIN_ATTEMPTS=2,
    )
    @mock.patch('apps.users.serializers.validate_hcaptcha')
    def test_too_many_logins_needs_captcha_and_more_will_throttle(self, validate):
        User._reset_login_cache(self.user.email)
        validate.return_value = False

        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['login']['errors'])
        self.assertTrue(content['data']['login']['ok'])

        # attempt 1
        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': 'worjsjlsjjssk'},
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertIn('the email or password is invalid.', json.dumps(content['data']['login']['errors']).lower())

        # attempt 2
        # try again and it should fail with captcha error
        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': 'worjsjlsjjssk'},
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertTrue(content['data']['login']['captchaRequired'])

        # attempt 3
        # invalid password and invalid captcha should raise invalid captcha
        response = self.query(
            self.login_query2,
            input_data={
                'email': self.user.email,
                'password': 'worjsjlsjjssk',
                'captcha': 'wrong=kaj',
                'siteKey': 'blaablaa',
            },
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertTrue(content['data']['login']['captchaRequired'])
        self.assertIn('the captcha is invalid.', json.dumps(content['data']['login']['errors']).lower())
        self.assertNotIn('the email or password is invalid.', json.dumps(content['data']['login']['errors']).lower())

        # again with captcha but wrong, throttles more login
        # attempt 4
        response = self.query(
            self.login_query2,
            input_data={
                'email': self.user.email,
                'password': 'worjsjlsjjssk',
                'captcha': 'wrong=kaj',
                'siteKey': 'blaablaa',
            },
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertIn('try again', json.dumps(content['data']['login']['errors']).lower())

    @override_settings(
        MAX_LOGIN_ATTEMPTS=1
    )
    @mock.patch('apps.users.serializers.validate_hcaptcha')
    def test_too_many_logins_with_valid_captcha(self, validate):
        User._reset_login_cache(self.user.email)
        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': self.user.raw_password},
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['login']['errors'])
        self.assertTrue(content['data']['login']['ok'])

        # attempt 1
        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': 'worjsjlsjjssk'},
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertIn('the email or password is invalid.', json.dumps(content['data']['login']['errors']).lower())

        # attempt 2
        # try again and it should fail with captcha error
        response = self.query(
            self.login_query2,
            input_data={'email': self.user.email, 'password': 'worjsjlsjjssk'},
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertTrue(content['data']['login']['captchaRequired'])

        # again with captcha but wrong
        validate.return_value = False
        response = self.query(
            self.login_query2,
            input_data={
                'email': self.user.email,
                'password': self.user.raw_password,
                'captcha': 'keyeyeyeye',
                'siteKey': 'keyeyeyeye',
            },
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertFalse(content['data']['login']['ok'])
        self.assertTrue(content['data']['login']['captchaRequired'])
        self.assertIn('the captcha is invalid.', json.dumps(content['data']['login']['errors']).lower())

        # with correct captcha
        validate.return_value = True
        response = self.query(
            self.login_query2,
            input_data={
                'email': self.user.email,
                'password': self.user.raw_password,
                'captcha': 'lakajl',
                'siteKey': 'lakajl',
            },
        )
        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertTrue(content['data']['login']['ok'], content)


class TestChangePassword(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.change_query = '''
            mutation MyMutation ($oldPassword: String!, $newPassword: String!){
                changePassword(data: {oldPassword: $oldPassword, newPassword: $newPassword}) {
                    errors
                    result {
                        email
                    }
                }
            }
        '''

    def test_valid_password_change(self):
        newpass = 'sdfjsjjkqjek'
        self.force_login(self.user)
        response = self.query(
            self.change_query,
            variables={'oldPassword': self.user.raw_password,
                       'newPassword': newpass},
        )

        content = response.json()

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['changePassword']['errors'])
        self.assertIsNotNone(content['data']['changePassword']['result'])
        self.assertIsNotNone(content['data']['changePassword']['result']['email'])

        self.user.refresh_from_db()
        assert self.user.check_password(newpass)

    @mock.patch('apps.users.serializers.validate_password')
    def test_invalid_password(self, validate):
        self.force_login(self.user)
        response = self.query(
            self.change_query,
            variables={
                'oldPassword': self.user.raw_password,
                'newPassword': 'abc',
            },
        )

        self.assertResponseNoErrors(response)
        assert validate.is_called()

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{'NAME': 'apps.users.password_validation.MaximumLengthValidator'}],
    )
    def test_maximum_password_length_validation(self):
        self.force_login(self.user)
        response = self.query(
            self.change_query,
            variables={
                'oldPassword': self.user.raw_password,
                'newPassword': '1W#$' * 100,
            },
        )
        content = json.loads(response.content)
        self.assertIsNotNone(content['data']['changePassword']['errors'])
        self.assertIn("newPassword", content['data']['changePassword']['errors'][0]["field"])


@mock.patch('apps.users.serializers.validate_hcaptcha')
class TestRegister(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.register = '''
            mutation Register ($input: RegisterInputType!){
                register(data: $input) {
                    errors
                }
            }
        '''
        self.input = {
            'email': 'admin@email.com',
            'password': 'jjaakksjsj1j2',
            'captcha': 'admin123',
            'siteKey': 'admin123',
        }

    def test_valid_registration(self, validate_captcha):
        validate_captcha.return_value = True
        response = self.query(
            self.register,
            input_data=self.input,
        )

        content = json.loads(response.content)

        self.assertResponseNoErrors(response)
        self.assertIsNone(content['data']['register']['errors'])

    def test_invalid_user_already_exists(self, validate_captcha):
        validate_captcha.return_value = True
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

    @override_settings(
        AUTH_PASSWORD_VALIDATORS=[{'NAME': 'apps.users.password_validation.MaximumLengthValidator'}],
    )
    def test_maximum_password_length_validation(self, validate_captcha):
        validate_captcha.return_value = True
        self.input['password'] = '#$@DFR$' * 100
        response = self.query(
            self.register,
            input_data=self.input,
        )
        content = json.loads(response.content)
        self.assertIsNotNone(content['data']['register']['errors'])
        self.assertIn("password", content['data']['register']['errors'][0]["field"])


class TestActivate(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.activate = '''
            mutation Activate ($input: ActivateInputType!) {
                activate(data: $input) {
                    errors
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
                    errors
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
            reviewing(page: 1, pageSize: 10) {
              totalCount
              results {
                id
                entry {
                  id
                }
              }
            }
          }
        }
        '''


class TestUserListSchema(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.users_q = '''
            query MyQuery($roles: [String!]) {
              users(filters: {roleIn: $roles}) {
                results {
                  id
                  email
                  portfoliosMetadata {
                    isAdmin
                  }
                }
              }
            }
        '''

    def test_filter_users(self):
        ue = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        ur = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        ua = create_user_with_role(USER_ROLE.ADMIN.name)
        guest = create_user_with_role(USER_ROLE.GUEST.name)

        self.force_login(guest)

        roles = [USER_ROLE.ADMIN.name, USER_ROLE.MONITORING_EXPERT.name]
        response = self.query(
            self.users_q,
            variables={"roles": roles},
        )

        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(sorted([int(each['id']) for each in content['data']['users']['results']]),
                         sorted([ue.id, ur.id, ua.id]))

        roles = [USER_ROLE.MONITORING_EXPERT.name]
        response = self.query(
            self.users_q,
            variables={"roles": roles},
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(sorted([int(each['id']) for each in content['data']['users']['results']]),
                         sorted([ur.id, ue.id]))

    def test_users_fields_access_based_on_authentication(self):
        users_q = '''
            query MyQuery {
              users {
                totalCount
                results {
                  id
                  portfoliosMetadata {
                    portfolioRole
                    portfolioRoleDisplay
                  }
                  permissions {
                    action
                  }
                  email
                }
              }
            }
        '''
        ua = create_user_with_role(USER_ROLE.ADMIN.name)
        urc = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        ud = create_user_with_role(USER_ROLE.DIRECTORS_OFFICE.name)
        urt = create_user_with_role(USER_ROLE.REPORTING_TEAM.name)
        um = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        guest = create_user_with_role(USER_ROLE.GUEST.name)

        expected_user_roles = {
            # Shown as GUEST with different PortfolioRole
            str(ua.pk): (USER_ROLE.GUEST.name, USER_ROLE.GUEST.label),   # Has Admin Role
            str(ud.pk): (USER_ROLE.GUEST.name, USER_ROLE.GUEST.label),   # Has DIRECTORS_OFFICE Role
            str(urt.pk): (USER_ROLE.GUEST.name, USER_ROLE.GUEST.label),  # Has REPORTING_TEAM Role
            str(urc.pk): (USER_ROLE.REGIONAL_COORDINATOR.name, USER_ROLE.REGIONAL_COORDINATOR.label),
            str(um.pk): (USER_ROLE.MONITORING_EXPERT.name, USER_ROLE.MONITORING_EXPERT.label),
            # Just GUEST
            str(guest.pk): (USER_ROLE.GUEST.name, USER_ROLE.GUEST.label),
        }
        total_user_count = len(expected_user_roles)

        self.force_login(guest)
        response = self.query(
            users_q
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['users']['totalCount'], total_user_count)
        self.assertEqual(set([item['email'] for item in content['data']['users']['results']]),
                         set([guest.email, None]))
        self.assertEqual(
            {
                item['id']: (
                    item['portfoliosMetadata']['portfolioRole'],
                    item['portfoliosMetadata']['portfolioRoleDisplay'],
                )
                for item in content['data']['users']['results']
            },
            expected_user_roles,
        )
        self.assertIn(
            None,
            [item['permissions'] for item in content['data']['users']['results']]
        )

        self.force_login(urc)
        response = self.query(
            users_q
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['users']['totalCount'], total_user_count)
        self.assertEqual(set([item['email'] for item in content['data']['users']['results']]),
                         set([urc.email, None]))
        self.force_login(ua)
        response = self.query(
            users_q
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(content['data']['users']['totalCount'], total_user_count)
        # we should not get all email
        self.assertIn(
            None,
            [item['email'] for item in content['data']['users']['results']]
        )

    def test_is_admin_field(self):
        create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        create_user_with_role(USER_ROLE.GUEST.name)
        admin_user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.force_login(admin_user)

        roles = [USER_ROLE.ADMIN.name]
        response = self.query(
            self.users_q,
            variables={"roles": roles},
        )
        content = response.json()
        self.assertResponseNoErrors(response)
        self.assertEqual(len(content['data']['users']['results']), 1)
        self.assertEqual(content['data']['users']['results'][0]['id'], str(admin_user.id))
        self.assertEqual(content['data']['users']['results'][0]['email'], admin_user.email)
        self.assertEqual(content['data']['users']['results'][0]['portfoliosMetadata']['isAdmin'], True)


class TestAPIMe(HelixAPITestCase):
    def test_me_api(self):
        user = UserFactory.create(
            email='ram@gmail.com'
        )
        self.authenticate(user)
        url = '/api/me/'
        response = self.client.get(url)
        assert response.status_code == 200
        data = response.data
        self.assertEqual(data['email'], user.email)

    def test_users_api(self):
        count = 3
        old_count = User.objects.count()
        users = UserFactory.create_batch(count)
        self.authenticate(users[0])
        url = '/api/users/'
        response = self.client.get(url)
        assert response.status_code == 200
        assert len(response.data) == count + old_count


class TestForgetResetPassword(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.forget_password_query = '''
            mutation MyMutation (
                $email: String!,
                $captcha: String!,
                $siteKey: String!
            ){
                generateResetPasswordToken(data: {
                    email: $email,
                    captcha: $captcha,
                    siteKey: $siteKey
                }) {
                    ok
                    errors
                }
            }
        '''

        self.reset_password_query = '''
            mutation MyMutation (
                $passwordResetToken: String!,
                $newPassword: String!,
                $uid: String!
            ){
                resetPassword(data: {
                        passwordResetToken: $passwordResetToken,
                        newPassword: $newPassword,
                        uid: $uid
                    }) {
                    ok
                    errors
                }
            }
        '''

    @mock.patch('apps.users.serializers.validate_hcaptcha')
    def test_should_generate_reset_password_token(self, validate):
        response = self.query(
            self.forget_password_query,
            variables={
                'email': self.user.email,
                'captcha': 'aaaaaaaa',
                'siteKey': 'bbbbbbbb',
            },
        )
        self.assertResponseNoErrors(response)

    def test_user_can_reset_password(self):
        # Create password reset token
        token = default_token_generator.make_token(self.user)
        uid = encode_uid(self.user.id)
        response = self.query(
            self.reset_password_query,
            variables={
                'passwordResetToken': token,
                'newPassword': '12343@#S#',
                'uid': uid
            },
        )
        self.assertResponseNoErrors(response)

        # Test link should expire if used by user
        response = self.query(
            self.reset_password_query,
            variables={
                'passwordResetToken': token,
                'newPassword': '12343@#S#',
                'uid': uid
            },
        )
        content = json.loads(response.content)
        self.assertFalse(content['data']['resetPassword']['ok'])
        message = content['data']['resetPassword']['errors'][0]['messages']
        self.assertEqual(message, 'The token is invalid.')

    def test_should_not_accept_invalid_token(self):
        token = 'MSwyMDIxLTA2LTA0IDE0OjM3O342jI1Ljg5NDQ4NSswMDowMA'
        uid = encode_uid(self.user.id)
        response = self.query(
            self.reset_password_query,
            variables={
                'passwordResetToken': token,
                'newPassword': '12343@#S#',
                'uid': uid
            },
        )
        content = json.loads(response.content)
        self.assertFalse(content['data']['resetPassword']['ok'])
        message = content['data']['resetPassword']['errors'][0]['messages']
        self.assertEqual(message, 'The token is invalid.')
