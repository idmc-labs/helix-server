import logging

from django.db import models
from django.contrib.auth.models import AbstractUser, Group
from django.utils.translation import gettext_lazy as _

from .roles import PERMISSIONS, USER_ROLE

logger = logging.getLogger(__name__)


class User(AbstractUser):
    email = models.EmailField(verbose_name=_('Email Address'), unique=True)
    username = models.CharField(
        verbose_name=_('Username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @classmethod
    def can_update_user(cls, user_id: int, authenticated_user: 'User') -> bool:
        return authenticated_user.has_perm('users.change_user') or\
                user_id == authenticated_user.id

    def set_role(self, role: int) -> None:
        try:
            group = Group.objects.get(name=USER_ROLE.get(role).name)
            self.groups.set([group])
        except AttributeError:
            logger.warning(f'User role with {role=} does not exist.')
        except Group.DoesNotExist:
            logger.warning(f'Group(UserRole) with name {USER_ROLE[role].name} does not exist.')

    @property
    def role(self):
        if group := self.groups.first():
            return USER_ROLE[group.name]
        return None

    @property
    def permissions(self):
        if self.role is not None and self.role in PERMISSIONS:
            return [{'action': k, 'entities': list(v)} for k, v in
                    PERMISSIONS[self.role].items()]
        return []

    def get_full_name(self):
        return ' '.join([
            name for name in [self.first_name, self.last_name] if name
        ]) or self.email

    @property
    def full_name(self):
        return self.get_full_name()

    def get_short_name(self):
        return self.first_name
