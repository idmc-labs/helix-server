from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.event.constants import CONFLICT_TYPES, DISASTERS, OTHER_SUB_TYPES
from apps.event.models import (
    DisasterCategory,
    DisasterSubCategory,
    DisasterSubType,
    DisasterType,
    OtherSubType,
    Violence,
    ViolenceSubType,
)

# Expected row counts derived from the constants, so the test tracks the source of truth.
EXPECTED_COUNTS = {
    OtherSubType: len(OTHER_SUB_TYPES),
    Violence: len(CONFLICT_TYPES),
    ViolenceSubType: sum(len(sub_types) for sub_types in CONFLICT_TYPES.values()),
    DisasterCategory: len(DISASTERS),
    DisasterSubCategory: sum(len(subcats) for subcats in DISASTERS.values()),
    DisasterType: sum(len(types) for subcats in DISASTERS.values() for types in subcats.values()),
    DisasterSubType: sum(
        len(dsubtypes) for subcats in DISASTERS.values() for types in subcats.values() for dsubtypes in types.values()
    ),
}


class InitTypesSubTypesCommandTest(TestCase):
    def _run(self, *args) -> str:
        out = StringIO()
        call_command("init_types_subtypes", *args, stdout=out)
        return out.getvalue()

    def test_seeds_all_taxonomies_on_empty_db(self):
        for model in EXPECTED_COUNTS:
            self.assertEqual(model.objects.count(), 0)

        self._run()

        for model, expected in EXPECTED_COUNTS.items():
            self.assertEqual(model.objects.count(), expected, model.__name__)

    def test_rerun_is_idempotent_and_reports_no_changes(self):
        self._run()

        output = self._run()

        # No duplicate rows created on a second run.
        for model, expected in EXPECTED_COUNTS.items():
            self.assertEqual(model.objects.count(), expected, model.__name__)

        total = sum(EXPECTED_COUNTS.values())
        self.assertIn(f"Total: created 0, updated 0, unchanged {total}.", output)

    def test_update_detected_and_healed_when_field_changes(self):
        self._run()

        sub_type = OtherSubType.objects.get(name__iexact=OTHER_SUB_TYPES[0].name)
        sub_type.idu_name = "corrupted-value"
        sub_type.save()

        output = self._run()

        sub_type.refresh_from_db()
        self.assertEqual(sub_type.idu_name, OTHER_SUB_TYPES[0].idu_name)
        self.assertIn("Other sub types: created 0, updated 1, unchanged", output)

    def test_dry_run_persists_nothing(self):
        output = self._run("--dry-run")

        for model in EXPECTED_COUNTS:
            self.assertEqual(model.objects.count(), 0, model.__name__)

        total = sum(EXPECTED_COUNTS.values())
        self.assertIn(f"DRY RUN: would create {total}, update 0; 0 unchanged; rolled back.", output)
