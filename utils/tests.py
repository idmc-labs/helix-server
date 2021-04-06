import os
import shutil
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core import management
from django.test import TestCase, override_settings
# dramatiq test case: setupclass is not properly called
# from django_dramatiq.test import DramatiqTestCase
from graphene_django.utils import GraphQLTestCase
from rest_framework.test import APITestCase

from apps.entry.models import FigureCategory, FigureTerm
from apps.entry.constants import STOCK, FLOW
from helix.settings import BASE_DIR
from utils.factories import UserFactory

User = get_user_model()
TEST_MEDIA_ROOT = 'media-temp'
TEST_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
TEST_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
TEST_DRAMATIQ_BROKER = {
    "BROKER": "dramatiq.brokers.stub.StubBroker",
    "OPTIONS": {},
    "MIDDLEWARE": [
        "dramatiq.middleware.AgeLimit",
        "dramatiq.middleware.TimeLimit",
        "dramatiq.middleware.Callbacks",
        "dramatiq.middleware.Pipelines",
        "dramatiq.middleware.Retries",
        "django_dramatiq.middleware.DbConnectionsMiddleware",
        "django_dramatiq.middleware.AdminMiddleware",
    ]
}
TEST_CACHES = None


class CommonSetupClassMixin:
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # initialize roles
        management.call_command('init_roles')
        # add necessary figure categories
        FigureCategory.objects.bulk_create([
            FigureCategory(type=STOCK, name='IDPs'),
            FigureCategory(type=FLOW, name='New Displacement'),
        ])
        # Add the figure terms
        FigureTerm.objects.bulk_create([
            FigureTerm(
                is_housing_related=True,
                name='destroyed housing',
                identifier='DESTROYED_HOUSING',
            ),
            FigureTerm(
                is_housing_related=False,
                name='Evacuated',
                identifier='EVACUATED',
            ),
        ])

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # clear the temporary media files
        try:
            shutil.rmtree(os.path.join(BASE_DIR, TEST_MEDIA_ROOT))
        except FileNotFoundError:
            pass

    def assertResponseNoErrors(self, response):
        content = response.json()
        self.assertIsNone(content.get('errors'), content)

    def assertQuerySetEqual(self, l1, l2):
        return self.assertEqual(
            sorted([each.id for each in l1]),
            sorted([each.id for each in l2]),
        )


@override_settings(
    EMAIL_BACKEND=TEST_EMAIL_BACKEND,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    DEFAULT_FILE_STORAGE=TEST_FILE_STORAGE,
    DRAMATIQ_BROKER=TEST_DRAMATIQ_BROKER,
    CACHES=TEST_CACHES,
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
    DEFAULT_FILE_STORAGE=TEST_FILE_STORAGE,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    DRAMATIQ_BROKER=TEST_DRAMATIQ_BROKER,
    CACHES=TEST_CACHES,
)
class HelixTestCase(CommonSetupClassMixin, ImmediateOnCommitMixin, TestCase):
    pass


@override_settings(
    EMAIL_BACKEND=TEST_EMAIL_BACKEND,
    DEFAULT_FILE_STORAGE=TEST_FILE_STORAGE,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    DRAMATIQ_BROKER=TEST_DRAMATIQ_BROKER,
    CACHES=TEST_CACHES,
)
class HelixAPITestCase(APITestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_password = 'joHnDave!@#123'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # initialize roles
        management.call_command('init_roles')

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username='jon@dave.com',
            first_name='Jon',
            last_name='Mon',
            password=self.user_password,
            email='jon@dave.com',
        )

    def authenticate(self, user=None):
        user = user or self.user
        self.client.force_login(user)
