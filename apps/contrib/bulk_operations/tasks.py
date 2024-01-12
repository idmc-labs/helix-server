from __future__ import annotations
import abc
import datetime
import typing
import logging

import django_filters
from rest_framework import serializers
from django.contrib.auth import login, logout
from django.utils import timezone
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
    # Reference from https://github.com/django/django/blob/main/django/contrib/sessions/middleware.py#L13-L20
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
    return result.data, result.errors


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
        """
        NOTE: Response should be (success_count, failure_count, errors)
        """
        filters = cls.get_filters(operation.filters)

        queryset = cls.get_filterset()(data=filters).qs.order_by('id')

        variables = cls.get_mutation_variables(operation.payload, queryset)
        gql_data, gql_errors = run_mutation(request, cls.MUTATION, variables)

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
        # Circular dependency issue
        from apps.contrib.models import BulkApiOperation

        api_request = HttpRequest()
        process_request(api_request)
        login(api_request, operation.created_by)
        (
            operation.success_count,
            operation.failure_count,
            operation.errors,
        ) = cls.update_database(operation, api_request)
        logout(api_request)
        operation.status = BulkApiOperation.BULK_OPERATION_STATUS.FINISHED
        operation.save()
        return operation


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
        from apps.extraction.filters import FigureExtractionBulkOperationFilterSet
        return FigureExtractionBulkOperationFilterSet

    @staticmethod
    def get_filters(filters: dict):
        return filters['figure_role']['figure']

    @staticmethod
    def get_update_payload(payload: dict) -> dict:
        from apps.event.models import Figure
        return {'role': Figure.ROLE(payload['figure_role']['role']).name}


def get_operation_handler(operation_action):
    # Circular dependency issue
    from apps.contrib.models import BulkApiOperation

    _handler: typing.Optional[typing.Type[BulkApiOperationBaseTask]] = None
    if operation_action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE:
        _handler = BulkFigureRoleUpdateTask
    if _handler is None:
        raise serializers.ValidationError(f'Action not implemented yet: {operation_action}')
    return _handler


def run_bulk_api_operation(operation: BulkApiOperation):
    # Circular dependency issue
    from apps.contrib.models import BulkApiOperation

    try:
        now = timezone.now()
        if now - operation.created_at > datetime.timedelta(minutes=BulkApiOperation.WAIT_TIME_THRESHOLD_IN_MINUTES):
            logger.warning(f'Skipping bulk operation: {operation}')
            operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.CANCELED)
            return operation
        logger.info(f'Processing bulk operation: {operation}')
        operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.STARTED)
        get_operation_handler(operation.action).run(operation)
    except Exception:
        logger.error(f'Failed to process bulk operation: {operation}', exc_info=True)
        operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.FAILED)
        return False
    return True
