from __future__ import annotations
import logging

from django.core.cache import cache
from django.db import models
from django.db.models.query import QuerySet
from django.contrib.auth.models import AbstractUser, Group
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

    def set_highest_role(self) -> None:
        role = Portfolio.get_highest_role(self)
        try:
            group = Group.objects.get(name=role.name)
            self.groups.set([group])
        except AttributeError:
            logger.warning(f'User role with {role=} does not exist.')
        except Group.DoesNotExist:
            logger.warning(f'Group(UserRole) with name {USER_ROLE[role].name} does not exist.')

    def get_full_name(self):
        return ' '.join([
            name for name in [self.first_name, self.last_name] if name
        ]) or self.email

    def get_short_name(self):
        return self.first_name

    def save(self, *args, **kwargs):
        self.full_name = self.get_full_name()
        instance = super().save(*args, **kwargs)
        return instance


class Portfolio(models.Model):
    user = models.ForeignKey(
        'User', verbose_name=_('User'),
        related_name='portfolios', on_delete=models.CASCADE
    )
    role = enum.EnumField(
        USER_ROLE,
        verbose_name=_('Role'),
        blank=False
    )
    monitoring_sub_region = models.ForeignKey(
        'country.MonitoringSubRegion', verbose_name=_('Monitoring Sub-region'),
        related_name='portfolios', on_delete=models.CASCADE,
        null=True, blank=True
    )

    objects = models.Manager()

    @classmethod
    def get_coordinators(cls) -> QuerySet:
        return cls.objects.filter(
            role=USER_ROLE.REGIONAL_COORDINATOR,
        )

    @classmethod
    def get_coordinator(cls, ms_region: int) -> Portfolio:
        return cls.get_coordinators.get(
            monitoring_sub_region=ms_region
        )

    @classmethod
    def get_highest_role(cls, user: User) -> USER_ROLE:
        # region based role is not required
        portfolios = user.portfolios.all()

        if USER_ROLE.ADMIN in portfolios:
            return USER_ROLE.ADMIN
        if USER_ROLE.REGIONAL_COORDINATOR in portfolios:
            return USER_ROLE.REGIONAL_COORDINATOR
        if USER_ROLE.MONITORING_EXPERT in portfolios:
            return USER_ROLE.MONITORING_EXPERT
        return USER_ROLE.GUEST

    @property
    def permissions(self) -> list[dict]:
        return [
            {'action': k, 'entities': list(v)} for k, v in
            PERMISSIONS[self.role].items()
        ]

    def set_role(self, role: USER_ROLE) -> None:
        try:
            group = Group.objects.get(name=USER_ROLE.get(role).name)
            self.user.groups.add([group])
        except AttributeError:
            logger.warning(f'User role with {role=} does not exist.')
        except Group.DoesNotExist:
            logger.warning(f'Group(UserRole) with name {USER_ROLE[role].name} does not exist.')

    def _clean_fields(self) -> None:
        # following roles are not allowed along with monitoring region
        if self.role in [USER_ROLE.ADMIN, USER_ROLE.GUEST]:
            self.monitoring_sub_region = None

    def save(self, *args, **kwargs):
        self._clean_fields()
        return super().save(*args, **kwargs)

    class Meta:
        unique_together = (('user', 'role', 'monitoring_sub_region'),)
