from django.db.models.signals import (
    post_save,
    m2m_changed,
)
from django.dispatch import receiver

from .models import User, Portfolio


def set_user_role(user: User) -> None:
    user.set_highest_role()


@receiver(post_save, sender=Portfolio)
def update_user_group(sender, instance, **kwargs):
    set_user_role(instance.user)


@receiver(m2m_changed, sender=User.portfolios.through)
def update_user_group_m2m(sender, instance, **kwargs):
    if kwargs['action'] in ['post_add', 'post_remove', 'post_clear']:
        set_user_role(instance)
