import re

from django.db import connection
from django.test import TestCase

from apps.entry.models import Figure

# Partial indexes whose predicate hardcodes the integer, both in `Figure.Meta.indexes` and in the
# migrations that created them (`apps/entry/migrations/0118_figure_aggregation_indexes.py` for the
# first two, `0119_figure_event_index_include.py` for the third). The enum class is not in scope
# inside `Meta`, so the condition is written as `models.Q(role=0)`; renumbering `Figure.ROLE` would
# leave all three matching TRIANGULATION rows instead, and every aggregation that relies on them
# would quietly fall back to a sequential scan without a single failing test.
ROLE_ZERO_PARTIAL_INDEXES = (
    "figure_ctry_cat_end_rec_idx",
    "figure_ctry_cat_start_rec_idx",
    "figure_event_cat_role_rec_idx",
)

ROLE_ZERO_PREDICATE = re.compile(r"role\s*=\s*0")


class RecommendedRoleConstantTestCase(TestCase):
    """`Figure.ROLE.RECOMMENDED` must stay 0, because three partial indexes say so literally."""

    def test_recommended_role_is_zero(self):
        assert Figure.ROLE.RECOMMENDED.value == 0, ROLE_ZERO_PARTIAL_INDEXES

    def test_the_partial_indexes_still_carry_the_literal_predicate(self):
        # Reads the live definitions rather than the migration text, so the assertion also covers
        # a hand-written or squashed migration that drifts from `Figure.Meta.indexes`.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = %s AND indexname = ANY(%s)",
                [Figure._meta.db_table, list(ROLE_ZERO_PARTIAL_INDEXES)],
            )
            definitions = dict(cursor.fetchall())

        # Non-vacuity guard: a renamed or dropped index must fail here, not silently pass by
        # matching nothing.
        assert sorted(definitions) == sorted(ROLE_ZERO_PARTIAL_INDEXES), sorted(definitions)
        for name, definition in definitions.items():
            assert ROLE_ZERO_PREDICATE.search(definition) is not None, (name, definition)
