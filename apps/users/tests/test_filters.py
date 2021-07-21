from apps.users.filters import UserFilter
from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import (
    UserFactory,
    CountryFactory,
    MonitoringSubRegionFactory
)


class TestUserFilter(HelixTestCase):
    def setUp(self) -> None:
        pass

    def test_filter_by_full_name(self):
        u1 = UserFactory.create(first_name='abc', last_name='def')
        UserFactory.create(first_name='bcd', last_name='efa')
        u3 = UserFactory.create(first_name='abc', last_name='dzy')

        data = dict(full_name='abc d')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1, u3])

        data = dict(full_name='def')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1])

        data = dict(full_name='zy')
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u3])

    def test_filter_users_defaults_to_active_only(self):
        u1 = UserFactory.create(first_name='abc', last_name='def', is_active=False)
        u2 = UserFactory.create(first_name='bcd', last_name='efa', is_active=True)

        data = dict()
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u2])

        data['include_inactive'] = True
        filtered = UserFilter(data).qs
        self.assertEqual([each for each in filtered], [u1, u2])

    def test_filter_user_by_role(self):
        u1 = create_user_with_role(role=USER_ROLE.ADMIN.name)
        u2 = create_user_with_role(role=USER_ROLE.REGIONAL_COORDINATOR.name)

        c1 = CountryFactory.create()
        u3 = create_user_with_role(role=USER_ROLE.MONITORING_EXPERT.name,
                                   monitoring_sub_region=c1.monitoring_sub_region.id,
                                   country=c1.id)
        for country in CountryFactory.create_batch(5):
            Portfolio.objects.create(
                user=u3,
                role=USER_ROLE.MONITORING_EXPERT,
                monitoring_sub_region=country.monitoring_sub_region,
                country=country,
            )
        qs = UserFilter(
            data=dict(
                role_in=[USER_ROLE.ADMIN.name]
            )
        ).qs
        self.assertIn(u1, qs)
        self.assertNotIn(u2, qs)

        qs = UserFilter(
            data=dict(
                role_not_in=[USER_ROLE.ADMIN.name]
            )
        ).qs
        self.assertIn(u2, qs)
        self.assertNotIn(u1, qs)

        # test for monitoring expert
        qs = UserFilter(
            data=dict(
                role_in=[USER_ROLE.MONITORING_EXPERT.name]
            )
        ).qs
        self.assertIn(u3, qs)
        self.assertEqual(1, len(qs))
        self.assertNotIn(u1, qs)
        self.assertNotIn(u2, qs)

    def test_filter_user_by_monitoring_sub_region(self):
        u1 = create_user_with_role(role=USER_ROLE.ADMIN.name)
        monitoring_sub_region = MonitoringSubRegionFactory.create()
        u2 = create_user_with_role(role=USER_ROLE.REGIONAL_COORDINATOR.name,
                                   monitoring_sub_region=monitoring_sub_region.id)
        u3 = create_user_with_role(role=USER_ROLE.REGIONAL_COORDINATOR.name)

        qs = UserFilter(
            data=dict(
                monitoring_sub_region_in=[monitoring_sub_region.id]
            )
        ).qs
        self.assertIn(u2, qs)
        self.assertNotIn(u1, qs)
        self.assertNotIn(u3, qs)

        qs = UserFilter(
            data=dict(
                monitoring_sub_region_not_in=[monitoring_sub_region.id]
            )
        ).qs
        self.assertNotIn(u2, qs)
        self.assertIn(u1, qs)
        self.assertIn(u3, qs)
