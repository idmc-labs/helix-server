from __future__ import annotations
import logging
from collections import OrderedDict

from django.core.cache import cache
from django.db import models
from django.db.models.constraints import UniqueConstraint
from django.db.models.query import QuerySet
from django.contrib.auth.models import AbstractUser, Group
from django.contrib.postgres.aggregates import ArrayAgg
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum


from .roles import PERMISSIONS, USER_ROLE

logger = logging.getLogger(__name__)


class User(AbstractUser):
    email = models.EmailField(verbose_name=_('Email Address'), unique=True)
    username = models.CharField(
        verbose_name=_('Username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
    )
    full_name = models.CharField(verbose_name=_('Full Name'), max_length=512,
                                 null=True, blank=True,
                                 help_text=_('Full name is auto generated.'))

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @classmethod
    def can_update_user(cls, user_id: int, authenticated_user: User) -> bool:
        return authenticated_user.has_perm('users.change_user') or\
            user_id == authenticated_user.id

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        """
        Generates data for Excel sheets based on filters applied to the user queryset.

        Parameters:
            user_id: The ID of the user requesting the data.
            filters: A dictionary of filters to apply to the user queryset.

        Returns:
            A dictionary containing headers, data, formulae, and a transformer function for Excel sheet generation.
        """
        from apps.users.filters import UserFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='ID',
            date_joined='Date Joined',
            full_name='Name',
            portfolio_role='Role',
            is_admin='Admin',
            is_directors_office="Director's Office",
            is_reporting_team='Reporting Team',
            is_active='Active',
        )

        users = UserFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.order_by('date_joined').annotate(
            portfolio_roles=ArrayAgg(models.F('portfolios__role'), distinct=True),
            roles=ArrayAgg(models.F('portfolios__role'), distinct=True),
        ).annotate(
            portfolio_role=models.Case(
                models.When(
                    portfolio_roles__overlap=[USER_ROLE.REGIONAL_COORDINATOR.value],
                    then=USER_ROLE.REGIONAL_COORDINATOR.value
                ),
                models.When(
                    portfolio_roles__overlap=[USER_ROLE.MONITORING_EXPERT.value],
                    then=USER_ROLE.MONITORING_EXPERT.value
                ),
                default=USER_ROLE.GUEST.value,
                output_field=models.IntegerField(),
            ),
        )

        ROLE_TO_HEADER_MAPPING = {
            USER_ROLE.ADMIN: 'is_admin',
            USER_ROLE.DIRECTORS_OFFICE: 'is_directors_office',
            USER_ROLE.REPORTING_TEAM: 'is_reporting_team',
        }

        def transformer(datum):
            transformed_data = {**datum, 'portfolio_role': USER_ROLE.get(datum['portfolio_role']).label}
            for role, header in ROLE_TO_HEADER_MAPPING.items():
                transformed_data[header] = "Yes" if role in datum['roles'] else "No"
            transformed_data['is_active'] = 'Yes' if datum['is_active'] else 'No'
            return transformed_data

        excluded_headers = ['is_admin', 'is_directors_office', 'is_reporting_team']
        filtered_headers = [header for header in headers.keys() if header not in excluded_headers]
        filtered_headers.append('roles')

        return {
            'headers': headers,
            'data': users.values(*filtered_headers),
            'formulae': None,
            'transformer': transformer,
        }

    @staticmethod
    def _reset_login_cache(email: str):
        cache.delete_many([
            User._last_login_attempt_cache_key(email),
            User._login_attempt_cache_key(email),
        ])

    # login attempts related stuff

    @staticmethod
    def _set_login_attempt(email: str, value: int):
        return cache.set(User._login_attempt_cache_key(email), value)

    @staticmethod
    def _get_login_attempt(email: str):
        return cache.get(User._login_attempt_cache_key(email), 0)

    @staticmethod
    def _set_last_login_attempt(email: str, value: float):
        return cache.set(User._last_login_attempt_cache_key(email), value)

    @staticmethod
    def _get_last_login_attempt(email: str):
        return cache.get(User._last_login_attempt_cache_key(email), 0)

    @staticmethod
    def _last_login_attempt_cache_key(email: str) -> str:
        return f'{email}_lga_time'

    @staticmethod
    def _login_attempt_cache_key(email: str) -> str:
        return f'{email}_lga'

    # end login attempts related stuff

    @property
    def permissions(self) -> list[dict]:
        return [
            {'action': k, 'entities': list(v)} for k, v in
            # FIXME: We should merge the permissions instead of getting the
            # role from the highest one
            PERMISSIONS[self.highest_role].items()
        ]

    def set_highest_role(self) -> None:
        try:
            groups = Group.objects.filter(name__in=[each.role.name for each in self.portfolios.all()])
            self.groups.set(groups)
        except Group.DoesNotExist:
            logger.warning(f'A group might be missing: {", ".join([each.role.name for each in self.portfolios.all()])}')

    @property
    def highest_role(self) -> USER_ROLE:
        return Portfolio.get_highest_role(self)

    def get_full_name(self):
        return ' '.join([
            name for name in [self.first_name, self.last_name] if name
        ]) or self.email

    def get_short_name(self):
        return self.first_name

    def save(self, *args, **kwargs):
        self.full_name = self.get_full_name()
        return super().save(*args, **kwargs)


