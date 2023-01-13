from datetime import timedelta
from django.utils import timezone
from apps.crisis.models import Crisis
from apps.event.models import Event
from apps.users.enums import USER_ROLE
from utils.factories import (
    CrisisFactory,
    DisasterSubTypeFactory,
    CountryFactory,
    EventFactory,
    MonitoringSubRegionFactory,
    CountryRegionFactory,
    CountrySubRegionFactory,
)
from utils.tests import create_user_with_role
from utils.tests import HelixTestCase
from utils.validations import is_child_parent_dates_valid


class TestEventModel(HelixTestCase):
    def setUp(self) -> None:
        self.data = {
            "crisis": CrisisFactory(),
            "name": "Event1",
            "event_type": Crisis.CRISIS_TYPE.DISASTER,
            "glide_numbers": ["glide-number"],
            "disaster_sub_type": DisasterSubTypeFactory(),
        }

    def test_valid_clean(self):
        event = Event(**self.data)
        self.assertIsNone(event.clean())


class TestGenericValidator(HelixTestCase):
    def test_is_child_parent_dates_valid(self):
        func = is_child_parent_dates_valid

        c_start = _c_start = timezone.now()
        c_end = _c_end = timezone.now() + timedelta(days=10)
        p_start = _p_start = c_start - timedelta(days=100)

        errors = func(c_start, c_end, p_start, 'parent')
        self.assertFalse(errors)

        c_start = _c_end + timedelta(days=1)
        errors = func(c_start, c_end, p_start, 'parent')
        self.assertTrue(errors)
        self.assertIn('start_date', errors)

        c_start = _c_start

        p_start = _c_start + timedelta(days=1)
        errors = func(c_start, c_end, p_start, 'parent')
        self.assertTrue(errors)
        self.assertIn('start_date', errors)

        p_start = None
        errors = func(c_start, c_end, p_start, 'parent')
        self.assertFalse(errors)

        p_start = _p_start
        c_start = None
        errors = func(c_start, c_end, p_start, 'parent')
        self.assertFalse(errors)

    def test_regional_coordinators(self):
        region_1 = CountryRegionFactory.create()
        sub_region_1 = CountrySubRegionFactory.create()
        monitoring_sub_region_1 = MonitoringSubRegionFactory.create()
        country_1 = CountryFactory.create(
            name='Australia',
            monitoring_sub_region=monitoring_sub_region_1,
            region=region_1,
            sub_region=sub_region_1,
        )
        region_2 = CountryRegionFactory.create()
        sub_region_2 = CountrySubRegionFactory.create()
        monitoring_sub_region_2 = MonitoringSubRegionFactory.create()
        country_2 = CountryFactory.create(
            name='Nepal',
            monitoring_sub_region=monitoring_sub_region_2,
            region=region_2,
            sub_region=sub_region_2,
        )

        # Create ME and RC in monitoring sub region
        monitoring_expert_1 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            monitoring_sub_region=monitoring_sub_region_1.id,
            country=country_1.id,
        )
        regional_coordinator_1 = create_user_with_role(
            USER_ROLE.REGIONAL_COORDINATOR.name,
            country=country_1.id,
            monitoring_sub_region=monitoring_sub_region_1.id,
        )

        # Create ME and RC in another monitoring sub region
        monitoring_expert_2 = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            country=country_2.id,
            monitoring_sub_region=monitoring_sub_region_2.id,
        )
        regional_coordinator_2 = create_user_with_role(
            USER_ROLE.REGIONAL_COORDINATOR.name,
            country=country_2.id,
            monitoring_sub_region=monitoring_sub_region_2.id,
        )

        event_1 = EventFactory.create(
            assigner=regional_coordinator_1,
            assignee=monitoring_expert_1,
            countries=[country_1]
        )
        event_2 = EventFactory.create(
            assigner=regional_coordinator_2,
            assignee=monitoring_expert_2,
            countries=[country_2]
        )
        event_3 = EventFactory.create(
            assigner=regional_coordinator_1,
            assignee=monitoring_expert_1,
            countries=[country_1, country_2]
        )

        # Test should return single regional coordinator if actor is same monitoring region
        event_1_only_regional_coordinators = Event.regional_coordinators(event_1, actor=monitoring_expert_1)
        event_2_only_regional_coordinators = Event.regional_coordinators(event_2, actor=monitoring_expert_2)
        # Test should return multiple regional coordinators if actor is from different monitoring region
        event_1_regional_coordinators = Event.regional_coordinators(event_1, actor=monitoring_expert_2)
        event_2_regional_coordinators = Event.regional_coordinators(event_2, actor=monitoring_expert_1)

        # Test should return multiple regional coordinators because it has country from different monitoring regions
        event_3_regional_coordinators = Event.regional_coordinators(event_3)

        self.assertEqual(
            set([user['id'] for user in event_1_only_regional_coordinators]),
            set([regional_coordinator_1.id])
        )
        self.assertEqual(
            set([user['id'] for user in event_2_only_regional_coordinators]),
            set([regional_coordinator_2.id])
        )
        self.assertEqual(
            set([user['id'] for user in event_1_regional_coordinators]),
            set([regional_coordinator_1.id, regional_coordinator_2.id])
        )
        self.assertEqual(
            set([user['id'] for user in event_2_regional_coordinators]),
            set([regional_coordinator_1.id, regional_coordinator_2.id])
        )
        self.assertEqual(
            set([user['id'] for user in event_3_regional_coordinators]),
            set([regional_coordinator_1.id, regional_coordinator_2.id])
        )
