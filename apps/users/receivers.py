from django.db.models.signals import (
    post_save,
    post_delete,
)
from django.dispatch import receiver

from .enums import USER_ROLE
from .models import User, Portfolio


def set_user_role(user: User) -> None:
    user.set_highest_role()


def remove_guest_portfolio(user: User):
    if user.portfolios.count() > 1:
        Portfolio.objects.filter(
            user=user,
            role=USER_ROLE.GUEST
        ).delete()


def add_guest_portfolio(user: User):
    if user.portfolios.count() == 0:
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE.GUEST
        )


@receiver(post_save, sender=User)
def add_default_guest_portfolio(sender, instance, **kwargs):
    add_guest_portfolio(instance)
    set_user_role(instance)


@receiver(post_delete, sender=Portfolio)
def update_user_group_post_delete(sender, instance, **kwargs):
    add_guest_portfolio(instance.user)
    set_user_role(instance.user)


@receiver(post_save, sender=Portfolio)
def update_user_group_post_save(sender, instance, **kwargs):
    remove_guest_portfolio(instance.user)
    set_user_role(instance.user)
