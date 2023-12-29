from __future__ import annotations
import typing

from django.http import HttpRequest
from django.contrib.auth import login, logout

from utils.error_types import mutation_is_not_valid
from apps.users.models import User
if typing.TYPE_CHECKING:
    from apps.contrib.models import BulkApiOperation


PERMISSION_DENIED_ERRORS = [
    {
        'field': 'nonFieldErrors',
        'messages': "You don't have permission for this",
    }
]


def bulk_figures_role_update(
    operation: BulkApiOperation,
    request: HttpRequest,
    user: User,
) -> typing.Tuple[int, int, typing.List[dict]]:
    from apps.extraction.filters import FigureExtractionFilterSet
    from apps.entry.serializers import NestedFigureUpdateSerializer

    filters = operation.filters['figure_role']
    payload = operation.payload['figure_role']
    figure_qs = FigureExtractionFilterSet(data=filters).qs

    success_count, failure_count = 0, 0
    serializer_kwargs = {
        'context': {
            'request': request,
        },
        'partial': True,
        'data': payload,
    }

    if not user.has_perms(['entry.add_entry']):
        return 0, figure_qs.count(), PERMISSION_DENIED_ERRORS

    errors = []
    for figure in figure_qs:
        # TODO: Use BulkFigureUpdateMutation after it is finalized
        serializer = NestedFigureUpdateSerializer(instance=figure, **serializer_kwargs)
        if _errors := mutation_is_not_valid(serializer):
            errors.append(_errors)
            failure_count += 1
            continue
        serializer.save()
        success_count += 1

    return success_count, failure_count, errors


def run_bulk_api_operation(operation: BulkApiOperation):
    _func: typing.Optional[
        typing.Callable[
            [BulkApiOperation, HttpRequest, User],
            typing.Tuple[int, int, typing.List[dict]],
        ]
    ] = None
    if operation.action == BulkApiOperation.BULK_OPERATION_ACTION.FIGURE_ROLE:
        _func = bulk_figures_role_update
    if _func is None:
        raise Exception(f'Action not implemented yet: {operation.action}')

    api_request = HttpRequest()
    login(api_request, operation.created_by)
    (
        operation.success_count,
        operation.failure_count,
        operation.errors,
    ) = _func(operation, api_request, operation.created_by)
    logout(api_request)
    operation.save()
