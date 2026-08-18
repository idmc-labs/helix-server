import logging

from django.core.management.base import BaseCommand
from django.db.models import Sum

from apps.crisis.models import Crisis
from apps.gidd.models import (
    Conflict,
    Disaster,
    GiddDisplacement,
    GiddEventDisplacement,
)
from apps.gidd.tasks import get_gidd_years

logger = logging.getLogger(__name__)

GIDD_YEARS = None


def get_years():
    global GIDD_YEARS
    if GIDD_YEARS is None:
        GIDD_YEARS = list(get_gidd_years())
    return GIDD_YEARS


def _compare(label, old_qs, new_qs, group_keys):
    old = {
        tuple(row[k] for k in group_keys): (row["nd"], row["td"])
        for row in old_qs.values(*group_keys).annotate(nd=Sum("new_displacement"), td=Sum("total_displacement"))
    }
    new = {
        tuple(row[k] for k in group_keys): (row["nd"], row["td"])
        for row in new_qs.values(*group_keys).annotate(nd=Sum("new_displacement"), td=Sum("total_displacement"))
    }

    mismatches = []
    for key in set(old) | set(new):
        old_val = old.get(key, (None, None))
        new_val = new.get(key, (None, None))
        if old_val != new_val:
            mismatches.append((key, old_val, new_val))

    if mismatches:
        logger.error(f"[FAIL] {label}: {len(mismatches)} mismatches")
        for key, old_val, new_val in mismatches[:10]:
            logger.error(f"  {dict(zip(group_keys, key))}: old={old_val} new={new_val}")
        return False

    logger.info(f"[PASS] {label}: {len(old)} rows match")
    return True


class Command(BaseCommand):
    help = "Validate GiddEventDisplacement and GiddDisplacement against existing GIDD tables"

    def handle(self, *args, **options):
        years = get_years()
        passed = 0
        failed = 0

        # Check 1: GiddEventDisplacement (disaster) vs Disaster
        # Compare at country+year level. Exclude legacy Disaster rows (event_raw_id null).
        result = _compare(
            label="GiddEventDisplacement (disaster) vs Disaster [country+year]",
            old_qs=Disaster.objects.filter(year__in=years, event_raw_id__isnull=False),
            new_qs=GiddEventDisplacement.objects.filter(cause=Crisis.CRISIS_TYPE.DISASTER),
            group_keys=["country_id", "year"],
        )
        passed += result
        failed += not result

        # Check 2: GiddDisplacement (conflict) vs Conflict
        # Compare at country+year level. Exclude legacy Conflict rows (year not in GIDD years).
        result = _compare(
            label="GiddDisplacement (conflict) vs Conflict [country+year]",
            old_qs=Conflict.objects.filter(year__in=years),
            new_qs=GiddDisplacement.objects.filter(cause=Crisis.CRISIS_TYPE.CONFLICT),
            group_keys=["country_id", "year"],
        )
        passed += result
        failed += not result

        # Check 3: GiddEventDisplacement totals == GiddDisplacement totals
        # When GiddEventDisplacement is grouped by country+year+cause+subtype keys,
        # it must equal GiddDisplacement.
        SUBTYPE_KEYS = [
            "country_id",
            "year",
            "cause",
            "violence_id",
            "violence_sub_type_id",
            "hazard_type_id",
            "hazard_sub_type_id",
        ]
        result = _compare(
            label="GiddEventDisplacement totals == GiddDisplacement totals [subtype level]",
            old_qs=GiddDisplacement.objects.all(),
            new_qs=GiddEventDisplacement.objects.all(),
            group_keys=SUBTYPE_KEYS,
        )
        passed += result
        failed += not result

        self.stdout.write(f"\nResults: {passed} passed, {failed} failed")
        if failed:
            raise SystemExit(1)
