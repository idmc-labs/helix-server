from unittest.mock import patch

from django.test import RequestFactory

from apps.users.serializers import RegisterSerializer
from utils.tests import HelixTestCase


class TestRegisterSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = dict(
            email='admin@email.com',
            username='admin',
            password1='admin123',
            password2='admin123',
        )
        self.context = dict(
            request=RequestFactory().post('/graphql')
        )

    def test_register_creates_inactive_user(self):
        self.serializer = RegisterSerializer(data=self.data)
        self.assertTrue(self.serializer.is_valid(), self.serializer.errors)

        user = self.serializer.save()
        self.assertFalse(user.is_active)

    @patch('apps.users.serializers.send_activation_email')
    def test_register_sends_activation_email(self, send_activation_email):
        self.serializer = RegisterSerializer(data=self.data, context=self.context)
        self.assertTrue(self.serializer.is_valid(), self.serializer.errors)

        self.serializer.save()
        send_activation_email.assert_called_once()
