from __future__ import annotations
import abc
import typing
import logging

import django_filters
from django.contrib.auth import login, logout
from django.http import HttpRequest
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

if typing.TYPE_CHECKING:
    from apps.contrib.models import BulkApiOperation


logger = logging.getLogger(__name__)

PERMISSION_DENIED_ERRORS = [
    {
        'field': 'nonFieldErrors',
        'messages': "You don't have permission for this",
    }
]


def process_request(request: HttpRequest) -> None:
    session_middlware = SessionMiddleware(None)  # pyright: ignore[reportGeneralTypeIssues]
    auth_middlware = AuthenticationMiddleware(None)  # pyright: ignore[reportGeneralTypeIssues]
    session_middlware.process_request(request)
    auth_middlware.process_request(request)


def run_mutation(
    request: HttpRequest,
    query: str,
    variables: dict,
) -> typing.Tuple[typing.Optional[dict], typing.Optional[dict]]:
    # To avoid circular dependency
    from helix.schema import schema as gql_schema
    from utils.graphene.context import GQLContext

    result = gql_schema.execute(
        query,
        context=GQLContext(request),
        variables=variables,
    )
    if result.errors:
        return None, result.errors
    return result.data, None


def get_gql_response_count(data: typing.Optional[typing.List[typing.Optional[dict]]]) -> int:
    return len([
        i
        for i in (data or [])
        if i is not None
    ])


class BulkApiOperationBaseTask:
    MUTATION: str
    filter_set: typing.Optional[typing.Type[django_filters.FilterSet]]

    @classmethod
    def get_filterset(cls) -> typing.Type[django_filters.FilterSet]:
        if cls.filter_set is None:
            raise Exception('filter_set not defined')
        return cls.filter_set

    @staticmethod
    @abc.abstractmethod
    def get_filters(filters: dict) -> dict:
        raise Exception('get_filters not implemented')

    @classmethod
    @abc.abstractmethod
    def get_mutation_variables(cls, payload: dict, queryset) -> dict:
        raise Exception('get_mutation_variables not implemented')

    @staticmethod
    @abc.abstractmethod
    def parse_mutation_response(response: typing.Optional[dict]) -> typing.Tuple[int, int, typing.List[dict]]:
        raise Exception('parse_mutation_response not implemented')

    @classmethod
    def update_database(
        cls,
        operation: BulkApiOperation,
        request: HttpRequest,
    ) -> typing.Tuple[int, int, typing.List[dict]]:
        filters = cls.get_filters(operation.filters)

        # TODO: Use limit
        queryset = cls.get_filterset()(data=filters).qs.order_by('id')

        variables = cls.get_mutation_variables(operation.payload, queryset)
        gql_data, gql_errors = run_mutation(request, cls.MUTATION, variables)

        # TODO: Handle this properly
        # This should't happen in theory - Should be validated using unit test cases
        if gql_data is None or gql_errors:
            logger.error(
                f'Error found on bulk operation: {operation.get_action_display()}',
                extra={
                    'context': {
                        'bulk_operation_id': operation.pk,
                        'variables': variables,
                        'data': gql_data,
                        'errors': gql_errors,
                    },
                },
            )

        return cls.parse_mutation_response(gql_data)

    @classmethod
    def run(cls, operation: BulkApiOperation):
        # From: https://github.com/django/django/blob/main/django/contrib/sessions/middleware.py#L13-L20
        api_request = HttpRequest()
        process_request(api_request)
        login(api_request, operation.created_by)
        (
            operation.success_count,
            operation.failure_count,
            operation.errors,
        ) = cls.update_database(operation, api_request)
        logout(api_request)
        operation.save()


class BulkFigureBulkUpdateTask(BulkApiOperationBaseTask):
    @staticmethod
    def parse_mutation_response(response: typing.Optional[dict]) -> typing.Tuple[int, int, typing.List[dict]]:
        _response = ((response or {}).get('bulkUpdateFigures') or {})
        errors = _response.get('errors') or []
        success_count = get_gql_response_count(_response.get('result'))
        failure_count = get_gql_response_count(errors)
        return success_count, failure_count, errors

    @staticmethod
    @abc.abstractmethod
    def get_update_payload(payload: dict) -> dict:
        raise Exception('get_update_payload not implemented')

    @classmethod
    def get_mutation_variables(cls, payload: dict, queryset) -> dict:
        payload = cls.get_update_payload(payload)
        return {
            'items': [
                {
                    'id': str(figure.id),
                    **payload,
                }
                for figure in queryset
            ],
        }


class BulkFigureRoleUpdateTask(BulkFigureBulkUpdateTask):
    MUTATION = '''
        mutation BulkUpdateFigures($items: [FigureUpdateInputType!]) {
            bulkUpdateFigures(items: $items) {
                errors
                result {
                  id
                  role
                }
            }
        }
    '''

    @classmethod
    def get_filterset(cls) -> typing.Type[django_filters.FilterSet]:
        from apps.extraction.filters import FigureExtractionFilterSet
        return FigureExtractionFilterSet

    @staticmethod
    def get_filters(filters: dict):
        return filters['figure_role']['figure']

    @staticmethod
    def get_update_payload(payload: dict) -> dict:
        from apps.event.models import Figure
        return {'role': Figure.ROLE(payload['figure_role']['role']).name}


def run_bulk_api_operation(operation: BulkApiOperation):
    # Circular dependency issue
    from apps.contrib.models import BulkApiOperation

    _handler: typing.Optional[typing.Type[BulkApiOperationBaseTask]] = None
    if operation.action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE:
        _handler = BulkFigureRoleUpdateTask
    if _handler is None:
        raise Exception(f'Action not implemented yet: {operation.action}')
    _handler.run(operation)
