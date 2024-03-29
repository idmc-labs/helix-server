import os
import copy
import shutil
from unittest.mock import patch
import pytz
import datetime

from django.contrib.auth import get_user_model
from django.core import management
from django.test import TestCase, override_settings
from django.conf import settings
from graphene_django.utils import GraphQLTestCase
from rest_framework.test import APITestCase
from django.core.cache import caches

from apps.users.enums import USER_ROLE
from apps.users.models import Portfolio
from helix.settings import BASE_DIR
from utils.factories import UserFactory, MonitoringSubRegionFactory, CountryFactory
from utils.common import convert_date_object_to_string_in_dict

User = get_user_model()
TEST_MEDIA_ROOT = 'media-temp'
TEST_EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
TEST_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
BROKER_BACKEND = 'memory'
CELERY_TASK_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES = True

TEST_CACHES = {
    cache_key: {
        **config,
        "LOCATION": f"{config['LOCATION']}-test",  # APPEND -test to existing redis db for test
    }
    for cache_key, config in settings.CACHES.items()
}


TEST_AUTH_PASSWORD_VALIDATORS = []


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

    def assertResponseNoErrors(self, response):
        content = response.json()
        self.assertIsNone(content.get('errors'), content)

    def assertResponseErrors(self, response):
        content = response.json()
        self.assertIsNotNone(content.get('errors'), content)

    def assertQuerySetEqual(self, l1, l2, message=None):
        return self.assertEqual(
            sorted([each.id for each in l1]),
            sorted([each.id for each in l2]),
            message,
        )


COMMON_OVERRIDE_SETTINGS = dict(
    SENTRY_DSN=None,
    USE_S3_BUCKET=False,
    EMAIL_BACKEND=TEST_EMAIL_BACKEND,
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    DEFAULT_FILE_STORAGE=TEST_FILE_STORAGE,
    CACHES=TEST_CACHES,
    AUTH_PASSWORD_VALIDATORS=TEST_AUTH_PASSWORD_VALIDATORS,
    BROKER_BACKEND=BROKER_BACKEND,
    CELERY_TASK_ALWAYS_EAGER=CELERY_TASK_ALWAYS_EAGER,
    CELERY_EAGER_PROPAGATES=CELERY_EAGER_PROPAGATES,
)


@override_settings(**COMMON_OVERRIDE_SETTINGS)
class HelixGraphQLTestCase(CommonSetupClassMixin, GraphQLTestCase):
    GRAPHQL_URL = '/graphql'
    GRAPHQL_SCHEMA = 'helix.schema.schema'

    def force_login(self, user):
        self._client.force_login(user)

    def create_user(self) -> User:
        raw_password = 'admin123'
        user = User.objects.create_user(
            username='admin',
            email='admin@email.com',
            password=raw_password,
        )
        user.raw_password = raw_password
        return user


def create_user_with_role(role: str, monitoring_sub_region: int = None, country: int = None) -> User:
    user = UserFactory.create()
    user.raw_password = 'lhjsjsjsjlj'
    user.set_password(user.raw_password)
    user.save()  # saves it as a guest
    user.refresh_from_db()
    if role == USER_ROLE.ADMIN.name:
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE[role],
        )
    if role == USER_ROLE.REPORTING_TEAM.name:
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE[role],
        )
    if role == USER_ROLE.DIRECTORS_OFFICE.name:
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE[role],
        )
    if role == USER_ROLE.REGIONAL_COORDINATOR.name:
        new_mr = monitoring_sub_region or MonitoringSubRegionFactory.create().id
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE[role],
            monitoring_sub_region_id=new_mr
        )  # assigns a new role
    elif role == USER_ROLE.MONITORING_EXPERT.name:
        new_mr = monitoring_sub_region or MonitoringSubRegionFactory.create().id
        new_country = country or CountryFactory.create(monitoring_sub_region_id=new_mr).id
        Portfolio.objects.create(
            user=user,
            role=USER_ROLE[role],
            monitoring_sub_region_id=new_mr,
            country_id=new_country,
        )  # assigns a new role
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
        '''
        NOTE:- __exit__() method expecting 3 positional args exc_type, exc_value, traceback after we changed
        python base from buster to bullseye.
        '''
        super().tearDownClass()

        # TODO:- Pass proper exc_type, exc_value, traceback instead of None in __exit__
        exc_type = None
        exc_value = None
        traceback = None

        cls.on_commit_mgr.__exit__(
            exc_type,
            exc_value,
            traceback,
        )


@override_settings(**COMMON_OVERRIDE_SETTINGS)
class HelixTestCase(CommonSetupClassMixin, ImmediateOnCommitMixin, TestCase):
    pass


@override_settings(**COMMON_OVERRIDE_SETTINGS)
class HelixAPITestCase(APITestCase):
    ENABLE_NOW_PATCHER = True

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
        for key in TEST_CACHES.keys():
            caches[key].clear()
        self.user = User.objects.create_user(
            username='jon@dave.com',
            first_name='Jon',
            last_name='Mon',
            password=self.user_password,
            email='jon@dave.com',
        )
        if self.ENABLE_NOW_PATCHER:
            self.now_patcher = patch('django.utils.timezone.now')
            self.now_datetime = datetime.datetime(2021, 1, 1, 0, 0, 0, 123456, tzinfo=pytz.UTC)
            self.now_datetime_str = self.now_datetime.isoformat()
            self.now_patcher.start().return_value = self.now_datetime

    def authenticate(self, user=None):
        user = user or self.user
        self.client.force_login(user)


class CommonUtilTest(TestCase):
    def test_convert_date_object_to_string_in_dict(self):
        data = {
            'key1': datetime.date(2021, 1, 1),
            'key2': {
                'key1': datetime.date(2021, 1, 1),
                'key2': datetime.date(2021, 1, 2),
                'key3': datetime.date(2021, 1, 3),
            },
            'key3': [
                datetime.date(2021, 1, 1),
                datetime.date(2021, 1, 2),
                datetime.date(2021, 1, 3),
            ],
        }
        expected_data = {
            'key1': '2021-01-01',
            'key2': {
                'key1': '2021-01-01',
                'key2': '2021-01-02',
                'key3': '2021-01-03',
            },
            'key3': [
                '2021-01-01',
                '2021-01-02',
                '2021-01-03',
            ],
        }

        def generate_nested(data, level):
            _data = copy.deepcopy(data)
            for _ in range(0, level):
                _data = {
                    **copy.deepcopy(_data),
                    'nested1': {
                        **copy.deepcopy(_data),
                    },
                    'nested2': {
                        **copy.deepcopy(_data),
                    },
                }
            return _data

        fdata = generate_nested(data, 5)
        edata = generate_nested(expected_data, 5)
        assert convert_date_object_to_string_in_dict(fdata) == edata
