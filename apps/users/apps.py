from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = 'apps.users'

    def ready(self):

        super().ready()

        from apps.users.receivers import (  # noqa
            add_default_guest_portfolio,
            update_user_group_post_delete,
            update_user_group_post_save,
        )
