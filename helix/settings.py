"""
Django settings for HELIX server project.

Generated by 'django-admin startproject' using Django 3.0.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os
import socket
import logging

from . import sentry
from helix.aws.secrets_manager import get_db_cluster_secret

logger = logging.getLogger(__name__)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS_DIRNAME = 'apps'
APPS_DIR = os.path.join(BASE_DIR, APPS_DIRNAME)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY',
                            'w(m6)jr08z!anjsq6mjz%xo^*+sfnv$e3list=gfcfxaj_^4%o')
PRODUCTION = 'production'
DEVELOPMENT = 'development'
ALPHA = 'alpha'
NIGHTLY = 'nightly'
HELIX_ENVIRONMENT = os.environ.get('HELIX_ENVIRONMENT', DEVELOPMENT)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
logger.debug(f'\nServer running in {DEBUG=} mode.\n')

ALLOWED_HOSTS = [
    os.environ.get('ALLOWED_HOST', '.idmcdb.org')
]

# https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-CSRF_USE_SESSIONS
CSRF_USE_SESSIONS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'False').lower() == 'true'
# https://docs.djangoproject.com/en/3.2/ref/settings/#std:setting-SESSION_COOKIE_DOMAIN
SESSION_COOKIE_DOMAIN = os.environ.get('SESSION_COOKIE_DOMAIN', None)
# https://docs.djangoproject.com/en/3.2/ref/settings/#csrf-cookie-domain
CSRF_COOKIE_DOMAIN = os.environ.get('CSRF_COOKIE_DOMAIN', '.idmcdb.org')

CORS_ORIGIN_REGEX_WHITELIST = [
    r'^https://[\w\-]+\.idmcdb\.org$'
]
CSRF_TRUSTED_ORIGINS = [
    'media-monitoring.idmcdb.org',
    'https://media-monitoring.idmcdb.org',
    'http://media-monitoring.idmcdb.org',
]

# Application definition

LOCAL_APPS = [
    'contrib',
    'country',
    'users',
    'organization',
    'contact',
    'crisis',
    'event',
    'entry',
    'resource',
    'review',
    'extraction',
    'parking_lot',
    'contextualupdate',
    'report',
]

THIRD_PARTY_APPS = [
    'graphene_django',
    'rest_framework.authtoken',  # required by djoser
    'djoser',
    'corsheaders',
    'django_filters',
    'debug_toolbar',
    'graphene_graphiql_explorer',
    'graphiql_debug_toolbar',
    'rest_framework',
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_email',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_hotp',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.postgres',
] + THIRD_PARTY_APPS + [
    # apps.users.apps.UsersConfig
    f'{APPS_DIRNAME}.{app}.apps.{"".join([word.title() for word in app.split("_")])}Config' for app in LOCAL_APPS
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'utils.middleware.HealthCheckMiddleware',
    'django.middleware.common.CommonMiddleware',
    # NOTE: DebugToolbarMiddleware will cause mutation to execute twice for the client, works fine with graphiql
    # 'utils.middleware.DebugToolbarMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

if HELIX_ENVIRONMENT not in (DEVELOPMENT,):
    MIDDLEWARE.append('django.middleware.clickjacking.XFrameOptionsMiddleware')

REDIS_BROKER_URL = 0
REDIS_CACHE_DB = 1
REDIS_RESULT_BACKEND = 2

if 'COPILOT_ENVIRONMENT_NAME' in os.environ:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://{}:{}/{}'.format(
                os.environ['ELASTI_CACHE_ADDRESS'],
                os.environ['ELASTI_CACHE_PORT'],
                REDIS_CACHE_DB,
            ),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_CACHE_URL', 'redis://redis:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend']
}

ROOT_URLCONF = 'helix.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'helix.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

if 'COPILOT_ENVIRONMENT_NAME' in os.environ:
    DBCLUSTER_SECRET = get_db_cluster_secret()
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            # in the workflow environment
            'NAME': DBCLUSTER_SECRET['dbname'],
            'USER': DBCLUSTER_SECRET['username'],
            'PASSWORD': DBCLUSTER_SECRET['password'],
            'HOST': DBCLUSTER_SECRET['host'],
            'PORT': DBCLUSTER_SECRET['port'],
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ.get('POSTGRES_DB', 'postgres'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
            'HOST': os.environ.get('POSTGRES_HOST', 'db'),
            'PORT': os.environ.get('POSTGRES_PORT', 5432),
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
    {
        'NAME': 'apps.users.password_validation.MaximumLengthValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

AUTH_USER_MODEL = 'users.User'

# https://docs.graphene-python.org/projects/django/en/latest/settings/
GRAPHENE = {
    'ATOMIC_MUTATIONS': True,
    'SCHEMA': 'helix.schema.schema',
    'SCHEMA_OUTPUT': 'schema.json',  # defaults to schema.json,
    'SCHEMA_INDENT': 2,  # Defaults to None (displays all data on a single line)
    'MIDDLEWARE': [
        'helix.sentry.SentryMiddleware',
        'helix.auth.WhiteListMiddleware',
    ],
}

GRAPHENE_DJANGO_EXTRAS = {
    'DEFAULT_PAGINATION_CLASS': 'utils.pagination.PageGraphqlPaginationWithoutCount',
    'DEFAULT_PAGE_SIZE': 20,
    'MAX_PAGE_SIZE': 50,
    # 'CACHE_ACTIVE': True,
    # 'CACHE_TIMEOUT': 300    # seconds
}
if not DEBUG:
    GRAPHENE['MIDDLEWARE'].append('utils.middleware.DisableIntrospectionSchemaMiddleware')

AUTHENTICATION_BACKEND = [
    'django.contrib.auth.backends.ModelBackend',
]

DJOSER = {
    'ACTIVATION_URL': '#/activate/{uid}/{token}',
    'SEND_ACTIVATION_EMAIL': os.environ.get('SEND_ACTIVATION_EMAIL', "True") == 'True',
}
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django_ses.SESBackend'

DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", 'contact@idmcdb.org')

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = 'media/'

# https://docs.djangoproject.com/en/3.1/ref/settings/#std:setting-APPEND_SLASH
APPEND_SLASH = False

########
# CORS #
########

CORS_ORIGIN_WHITELIST = [
    "http://localhost:3080",
    "http://127.0.0.1:3080"
]
CORS_ALLOW_CREDENTIALS = True
# CORS_ORIGIN_ALLOW_ALL = False
# CORS_ORIGIN_REGEX_WHITELIST = [
#     '^https://[\w\-]+\.idmcdb\.org$'
# ]
# CSRF_TRUSTED_ORIGINS = []

#################
# DEBUG TOOLBAR #
#################

INTERNAL_IPS = [
    '127.0.0.1',
]

# https://github.com/flavors/django-graphiql-debug-toolbar/#installation
hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS += [ip[:-1] + '1' for ip in ips]

# Django storage

# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html
if 'COPILOT_ENVIRONMENT_NAME' in os.environ:
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    # NOTE: This naming convention is defined in the addon for s3
    AWS_STORAGE_BUCKET_NAME = os.environ['COPILOT_S3_BUCKET_NAME']
elif HELIX_ENVIRONMENT not in (DEVELOPMENT,):
    # TODO: Remove me after complete move to copilot
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'idmc-helix')
    AWS_S3_REGION_NAME = os.environ.get('AWS_REGION', 'us-east-1')

# NOTE: s3 bucket is public
# AWS_QUERYSTRING_EXPIRE = int(os.environ.get('AWS_QUERYSTRING_EXPIRE', 12 * 60 * 60))
AWS_QUERYSTRING_AUTH = False
AWS_S3_FILE_OVERWRITE = False
AWS_IS_GZIPPED = True
GZIP_CONTENT_TYPES = [
    'text/css',
    'text/javascript',
    'application/javascript',
    'application/x-javascript',
    'image/svg+xml',
    'application/json',
    'application/pdf',
]

# Sentry Config
SENTRY_DSN = os.environ.get('SENTRY_DSN')

if SENTRY_DSN:
    SENTRY_CONFIG = {
        'dsn': SENTRY_DSN,
        'send_default_pii': True,
        # TODO: Move server to root directory to get access to .git
        # 'release': sentry.fetch_git_sha(os.path.dirname(BASE_DIR)),
        'environment': HELIX_ENVIRONMENT,
        'debug': DEBUG,
        'tags': {
            'site': ALLOWED_HOSTS[0],
        },
    }
    sentry.init_sentry(
        app_type='server',
        **SENTRY_CONFIG,
    )

RESOURCE_NUMBER = GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']
RESOURCEGROUP_NUMBER = GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']
FIGURE_NUMBER = GRAPHENE_DJANGO_EXTRAS['MAX_PAGE_SIZE']

# CELERY

if 'COPILOT_ENVIRONMENT_NAME' in os.environ:
    CELERY_BROKER_URL = 'redis://{}:{}/{}'.format(
        os.environ['ELASTI_CACHE_ADDRESS'],
        os.environ['ELASTI_CACHE_PORT'],
        REDIS_BROKER_URL,
    )
    CELERY_RESULT_BACKEND = 'redis://{}:{}/{}'.format(
        os.environ['ELASTI_CACHE_ADDRESS'],
        os.environ['ELASTI_CACHE_PORT'],
        REDIS_RESULT_BACKEND,
    )
else:
    CELERY_BROKER_URL = os.environ.get('CELERY_REDIS_URL', 'redis://redis:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/1')

# NOTE: These queue names must match the worker container command
# CELERY_DEFAULT_QUEUE = LOW_PRIO_QUEUE = os.environ.get('LOW_PRIO_QUEUE_NAME', 'celery_low')
# HIGH_PRIO_QUEUE = os.environ.get('HIGH_PRIO_QUEUE_NAME', 'celery_high')

# CELERY ROUTES
# CELERY_ROUTES = {
#     'apps.users.tasks.send_email': {'queue': HIGH_PRIO_QUEUE},
#     'apps.entry.tasks.generate_pdf': {'queue': HIGH_PRIO_QUEUE},
#     # LOW
#     'apps.contrib.tasks.kill_all_old_excel_exports': {'queue': LOW_PRIO_QUEUE},
#     'apps.contrib.tasks.kill_all_long_running_previews': {'queue': LOW_PRIO_QUEUE},
#     'apps.contrib.tasks.kill_all_long_running_report_generations': {'queue': LOW_PRIO_QUEUE},
#     'apps.report.tasks.trigger_report_generation': {'queue': LOW_PRIO_QUEUE},
#     'apps.contrib.tasks.generate_excel_file': {'queue': LOW_PRIO_QUEUE},
# }

# end CELERY

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# WHITELIST following nodes from authentication checks
GRAPHENE_NODES_WHITELIST = (
    'login',
    'logout',
    'activate',
    'register',
    'me',
    'generateResetPasswordToken',
    'resetPassword',
    # __ double underscore nodes
    '__schema',
    '__type',
    '__typename',
)

# CAPTCHA
HCAPTCHA_SECRET = os.environ.get('HCAPTCHA_SECRET', '0x0000000000000000000000000000000000000000')

# It login attempts exceed MAX_LOGIN_ATTEMPTS, users will need to enter captcha
# to login
MAX_LOGIN_ATTEMPTS = 3

# If login attempts exceed MAX_CAPTCHA_LOGIN_ATTEMPTS , users will need to wait LOGIN_TIMEOUT seconds

MAX_CAPTCHA_LOGIN_ATTEMPTS = 10
LOGIN_TIMEOUT = 10 * 60  # seconds

# Frontend base url for email button link
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:3080')

# https://docs.djangoproject.com/en/3.2/ref/settings/#password-reset-timeout
PASSWORD_RESET_TIMEOUT = 15 * 60  # seconds
PASSWORD_RESET_CLIENT_URL = "{FRONTEND_BASE_URL}reset-password/{{uid}}/{{token}}".format(
    FRONTEND_BASE_URL=FRONTEND_BASE_URL
)

# TASKS TIMEOUTS
OLD_JOB_EXECUTION_TTL = 72 * 60 * 60  # seconds
# staying in pending for too long will be moved to killed
EXCEL_EXPORT_PENDING_STATE_TIMEOUT = 5 * 60 * 60  # seconds
# staying in progress for too long will be moved to killed
EXCEL_EXPORT_PROGRESS_STATE_TIMEOUT = 10 * 60  # seconds

EXCEL_EXPORT_CONCURRENT_DOWNLOAD_LIMIT = 10

OTP_TOTP_ISSUER = 'IDMC'
OTP_HOTP_ISSUER = 'IDMC'
OTP_EMAIL_SENDER = DEFAULT_FROM_EMAIL
OTP_EMAIL_SUBJECT = 'IDMC OTP Token'
OTP_EMAIL_BODY_TEMPLATE_PATH = 'emails/otp.html'
