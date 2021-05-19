from django.test import RequestFactory
import mock

from apps.users.serializers import RegisterSerializer
from apps.users.enums import USER_ROLE
from apps.users.serializers import UserSerializer
from utils.tests import HelixTestCase, create_user_with_role

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name
MONITORING_EXPERT_REVIEWER = USER_ROLE.MONITORING_EXPERT_REVIEWER.name


@mock.patch('apps.users.serializers.validate_hcaptcha')
class TestRegisterSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = dict(
            email='admin@email.com',
            username='admin',
            password='12jjk2282i1kl',
            captcha='admin123',
            site_key='admin123',
        )
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_register_creates_inactive_user(self, validate_captcha):
        validate_captcha.return_value = True
        self.serializer = RegisterSerializer(data=self.data, context=self.context)
        self.assertTrue(self.serializer.is_valid(), self.serializer.errors)

        user = self.serializer.save()
        self.assertFalse(user.is_active)

    def test_registered_user_defaults_to_guest_role(self, validate_captcha):
        validate_captcha.return_value = True
        serializer = RegisterSerializer(data=self.data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.role, USER_ROLE[GUEST])


class TestUserSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = dict(
            first_name='firstname',
            last_name='last_name',
        )
        self.admin_user = create_user_with_role(ADMIN)
        self.reviewer = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.request = RequestFactory().post('/graphql')

    def test_valid_user_update(self):
        self.request.user = self.reviewer
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.request.user = self.admin_user
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_user_update_from_non_owner_and_non_admin(self):
        reviewer2 = create_user_with_role(MONITORING_EXPERT_REVIEWER)
        self.request.user = reviewer2
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

        # non-admin cannot change their role themselves
        self.request.user = self.reviewer
        self.data['role'] = USER_ROLE.ADMIN.value
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

    def test_invalid_role_or_activation_updates(self):
        # even admins are not allowed to change their own roles
        self.request.user = self.admin_user

        self.data['role'] = USER_ROLE.MONITORING_EXPERT_EDITOR.value
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.request.user, data=self.data, context=context,
                                    partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)

        # lets keep the role as is
        self.data['role'] = USER_ROLE.ADMIN.value
        serializer = UserSerializer(instance=self.request.user, data=self.data, context=context,
                                    partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # any user is not allowed to activate/deactivate themselves
        self.data['is_active'] = False
        serializer = UserSerializer(instance=self.request.user, data=self.data, context=context,
                                    partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('is_active', serializer.errors)