class Portfolio(models.Model):
    user = models.ForeignKey(
        'User', verbose_name=_('User'),
        related_name='portfolios', on_delete=models.CASCADE
    )
    role = enum.EnumField(
        USER_ROLE,
        verbose_name=_('Role'),
        default=USER_ROLE.GUEST,
        blank=False
    )
    monitoring_sub_region = models.ForeignKey(
        'country.MonitoringSubRegion', verbose_name=_('Monitoring Sub-region'),
        related_name='portfolios', on_delete=models.CASCADE,
        null=True, blank=True
    )
    country = models.OneToOneField(
        'country.Country',
        verbose_name=_('Country'),
        related_name='portfolio',
        blank=True, null=True,
        on_delete=models.CASCADE,
    )

    objects = models.Manager()

    def user_can_alter(self, user: User) -> bool:
        if user.highest_role == USER_ROLE.ADMIN:
            return True
        # FIXME: We should not use highest_role for anything except ADMIN and GUEST
        if user.highest_role == USER_ROLE.REGIONAL_COORDINATOR:
            # regional coordinator cannot alter admins or regional coordinators
            return self.role not in [USER_ROLE.ADMIN, USER_ROLE.REGIONAL_COORDINATOR]
        return False

    @classmethod
    def get_role_allows_region_map(cls) -> dict:
        region_allowed_in = [
            USER_ROLE.REGIONAL_COORDINATOR,
        ]
        countries_allowed_in = [
            USER_ROLE.MONITORING_EXPERT,
        ]
        return {
            role.name: {
                'label': role.label,
                'allows_region': role in region_allowed_in,
                'allows_countries': role in countries_allowed_in,
            } for role in USER_ROLE
        }

    @classmethod
    def get_coordinators(cls) -> QuerySet:
        return cls.objects.filter(
            role=USER_ROLE.REGIONAL_COORDINATOR,
        )

    @classmethod
    def get_coordinator(cls, ms_region: int) -> Portfolio:
        """Only one coordinator per region"""
        return cls.get_coordinators().filter(
            monitoring_sub_region=ms_region
        ).first()

    @classmethod
    def get_highest_role(cls, user: User) -> USER_ROLE:
        # region based role is not required
        roles = list(user.portfolios.values_list('role', flat=True))

        if USER_ROLE.ADMIN in roles:
            return USER_ROLE.ADMIN
        if USER_ROLE.REGIONAL_COORDINATOR in roles:
            return USER_ROLE.REGIONAL_COORDINATOR
        if USER_ROLE.MONITORING_EXPERT in roles:
            return USER_ROLE.MONITORING_EXPERT
        if USER_ROLE.DIRECTORS_OFFICE in roles:
            return USER_ROLE.DIRECTORS_OFFICE
        if USER_ROLE.REPORTING_TEAM in roles:
            return USER_ROLE.REPORTING_TEAM
        return USER_ROLE.GUEST

    @property
    def permissions(self) -> list[dict]:
        return [
            {'action': k, 'entities': list(v)} for k, v in
            PERMISSIONS[USER_ROLE[self.role]].items()
        ]

    def save(self, *args, **kwargs):
        if self.role == USER_ROLE.ADMIN:
            self.monitoring_sub_region = None
            self.country = None
        elif self.role == USER_ROLE.REGIONAL_COORDINATOR:
            self.country = None
        elif self.role == USER_ROLE.DIRECTORS_OFFICE:
            self.monitoring_sub_region = None
            self.country = None
        elif self.role == USER_ROLE.REPORTING_TEAM:
            self.monitoring_sub_region = None
            self.country = None
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['role', 'monitoring_sub_region'],
                             condition=models.Q(role=USER_ROLE.REGIONAL_COORDINATOR),
                             name='unique_for_monitoring_sub_region'),
            UniqueConstraint(fields=['role', 'country'],
                             condition=models.Q(role=USER_ROLE.MONITORING_EXPERT),
                             name='unique_for_country'),
        ]
