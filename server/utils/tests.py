import os
import shutil
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core import management
from django.test import TestCase, override_settings
from graphene_django.utils import GraphQLTestCase

from helix.settings import BASE_DIR
from utils.factories import UserFactory

User = get_user_model()
TEST_MEDIA_ROOT = 'media-temp'
TEST_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class CommonSetupClassMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # initialize roles
        management.call_command('init_roles')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # clear the temporary media files
        try:
            shutil.rmtree(os.path.join(BASE_DIR, TEST_MEDIA_ROOT))
        except FileNotFoundError:
            pass


@override_settings(
    EMAIL_BACKEND=TEST_EMAIL_BACKEND,
    MEDIA_ROOT=TEST_MEDIA_ROOT
)
class HelixGraphQLTestCase(CommonSetupClassMixin, GraphQLTestCase):
    GRAPHQL_URL = '/graphql'
    GRAPHQL_SCHEMA = 'helix.schema.schema'

    def force_login(self, user):
        self._client.force_login(user)

    def create_monitoring_expert(self):
        user = UserFactory.create()
        user.user_permissions.add(Permission.objects.get(codename='change_entry'))
        return user

    def create_user(self) -> User:
        raw_password = 'admin123'
        user = User.objects.create_user(
            username='admin',
            email='admin@email.com',
            password=raw_password,
        )
        user.raw_password = raw_password
        return user


def create_user_with_role(role: str) -> User:
    user = UserFactory.create()
    user.groups.set([Group.objects.get(name=role)])
    return user


class ImmediateOnCommitMixin(object):
    """
    Note: shamelessly copied from https://code.djangoproject.com/ticket/30457

    Will be redundant in immediate_on_commit function is actually implemented in Django 3.2
    Check this PR: https://github.com/django/django/pull/12944
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        def immediate_on_commit(func, using=None):
            func()
        # Context manager executing transaction.on_commit() hooks immediately
        # This is required when using a subclass of django.test.TestCase as all tests are wrapped in
        # a transaction that never gets committed.
        cls.on_commit_mgr = patch('django.db.transaction.on_commit', side_effect=immediate_on_commit)
        cls.on_commit_mgr.__enter__()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.on_commit_mgr.__exit__()


@override_settings(
    EMAIL_BACKEND=TEST_EMAIL_BACKEND,
    MEDIA_ROOT=TEST_MEDIA_ROOT
)
class HelixTestCase(CommonSetupClassMixin, ImmediateOnCommitMixin, TestCase):
    pass
