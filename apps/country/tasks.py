import logging
import typing

from django.db import models, transaction

from apps.contrib.bulk_operations.tasks import BulkOperationBaseTask, FailureDataType, SuccessDataType
from apps.contrib.models import BulkApiOperation
from apps.country.models import HouseholdSize
from helix.celery import app as celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AHHS_COPY_TASK_TIMEOUT_SECONDS = 60

ModelType = typing.TypeVar("ModelType", bound=models.Model)


@celery_app.task(time_limit=AHHS_COPY_TASK_TIMEOUT_SECONDS)
@transaction.atomic
def carry_over_ahhs_data():
    latest_household = HouseholdSize.objects.order_by("-year").first()
    if not latest_household:
        return

    destination_year = latest_household.year
    source_year = destination_year - 1

    existing_count = HouseholdSize.objects.filter(year=destination_year).count()
    if existing_count > 0:
        logger.error(f"Year already has data: Total records: {existing_count}")
        return

    cloned_data = []
    for row in HouseholdSize.objects.filter(year=source_year).all():
        row.pk = None  # Create new
        row.year = destination_year  # Change year
        cloned_data.append(row)
    resp = HouseholdSize.objects.bulk_create(cloned_data)
    logger.info(f"Success: Total records created: {len(resp)}")
    logger.info("New records:")
    for i in resp:
        logger.info(f"- {i}")


class BulkAHHSCloneTask(BulkOperationBaseTask):
    @staticmethod
    def get_update_payload(payload: dict) -> dict:
        return {
            "role": Figure.ROLE(payload["figure_role"]["role"]).name,
        }

    @classmethod
    def get_mutation_variables(cls, payload: dict, items: typing.List[HouseholdSize]) -> dict:
        payload = cls.get_update_payload(payload)
        return {
            "items": [
                {
                    "id": str(figure.pk),
                    **payload,
                }
                for figure in items
            ],
        }

    @staticmethod
    def parse_mutation_response(
        items: typing.List[HouseholdSize], response: typing.Optional[dict]
    ) -> typing.Tuple[typing.List[SuccessDataType], typing.List[FailureDataType]]:
        # def _get_urls(figure) -> FrontendUrlDataType:
        #     return {
        #         "frontend_url": Permalink.current_figure(figure.entry_id, figure.pk, absolute=False),
        #         "frontend_permalink_url": Permalink.figure(figure.entry_id, figure.pk, absolute=False),
        #     }

        success_list: typing.List[SuccessDataType] = []
        failure_list: typing.List[FailureDataType] = []
        _response = (response or {}).get("bulkUpdateFigures") or {}

        raw_success = _response.get("result") or []
        if raw_success:
            for item, _resp in zip(
                items,
                raw_success,
            ):
                if _resp:
                    success_list.append(
                        {
                            "id": item.pk,
                            # **_get_urls(item),
                        }
                    )

        raw_errors = _response.get("errors") or []
        if raw_errors:
            for item, _errors in zip(
                items,
                raw_errors,
            ):
                if _errors:
                    failure_list.append(
                        {
                            "id": item.pk,
                            "errors": _errors,
                            # **_get_urls(item),
                        }
                    )

        return success_list, failure_list

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
        # api_request = generate_dummy_request(operation.created_by)

        variables = cls.get_mutation_variables(operation.payload, items)
        print("Variables----------------", variables)
        # gql_data, gql_errors = cls.run_mutation(api_request, cls.MUTATION, variables)
        gql_data, gql_errors = carry_over_ahhs_data(refrence_year, destination_year)

        # This should't happen in theory - Should be validated using unit test cases
        if gql_errors:
            logger.error(
                f"Error found on bulk operation: {operation.get_action_display()}",
                extra={
                    "context": {
                        "bulk_operation_id": operation.pk,
                        "variables": variables,
                        "data": gql_data,
                        "errors": gql_errors,
                    },
                },
            )

        return cls.parse_mutation_response(items, gql_data)
