from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio
from utils.tests import HelixTestCase
from utils.factories import UserFactory

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name


class TestUserModel(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_user_is_at_least_a_guest(self):
        self.user = UserFactory.create()
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.portfolios.count(),
            1,
            self.user.portfolios.count()
        )
        self.assertEqual(
            self.user.portfolios.first().role,
            USER_ROLE.GUEST
        )

    def test_user_should_not_have_guest_if_other_exists(self):
        self.user = UserFactory.create()
        self.user.refresh_from_db()
        self.assertEqual(self.user.portfolios.count(), 1)

        Portfolio.objects.create(
            user=self.user,
            role=USER_ROLE.ADMIN
        )
        self.user.refresh_from_db()
        # adding any should remove guest
        self.assertEqual(self.user.portfolios.count(), 1)
        self.assertEqual(
            self.user.portfolios.first().role,
            USER_ROLE.ADMIN
        )

    def test_user_will_only_have_one_group(self):
        self.user = UserFactory.create()
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.portfolios.count(),
            1,
            self.user.portfolios.count()
        )
        self.assertEqual(
            self.user.groups.first().name,
            GUEST,
            self.user.portfolios.count()
        )
