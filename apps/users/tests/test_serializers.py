from django.test import RequestFactory
import mock

from apps.users.serializers import (
    RegisterSerializer,
    UserSerializer,
    BulkMonitoringExpertPortfolioSerializer,
    RegionalCoordinatorPortfolioSerializer,
    AdminPortfolioSerializer,
)
from apps.users.models import Portfolio
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
            register=True,
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        other_admin = create_user_with_role(USER_ROLE.ADMIN.name)
        data = dict(
            user=other_admin.id,
            register=True,
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'already-exists', serializer.errors)

        # removing is fine
        data = dict(
            user=other_admin.id,
            register=False,
        )
        serializer = AdminPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        other_admin.refresh_from_db()
        self.assertEqual(other_admin.highest_role, USER_ROLE.GUEST)

    def test_only_admin_is_allowed(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        data = dict(
            user=self.expert.id,
            register=True,
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
            region=monitoring_sub_region.id,
            portfolios=[dict(
                user=guest.id,
                country=each.id
            ) for each in CountryFactory.create_batch(3)]
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
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
            region=coordinator_region.id,
            portfolios=[],
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
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
            region=coordinator_region.id,
            portfolios=[dict(
                user=guest.id,
                country=each.id
            ) for each in CountryFactory.create_batch(3, monitoring_sub_region=coordinator_region)]
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
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
                                       country=country1.id)
        portfolio1 = country1.monitoring_expert
        # also add him to other country
        portfolio2 = Portfolio.objects.create(
            user=expert,
            role=USER_ROLE.MONITORING_EXPERT,
            monitoring_sub_region=country2.monitoring_sub_region,
            country=country2,
        )
        coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name,
                                            monitoring_sub_region=monitoring_sub_region.id)
        coordinator_region = coordinator.portfolios.first().monitoring_sub_region

        self.request.user = coordinator
        context = dict(
            request=self.request
        )

        # its okay to alter: same users across different occupied countries
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        data = dict(
            region=coordinator_region.id,
            portfolios=[dict(
                id=portfolio1.id,
                user=guest.id,
                country=portfolio1.country.id,
            ), dict(
                id=portfolio2.id,
                user=guest.id,
                country=portfolio2.country.id,
            )]
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        # try and add another user to the same country, should fail
        # it no longer fails, we overwrite the monitoring expert in the country
        # self.assertEqual(serializer.errors['country'][0].code, 'already-occupied', serializer.errors)
        # The big assumption: portfolio for each country and region should already exist

    def test_coordinator_not_allowed_to_add_in_other_region(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            region=other_region.id,
            portfolios=[
                dict(user=guest.id, country=each.id)
                for each in CountryFactory.create_batch(3, monitoring_sub_region=other_region)
            ]
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors, serializer.errors)
        self.assertEqual('not-allowed-in-region', serializer.errors['non_field_errors'][0].code, serializer.errors)

    def test_invalid_countries_from_different_region(self):
        self.request.user = self.coordinator
        context = dict(
            request=self.request
        )
        guest = create_user_with_role(USER_ROLE.GUEST.name)
        other_region = MonitoringSubRegionFactory.create()
        coordinator_region = self.coordinator.portfolios.first().monitoring_sub_region
        data = dict(
            region=coordinator_region.id,
            portfolios=[
                dict(user=guest.id, country=each.id)
                for each in CountryFactory.create_batch(3, monitoring_sub_region=other_region)
            ]
        )
        serializer = BulkMonitoringExpertPortfolioSerializer(
            data=data,
            context=context
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors, serializer.errors)
        self.assertEqual('region-mismatch', serializer.errors['non_field_errors'][0].code, serializer.errors)
