from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from graphene_django.utils import GraphQLTestCase

User = get_user_model()


class HelixGraphQLTestCase(GraphQLTestCase):
    GRAPHQL_URL = '/graphql'
    GRAPHQL_SCHEMA = 'helix.schema.schema'

    def create_user(self) -> User:
        raw_password = 'admin123'
        user = User.objects.create_user(
            username='admin',
            email='admin@email.com',
            password=raw_password,
        )
        user.raw_password = raw_password
        return user


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
)
class HelixTestCase(TestCase):
    pass
