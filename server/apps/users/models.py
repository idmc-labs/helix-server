from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    email = models.EmailField(verbose_name=_('Email Address'), unique=True)
    username = models.CharField(
        verbose_name=_('Username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    @property
    def role(self):
        if group := self.groups.first():
            return group.name
        return None

    def get_full_name(self):
        return f'{self.first_name}, {self.last_name}'

    def get_short_name(self):
        return self.first_name
