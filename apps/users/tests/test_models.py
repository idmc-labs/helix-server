from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase
from utils.factories import UserFactory

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name


class TestRegisterSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.user = UserFactory.create()

    def test_user_will_only_have_one_group(self):
        # TODO portfolio
        ...
