import logging

from django.db.models import Subquery
from django.utils import timezone

from helix.celery import app as celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AHHS_COPY_TASK_TIMEOUT_SECONDS = 60


@celery_app.task(time_limit=AHHS_COPY_TASK_TIMEOUT_SECONDS)
def carry_over_household_size(ahhs_copy_id):
    """
    This should be run by a super user only
    """
    from apps.country.models import HouseholdSize, HouseholdSizeCarryOverTask

    logger.info(f"Starting copying household size; HouseholdSizeCopyTask={ahhs_copy_id}...")

    ahhs_copy = HouseholdSizeCarryOverTask.objects.get(id=ahhs_copy_id)
    ahhs_copy.started_at = timezone.now()
    ahhs_copy.status = HouseholdSizeCarryOverTask.AHHS_COPY_OPERATION_STATUS.IN_PROGRESS
    ahhs_copy.save()

    destination_year = ahhs_copy.target_year
    source_year = destination_year - 1
    try:
        # NOTE: check for possible duplication
        destination_countries = HouseholdSize.objects.filter(year=destination_year).values("country_id")

        source_year_ahhs = HouseholdSize.objects.filter(year=source_year).exclude(
            country_id__in=Subquery(destination_countries)
        )
        to_be_created_ahhs = []
        for row in source_year_ahhs:
            row.pk = None
            row.year = destination_year
            to_be_created_ahhs.append(row)

        resp = HouseholdSize.objects.bulk_create(to_be_created_ahhs)

        logger.info(f"Total {len(resp)} HouseholdSize copied to {destination_year} from {source_year}")

        ahhs_copy.completed_at = timezone.now()
        ahhs_copy.status = HouseholdSizeCarryOverTask.AHHS_COPY_OPERATION_STATUS.COMPLETED
        ahhs_copy.save()

        logger.info(f"Completed copying household size; HouseholdSizeCarryOverTask={ahhs_copy_id}")
    except Exception as e:
        logger.error(f"Error copying household size; HouseholdSizeCarryOverTask={ahhs_copy_id}, {e}")
        ahhs_copy.status = HouseholdSizeCarryOverTask.AHHS_COPY_OPERATION_STATUS.FAILED
        current_reasons = ahhs_copy.failure_reasons or []
        current_reasons.append(str(e))
        ahhs_copy.completed_at = timezone.now()
        ahhs_copy.failure_reasons = current_reasons
        ahhs_copy.save(update_fields=["completed_at", "status", "failure_reasons"])
