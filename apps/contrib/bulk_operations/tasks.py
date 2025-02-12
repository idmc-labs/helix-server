from __future__ import annotations
import abc
import datetime
import typing
import logging

import django_filters
from openpyxl import Workbook
from rest_framework import serializers
from django.contrib.auth import login, logout
from django.utils import timezone
from django.core.files import File
from django.db import models
from django.http import HttpRequest
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.test import override_settings

from apps.contrib.models import BulkApiOperation
from apps.extraction.filters import FigureExtractionBulkOperationFilterSet
from apps.event.models import Figure

from helix.permalinks import Permalink
from utils.common import get_temp_file


logger = logging.getLogger(__name__)

PERMISSION_DENIED_ERRORS = [
    {
        'field': 'nonFieldErrors',
        'messages': "You don't have permission for this",
    }
]


class FrontendUrlDataType(typing.TypedDict):
    frontend_url: str
    frontend_permalink_url: str


class SuccessDataType(FrontendUrlDataType):
    id: int


class FailureDataType(SuccessDataType):
    errors: typing.List[dict]


def process_request(request: HttpRequest) -> None:
    # Reference from https://github.com/django/django/blob/main/django/contrib/sessions/middleware.py#L13-L20
    session_middlware = SessionMiddleware(None)  # pyright: ignore[reportGeneralTypeIssues]
    auth_middlware = AuthenticationMiddleware(None)  # pyright: ignore[reportGeneralTypeIssues]
    session_middlware.process_request(request)
    auth_middlware.process_request(request)


def generate_dummy_request(user):
    api_request = HttpRequest()
    process_request(api_request)
    login(api_request, user)
    return api_request


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


def save_workbook_file(operation: BulkApiOperation, workbook: Workbook, path: typing.Optional[str] = None):
    if path is None:
        path = f'{operation.pk}-{operation.started_at.isoformat()}.xlsx'
    with get_temp_file() as tmp:
        workbook.save(tmp.name)
        workbook.close()
        file = File(tmp)
        operation.snapshot.save(path, file)
        operation.save(update_fields=('snapshot',))
        del workbook


ModelType = typing.TypeVar("ModelType", bound=models.Model)


class BulkApiOperationBaseTask(typing.Generic[ModelType]):
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
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def generate_snapshot(operation: BulkApiOperation, items: typing.List[ModelType]):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_mutation_variables(cls, payload: dict, items: typing.List[ModelType]) -> dict:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def parse_mutation_response(
        items: typing.List[ModelType],
        response: typing.Optional[dict],
    ) -> typing.Tuple[typing.List[SuccessDataType], typing.List[FailureDataType]]:  # Success-List, Error-List
        raise NotImplementedError

    @classmethod
    def get_items(cls, operation: BulkApiOperation) -> typing.List[ModelType]:
        filterset = cls.get_filterset()
        filters = cls.get_filters(operation.filters)
        queryset: models.QuerySet[ModelType] = filterset(data=filters).qs.order_by('id')
        return list(queryset)

    @classmethod
    def run_mutation(
        cls,
        request: HttpRequest,
        query: str,
        variables: dict,
    ) -> typing.Tuple[typing.Optional[dict], typing.Optional[dict]]:
        return run_mutation(request, query, variables)

    @classmethod
    def mutate(
        cls,
        operation: BulkApiOperation,
        items: typing.List[ModelType],
    ) -> typing.Tuple[typing.List[SuccessDataType], typing.List[FailureDataType]]:
        """
        NOTE: Response should be (success_count, failure_count, errors)
        """
        # TODO: Create a context manager for login/logout
        api_request = generate_dummy_request(operation.created_by)

        variables = cls.get_mutation_variables(operation.payload, items)
        gql_data, gql_errors = cls.run_mutation(api_request, cls.MUTATION, variables)

        logout(api_request)

        # This should't happen in theory - Should be validated using unit test cases
        if gql_errors:
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

        return cls.parse_mutation_response(items, gql_data)

    @classmethod
    def run(cls, operation: BulkApiOperation):
        # Generate item list
        items = cls.get_items(operation)
        # Create a snapshot
        cls.generate_snapshot(operation, items)
        # Mutate -> success, errors
        (
            operation.success_list,
            operation.failure_list,
        ) = cls.mutate(operation, items)
        operation.success_count = len(operation.success_list)
        operation.failure_count = len(operation.failure_list)
        operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.COMPLETED, commit=False)
        operation.save()
        return operation


