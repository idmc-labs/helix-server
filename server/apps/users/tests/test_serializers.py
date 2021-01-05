
from django.test import RequestFactory

from apps.users.serializers import RegisterSerializer
from apps.users.enums import USER_ROLE
from apps.users.serializers import UserSerializer
from utils.tests import HelixTestCase, create_user_with_role

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name
MONITORING_EXPERT_REVIEWER = USER_ROLE.MONITORING_EXPERT_REVIEWER.name


class TestRegisterSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = dict(
            email='admin@email.com',
            username='admin',
            password='admin123',
        )
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_register_creates_inactive_user(self):
        self.serializer = RegisterSerializer(data=self.data, context=self.context)
        self.assertTrue(self.serializer.is_valid(), self.serializer.errors)

        user = self.serializer.save()
        self.assertFalse(user.is_active)

    def test_registered_user_defaults_to_guest_role(self):
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

        # user cannot change their role themselves
        self.request.user = self.reviewer
        self.data['role'] = USER_ROLE.ADMIN.value
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
