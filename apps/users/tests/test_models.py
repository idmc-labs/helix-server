from django.db.utils import IntegrityError

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio
from utils.tests import HelixTestCase
from utils.factories import UserFactory, MonitoringSubRegionFactory, CountryFactory

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


class TestPortfolio(HelixTestCase):
    def test_unique_constraints_check_regional(self):
        rc_data = dict(
            user=UserFactory.create(),
            role=USER_ROLE.REGIONAL_COORDINATOR,
            monitoring_sub_region=MonitoringSubRegionFactory.create()
        )
        Portfolio.objects.create(**rc_data)

        # lets alter user, should not be allowed
        rc_data['user'] = UserFactory.create()
        with self.assertRaisesMessage(IntegrityError, 'unique'):
            Portfolio.objects.create(**rc_data)

    def test_unique_constraints_check_regional_2(self):
        rc_data = dict(
            user=UserFactory.create(),
            role=USER_ROLE.REGIONAL_COORDINATOR,
            monitoring_sub_region=MonitoringSubRegionFactory.create()
        )
        Portfolio.objects.create(**rc_data)

        # lets alter user, should not be allowed
        rc_data['user'] = UserFactory.create()
        # additional info to irrelevant roles does not matter
        rc_data['country'] = CountryFactory.create()
        with self.assertRaisesMessage(IntegrityError, 'unique'):
            Portfolio.objects.create(**rc_data)

    # def test_unique_constraints_check_admin(self):
    #     admin_data = dict(
    #         user=UserFactory.create(),
    #         role=USER_ROLE.ADMIN,
    #     )
    #     Portfolio.objects.create(**admin_data)
    #
    #     # lets retry the same user
    #     with self.assertRaisesMessage(IntegrityError, 'unique'):
    #         Portfolio.objects.create(**admin_data)

    def test_unique_constraints_check_monitor(self):
        monitor_data = dict(
            user=UserFactory.create(),
            role=USER_ROLE.MONITORING_EXPERT,
            monitoring_sub_region=MonitoringSubRegionFactory.create(),
            country=CountryFactory.create(),
        )
        Portfolio.objects.create(**monitor_data)

        # lets try with different user
        monitor_data['user'] = UserFactory.create()
        with self.assertRaisesMessage(IntegrityError, 'unique'):
            Portfolio.objects.create(**monitor_data)
