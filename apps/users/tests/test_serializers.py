from django.test import RequestFactory
import mock

from apps.users.serializers import RegisterSerializer, UserSerializer, PortfolioSerializer
from apps.users.enums import USER_ROLE
from utils.tests import HelixTestCase, create_user_with_role
from utils.factories import MonitoringSubRegionFactory, UserFactory

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


class TestPortfolio(HelixTestCase):
    def setUp(self):
        self.admin = create_user_with_role(USER_ROLE.ADMIN.name)
        self.coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        self.expert = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)

        self.request = RequestFactory().post('/graphql')

    def test_coordinator_cannot_create_portfolio_for_other_region(self):
        self.request.user = self.coordinator
        other_region = MonitoringSubRegionFactory.create()
        other_user = UserFactory.create()
        self.context = dict(request=self.request)
        data = dict(
            role=USER_ROLE.MONITORING_EXPERT.value,
            monitoring_sub_region=other_region.id,
            user=other_user.id,
        )
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('monitoring_sub_region', serializer.errors)

        # same as the region of coordinator should be allowed
        data['monitoring_sub_region'] = self.coordinator.portfolios.first().monitoring_sub_region.id
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_coordinator_cannot_change_his_own_portfolio(self):
        self.request.user = self.coordinator
        self.context = dict(request=self.request)
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            user=self.request.user.id,
            monitoring_sub_region=other_region.id,  # change my own region
            role=USER_ROLE.REGIONAL_COORDINATOR.value,
        )
        serializer = PortfolioSerializer(
            instance=self.coordinator.portfolios.first(),
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
        self.assertEqual(serializer.errors['role'][0].code, 'cannot-modify-yourself', serializer.errors)

    def test_coordinator_cannot_upgrade_himself_to_admin(self):
        self.request.user = self.coordinator
        self.context = dict(request=self.request)
        data = dict(
            user=self.request.user.id,
            role=USER_ROLE.ADMIN.value,
        )
        serializer = PortfolioSerializer(
            instance=self.request.user.portfolios.first(),
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
        self.assertEqual(serializer.errors['role'][0].code, 'role-not-set', serializer.errors)

    def test_region_is_required_for_specific_roles(self):
        self.request.user = self.coordinator
        self.context = dict(request=self.request)
        other_user = UserFactory.create()
        data = dict(
            user=other_user.id,
            role=USER_ROLE.MONITORING_EXPERT.value,
        )
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('monitoring_sub_region', serializer.errors)
        self.assertEqual(serializer.errors['monitoring_sub_region'][0].code, 'required', serializer.errors)

        coordinator_region = self.coordinator.portfolios.first().monitoring_sub_region
        data['monitoring_sub_region'] = coordinator_region.id
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_admin_can_downgrade_other_admin_portfolio(self):
        self.request.user = self.admin
        other_region = MonitoringSubRegionFactory.create()
        admin2 = create_user_with_role(USER_ROLE.ADMIN.name)
        self.context = dict(request=self.request)
        data = dict(
            user=admin2.id,
            role=USER_ROLE.MONITORING_EXPERT.value,
            monitoring_sub_region=other_region.id
        )
        serializer = PortfolioSerializer(
            instance=admin2.portfolios.first(),
            data=data,
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_admin_cannot_change_his_own_portfolio(self):
        self.request.user = self.admin
        self.context = dict(request=self.request)
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            user=self.request.user.id,
            role=USER_ROLE.MONITORING_EXPERT.value,  # downgrading myself
            monitoring_sub_region=other_region.id
        )
        serializer = PortfolioSerializer(
            instance=self.request.user.portfolios.first(),
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)

    def test_admin_can_change_other_admin_or_coordinator_portfolio(self):
        self.request.user = self.admin
        self.context = dict(request=self.request)
        other_admin = create_user_with_role(USER_ROLE.ADMIN.name)
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            role=USER_ROLE.MONITORING_EXPERT.value,  # downgrading other admin
            monitoring_sub_region=other_region.id
        )
        serializer = PortfolioSerializer(
            instance=other_admin.portfolios.first(),
            data=data,
            context=self.context,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(other_admin.portfolios.count(), 1)
        self.assertEqual(other_admin.portfolios.first().role, USER_ROLE.MONITORING_EXPERT)

        other_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        old_region = other_coordinator.portfolios.first().monitoring_sub_region.id
        other_region = MonitoringSubRegionFactory.create()
        data = dict(
            role=USER_ROLE.MONITORING_EXPERT.value,
            monitoring_sub_region=other_region.id  # moving across the region
        )
        serializer = PortfolioSerializer(
            instance=other_coordinator.portfolios.first(),
            data=data,
            context=self.context,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(other_coordinator.portfolios.count(), 1)
        self.assertNotEqual(other_coordinator.portfolios.first().monitoring_sub_region.id,
                            old_region)
        self.assertEqual(other_coordinator.portfolios.first().monitoring_sub_region.id,
                         data['monitoring_sub_region'])

        # upgrading a user to admin is valid
        other_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        old_region = other_coordinator.portfolios.first().monitoring_sub_region.id
        data = dict(
            role=USER_ROLE.ADMIN.value,
        )
        serializer = PortfolioSerializer(
            instance=other_coordinator.portfolios.first(),
            data=data,
            context=self.context,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(other_coordinator.portfolios.count(), 1)
        self.assertIsNone(other_coordinator.portfolios.first().monitoring_sub_region)

    def test_coordinator_can_change_portfolio_of_people_in_same_region(self):
        self.request.user = self.coordinator
        coordinator_region = self.coordinator.portfolios.first().monitoring_sub_region
        self.context = dict(request=self.request)

        other_coordinator = create_user_with_role(USER_ROLE.REGIONAL_COORDINATOR.name)
        other_coordinator.portfolios.update(
            monitoring_sub_region=coordinator_region
        )
        data = dict(
            role=USER_ROLE.MONITORING_EXPERT.value,  # downgrade the user
            monitoring_sub_region=coordinator_region.id,
        )
        self.assertEqual(other_coordinator.portfolios.first().role, USER_ROLE.REGIONAL_COORDINATOR)
        serializer = PortfolioSerializer(
            instance=other_coordinator.portfolios.first(),
            data=data,
            context=self.context,
            partial=True
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        # and can create another regional coordinator
        other_user = UserFactory.create()
        data = dict(
            user=other_user.id,
            role=USER_ROLE.REGIONAL_COORDINATOR.value,
            monitoring_sub_region=coordinator_region.id,
        )
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(other_user.portfolios.first().role, USER_ROLE.REGIONAL_COORDINATOR)
        self.assertEqual(other_user.portfolios.first().monitoring_sub_region, coordinator_region)

    def test_admin_or_guest_portfolio_do_not_need_region(self):
        self.request.user = self.admin
        self.context = dict(request=self.request)
        other_user = UserFactory.create()
        data = dict(
            user=other_user.id,
            role=USER_ROLE.ADMIN.value,
        )
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(other_user.portfolios.first().role, USER_ROLE.ADMIN)
        self.assertEqual(other_user.portfolios.first().monitoring_sub_region, None)

        other_user2 = UserFactory.create()
        # already a guest
        data = dict(
            user=other_user2.id,
            role=USER_ROLE.GUEST.value,
        )
        serializer = PortfolioSerializer(
            data=data,
            context=self.context,
        )
        self.assertFalse(serializer.is_valid(), serializer.errors)
        self.assertIn('non_field_errors', serializer.errors)