class BulkFigureBulkUpdateTask(BulkApiOperationBaseTask[Figure]):
    @staticmethod
    def generate_snapshot(operation: BulkApiOperation, items: typing.List[Figure]):
        # Circular dependency
        from apps.contrib.tasks import get_excel_sheet_content

        qs = Figure.objects.filter(id__in=[item.pk for item in items])

        sheet_data = Figure.get_figure_excel_sheets_data(qs)
        workbook = get_excel_sheet_content(**sheet_data)
        save_workbook_file(operation, workbook)

    @staticmethod
    @abc.abstractmethod
    def get_update_payload(payload: dict) -> dict:
        raise NotImplementedError

    @classmethod
    def run_mutation(
        cls,
        request: HttpRequest,
        query: str,
        variables: dict,
    ) -> typing.Tuple[typing.Optional[dict], typing.Optional[dict]]:
        with override_settings(GRAPHENE_BATCH_DEFAULT_MAX_LIMIT=len(variables['items'])):
            return super().run_mutation(request, query, variables)

    @classmethod
    def get_mutation_variables(cls, payload: dict, items: typing.List[Figure]) -> dict:
        payload = cls.get_update_payload(payload)
        return {
            'items': [
                {
                    'id': str(figure.pk),
                    **payload,
                }
                for figure in items
            ],
        }

    @staticmethod
    def parse_mutation_response(
        items: typing.List[Figure],
        response: typing.Optional[dict]
    ) -> typing.Tuple[typing.List[SuccessDataType], typing.List[FailureDataType]]:
        def _get_urls(figure) -> FrontendUrlDataType:
            return {
                'frontend_url': Permalink.current_figure(figure.entry_id, figure.pk, absolute=False),
                'frontend_permalink_url': Permalink.figure(figure.entry_id, figure.pk, absolute=False),
            }

        success_list: typing.List[SuccessDataType] = []
        failure_list: typing.List[FailureDataType] = []
        _response = ((response or {}).get('bulkUpdateFigures') or {})

        raw_success = _response.get('result') or []
        if raw_success:
            for item, _resp in zip(
                items,
                raw_success,
            ):
                if _resp:
                    success_list.append({
                        'id': item.pk,
                        **_get_urls(item),
                    })

        raw_errors = _response.get('errors') or []
        if raw_errors:
            for item, _errors in zip(
                items,
                raw_errors,
            ):
                if _errors:
                    failure_list.append({
                        'id': item.pk,
                        'errors': _errors,
                        **_get_urls(item),
                    })

        return success_list, failure_list


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
    filter_set = FigureExtractionBulkOperationFilterSet

    @staticmethod
    def get_filters(filters: dict):
        return filters['figure_role']['figure']

    @staticmethod
    def get_update_payload(payload: dict) -> dict:
        return {
            'role': Figure.ROLE(payload['figure_role']['role']).name,
        }


class BulkFigureEventUpdateTask(BulkFigureBulkUpdateTask):
    # TODO: Use eventId instead of event{id}
    MUTATION = '''
        mutation BulkUpdateFigures($items: [FigureUpdateInputType!]) {
            bulkUpdateFigures(items: $items) {
                errors
                result {
                  id
                  event {
                    id
                  }
                }
            }
        }
    '''
    filter_set = FigureExtractionBulkOperationFilterSet

    @staticmethod
    def get_filters(filters: dict):
        return filters['figure_event']['figure']

    @classmethod
    def get_mutation_variables(cls, payload: dict, items: typing.List[Figure]) -> dict:
        by_figures = {
            data['figure']: data['event']
            for data in payload['figure_event']['by_figures']
        }
        return {
            'items': [
                {
                    'id': str(figure.pk),
                    'event': by_figures[figure.pk]
                }
                for figure in items
                if figure.pk in by_figures
            ],
        }


def get_operation_handler(operation_action):
    _handler: typing.Optional[typing.Type[BulkApiOperationBaseTask]] = None
    if operation_action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE:
        _handler = BulkFigureRoleUpdateTask
    if operation_action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_EVENT:
        _handler = BulkFigureEventUpdateTask
    if _handler is None:
        raise serializers.ValidationError(f'Action not implemented yet: {operation_action}')
    return _handler


def run_bulk_api_operation(operation: BulkApiOperation):
    try:
        now = timezone.now()
        if now - operation.created_at > datetime.timedelta(minutes=BulkApiOperation.WAIT_TIME_THRESHOLD_IN_MINUTES):
            logger.warning(f'Skipping bulk operation: {operation}')
            operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.KILLED)
            return operation
        logger.info(f'Processing bulk operation: {operation}')
        operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.IN_PROGRESS)
        get_operation_handler(operation.action).run(operation)
    except Exception:
        logger.error(f'Failed to process bulk operation: {operation}', exc_info=True)
        operation.update_status(BulkApiOperation.BULK_OPERATION_STATUS.FAILED)
        return False
    return True
