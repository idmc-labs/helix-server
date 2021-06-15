from django.test import RequestFactory
import mock

from apps.users.serializers import (
    RegisterSerializer,
    UserSerializer,
    MonitoringExpertPortfolioSerializer,
    RegionalCoordinatorPortfolioSerializer,
    AdminPortfolioSerializer,
)
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import MonitoringSubRegionFactory, CountryFactory

ADMIN = USER_ROLE.ADMIN.name
GUEST = USER_ROLE.GUEST.name
MONITORING_EXPERT = USER_ROLE.MONITORING_EXPERT.name


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
        self.assertEqual(user.portfolios.get().role, USER_ROLE.GUEST)
        self.assertEqual(user.groups.get().name, USER_ROLE.GUEST.name)


class TestUserSerializer(HelixTestCase):
    def setUp(self) -> None:
        self.data = dict(
            first_name='firstname',
            last_name='last_name',
        )
        self.admin_user = create_user_with_role(ADMIN)
        self.reviewer = create_user_with_role(MONITORING_EXPERT)
        self.request = RequestFactory().post('/graphql')

    def test_valid_user_update(self):
        self.request.user = self.reviewer
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # admin updating another user
        self.request.user = self.admin_user
        context = dict(
            request=self.request
        )
        serializer = UserSerializer(instance=self.reviewer, data=self.data, context=context,
                                    partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class TestAdminPortfolioSerializer(HelixTestCase):
    def setUp(self):
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.request = RequestFactory().post('/graphql')

    def test_unique_admin_per_user(self):
        self.request.user = self.admin
        context = dict(
            request=self.request
        )
        data = dict(
            user=create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name).id,
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        other_admin = create_user_with_role(USER_ROLE.ADMIN.name)
        data = dict(
            user=other_admin.id
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'already-exists', serializer.errors)

    def test_only_admin_is_allowed(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        data = dict(
            user=self.expert.id,
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'not-allowed', serializer.errors)


class TestRegionalCoordinatorPortfolioSerializer(HelixTestCase):
    def setUp(self):
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.request = RequestFactory().post('/graphql')

    def test_unique_coordinator_per_region(self):
        self.request.user = self.admin
        context = dict(
            request=self.request
        )
        coordinator_region = self.coordinator.portfolios.first().monitoring_sub_region
        other_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        data = dict(
            user=other_coordinator.id,
            monitoring_sub_region=coordinator_region.id,
        )
        serializer = RegionalCoordinatorPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'already-occupied', serializer.errors)

        # same coordinator in multiple region is allowed
        data = dict(
            user=self.coordinator.id,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        serializer = RegionalCoordinatorPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

    def test_only_admin_is_allowed(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        data = dict(
            user=self.coordinator.id,
            monitoring_sub_region=MonitoringSubRegionFactory.create().id,
        )
        serializer = RegionalCoordinatorPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'not-allowed', serializer.errors)


class TestMonitoringExpertPortfolioSerializer(HelixTestCase):
    def setUp(self):
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.request = RequestFactory().post('/graphql')

    def test_admin_cannot_create(self):
        self.request.user = self.admin
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        monitoring_sub_region = MonitoringSubRegionFactory.create()
        data = dict(
            user=guest.id,
            monitoring_sub_region=monitoring_sub_region.id,
            countries=[each.id for each in CountryFactory.create_batch(3)]
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'not-allowed', serializer.errors)

    def test_coordinators_are_allowed_to_create(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        coordinator_region = self.coordinator.portfolios.first().monitoring_sub_region
        data = dict(
            user=guest.id,
            monitoring_sub_region=coordinator_region.id,
            countries=[each.id for each in CountryFactory.create_batch(3)]
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        # monitoring expert is not allowed
        self.request.user = self.expert
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        data = dict(
            user=guest.id,
            monitoring_sub_region=coordinator_region.id,
            countries=[each.id for each in CountryFactory.create_batch(3)]
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'not-allowed', serializer.errors)

    def test_unique_expert_per_country(self):
        monitoring_sub_region = MonitoringSubRegionFactory.create()
        country1 = CountryFactory.create(monitoring_sub_region=monitoring_sub_region)
        country2 = CountryFactory.create(monitoring_sub_region=monitoring_sub_region)

        expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name,
                                       monitoring_sub_region=monitoring_sub_region.id)
        portfolio = expert.portfolios.first()
        portfolio.countries.set([country1, country2])
        coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name,
                                            monitoring_sub_region=monitoring_sub_region.id)

        self.request.user = coordinator
        context = dict(
            request=self.request
        )

        # try and add another user to the same country, should fail
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        data = dict(
            user=guest.id,
            monitoring_sub_region=monitoring_sub_region.id,
            countries=[country1.id, country2.id],
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'already-occupied', serializer.errors)

        country3 = CountryFactory.create(monitoring_sub_region=monitoring_sub_region)
        data = dict(
            user=guest.id,
            monitoring_sub_region=monitoring_sub_region.id,
            countries=[country3.id]
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

    def test_user_can_only_have_one_expert_role_in_region(self):
        monitoring_sub_region = MonitoringSubRegionFactory.create()
        coordinator = create_user_with_role(
            USER_ROLE.REGIONAL_COORDINATOR.name,
            monitoring_sub_region=monitoring_sub_region.id
        )
        expert = create_user_with_role(
            USER_ROLE.MONITORING_EXPERT.name,
            monitoring_sub_region=monitoring_sub_region.id
        )

        self.request.user = coordinator
        context = dict(
            request=self.request
        )

        country2 = CountryFactory.create()
        data = dict(
            user=expert.id,
            # already exists, though its a different country but in the same monitoring region
            monitoring_sub_region=monitoring_sub_region.id,
            countries=[country2.id],
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'duplicate-portfolio', serializer.errors)

    def test_coordinator_not_allowed_to_add_in_other_region(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            user=guest.id,
            monitoring_sub_region=other_region.id,
            countries=[each.id for each in CountryFactory.create_batch(3)]
        )
        serializer = MonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors, serializer.errors)
        self.assertEqual('not-allowed-in-region', serializer.errors['non_field_errors'][0].code, serializer.errors)
