from django.contrib.auth.models import Group

from apps.users.enums import USER_ROLE
from apps.users.models import User
from apps.users.serializers import UserSerializer
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import UserFactory

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name


class TestRegisterSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()

    def test_user_will_only_have_one_group(self):
        groups = Group.objects.filter(name__in=[ADMIN, GUEST])
        self.user.groups.set(groups)
        self.assertEqual(self.user.groups.count(), 2)

        self.user.save()
        self.assertEqual(self.user.groups.count(), 1)

