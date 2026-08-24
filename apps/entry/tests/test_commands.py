import csv
import tempfile
from datetime import date
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.contrib.models import BulkApiOperation
from apps.country.models import HouseholdSize
from apps.entry.management.commands.update_ahhs import Command as UpdateAhhsCommand
from apps.entry.management.commands.update_ahhs import calculate_gap_filling_method, rewrite_excerpt_idu
from apps.entry.management.commands.update_figure_event import Command as UpdateFigureEventCommand
from apps.entry.models import Figure
from apps.event.models import Event
from utils.factories import (
    CountryFactory,
    EventFactory,
    FigureFactory,
    HouseholdSizeFactory,
    UnifiedReviewCommentFactory,
)
from utils.tests import HelixGraphQLTestCase, HelixTestCase


class TestCalculateGapFillingMethod(SimpleTestCase):
    def test_reference_year_equals_year_is_exact(self):
        self.assertEqual(
            calculate_gap_filling_method(2020, 2020),
            HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR,
        )

    def test_reference_year_after_year_is_backward_filling(self):
        self.assertEqual(
            calculate_gap_filling_method(2020, 2022),
            HouseholdSize.GAP_FILLING_METHOD.BACKWARD_FILLING,
        )

    def test_reference_year_before_year_is_forward_filling(self):
        self.assertEqual(
            calculate_gap_filling_method(2020, 2018),
            HouseholdSize.GAP_FILLING_METHOD.FORWARD_FILLING,
        )


class TestRewriteExcerptIdu(SimpleTestCase):
    def test_plain_digits_are_replaced(self):
        rewrite = rewrite_excerpt_idu("a total of 1200 people were displaced", 1200, 1500)
        self.assertEqual(rewrite.text, "a total of 1500 people were displaced")
        self.assertEqual(rewrite.substitutions, 1)
        self.assertEqual(rewrite.ambiguous_matches, 0)

    def test_comma_separated_value_keeps_its_grouping(self):
        self.assertEqual(rewrite_excerpt_idu("around 1,200 people", 1200, 1500).text, "around 1,500 people")

    def test_ungrouped_value_stays_ungrouped(self):
        self.assertEqual(rewrite_excerpt_idu("around 1200 people", 1200, 1500).text, "around 1500 people")

    def test_grouping_is_applied_per_occurrence(self):
        self.assertEqual(
            rewrite_excerpt_idu("2,051 people; 2051 people", 2051, 1743).text,
            "1,743 people; 1743 people",
        )

    def test_grouping_drops_out_when_the_new_total_is_shorter(self):
        self.assertEqual(rewrite_excerpt_idu("1,010 people", 1010, 964).text, "964 people")

    def test_absent_total_leaves_excerpt_untouched(self):
        excerpt = "2 houses were destroyed"
        rewrite = rewrite_excerpt_idu(excerpt, 7, 5)
        self.assertEqual(rewrite.text, excerpt)
        self.assertEqual(rewrite.substitutions, 0)
        self.assertEqual(rewrite.ambiguous_matches, 0)

    def test_word_boundary_prevents_matching_inside_a_longer_number(self):
        self.assertEqual(rewrite_excerpt_idu("50 of 1500 households", 50, 60).text, "60 of 1500 households")

    def test_every_person_total_occurrence_is_replaced(self):
        self.assertEqual(
            rewrite_excerpt_idu("120 people displaced; 120 people returned", 120, 90).text,
            "90 people displaced; 90 people returned",
        )

    def test_a_day_of_month_is_not_substituted(self):
        excerpt = "on 21 July 2025, a total of 20 people were displaced"
        rewrite = rewrite_excerpt_idu(excerpt, 21, 20)
        self.assertEqual(rewrite.text, excerpt)
        self.assertEqual(rewrite.substitutions, 0)
        self.assertEqual(rewrite.ambiguous_matches, 1)

    def test_the_person_total_is_substituted_while_the_date_is_left_alone(self):
        rewrite = rewrite_excerpt_idu("on 31 March 2025, a total of 31 people", 31, 30)
        self.assertEqual(rewrite.text, "on 31 March 2025, a total of 30 people")
        self.assertEqual(rewrite.substitutions, 1)
        self.assertEqual(rewrite.ambiguous_matches, 1)

    def test_a_date_written_month_first_is_not_substituted(self):
        excerpt = "displaced on March 14, 2025"
        self.assertEqual(rewrite_excerpt_idu(excerpt, 14, 13).text, excerpt)

    def test_a_glued_ordinal_day_is_never_reached(self):
        # The trailing word boundary cannot match "8th" at all, so the guard never sees it.
        # Out of scope on purpose: such a figure still reaches the verification list, under the
        # "states neither figure" reason rather than as an ambiguous match.
        excerpt = "displaced on the 8th of June"
        rewrite = rewrite_excerpt_idu(excerpt, 8, 6)
        self.assertEqual(rewrite.text, excerpt)
        self.assertEqual(rewrite.substitutions, 0)
        self.assertEqual(rewrite.ambiguous_matches, 0)

    def test_a_spaced_ordinal_day_is_refused(self):
        excerpt = "displaced on the 8 th of June"
        rewrite = rewrite_excerpt_idu(excerpt, 8, 6)
        self.assertEqual(rewrite.text, excerpt)
        self.assertEqual(rewrite.substitutions, 0)
        self.assertEqual(rewrite.ambiguous_matches, 1)

    def test_a_household_count_is_not_substituted(self):
        excerpt = "500 houses were destroyed"
        rewrite = rewrite_excerpt_idu(excerpt, 500, 400)
        self.assertEqual(rewrite.text, excerpt)
        self.assertEqual(rewrite.ambiguous_matches, 1)

    def test_a_household_noun_behind_adjectives_is_not_substituted(self):
        excerpt = "500 newly destroyed houses"
        self.assertEqual(rewrite_excerpt_idu(excerpt, 500, 400).text, excerpt)

    def test_a_prefix_of_a_longer_grouped_number_is_not_substituted(self):
        excerpt = "a total of 1,234,567 people"
        self.assertEqual(rewrite_excerpt_idu(excerpt, 1234, 999).text, excerpt)


class TestUpdateAhhsCommand(HelixTestCase):
    YEAR = 2020

    def setUp(self):
        super().setUp()
        self.country = CountryFactory.create(iso3="NPL")
        # Current active AHHS the figures were computed against.
        self.active_hhs = HouseholdSizeFactory.create(
            country=self.country,
            year=self.YEAR,
            size=5.0,
            is_active=True,
            data_source_category="Census",
            source="Src",
            source_link="http://example.com",
            notes="note",
            reference_date=date(self.YEAR, 1, 1),
            gap_filling_method=HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR,
        )
        # A household-unit figure whose stored household_size matches the active AHHS.
        event = EventFactory.create(countries=[self.country])
        self.figure = FigureFactory.create(
            event=event,
            country=self.country,
            unit=Figure.UNIT.HOUSEHOLD,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            start_date=date(self.YEAR, 6, 1),
            end_date=date(self.YEAR, 6, 30),
            reported=10,
            household_size=5.0,
            total_figures=50,
            excerpt_idu="A total of 50 people were displaced.",
        )

    def _write_csv(self, rows):
        fields = ["Year", "AHHS", "ISO3", "Data source category", "Reference date", "Source", "Source link", "Notes"]
        csv_file = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        csv_file.close()
        return csv_file.name

    def _default_row(self, ahhs="6"):
        return {
            "Year": str(self.YEAR),
            "AHHS": ahhs,
            "ISO3": "NPL",
            "Data source category": "Census",
            "Reference date": f"{self.YEAR}-01-01",
            "Source": "Src",
            "Source link": "http://example.com",
            "Notes": "note",
        }

    def _active_hhs_qs(self):
        return HouseholdSize.objects.filter(country=self.country, year=self.YEAR, is_active=True)

    def test_numbers_mode_updates_figure_values_and_excerpt_not_note(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers")

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 6.0)
        self.assertEqual(self.figure.total_figures, 60)
        self.assertIn("60", self.figure.excerpt_idu)
        self.assertNotIn("50", self.figure.excerpt_idu)
        self.assertFalse(self.figure.calculation_logic)

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().size, 6.0)

    def test_numbers_and_note_mode_appends_calculation_logic(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers_and_note",
            retroactive_update_date="2024-03-27",
        )

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.total_figures, 60)
        self.assertIn("retrospective update in AHHS", self.figure.calculation_logic)

    def test_none_mode_imports_ahhs_but_leaves_figures_untouched(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none")

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().size, 6.0)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 5.0)
        self.assertEqual(self.figure.total_figures, 50)

    def test_unchanged_row_is_skipped(self):
        # CSV values are identical to the current active record, so no new record is created.
        csv_path = self._write_csv([self._default_row(ahhs="5")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers")

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().pk, self.active_hhs.pk)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 5.0)
        self.assertEqual(self.figure.total_figures, 50)

    def test_dry_run_rolls_back_when_the_body_returns_early(self):
        # `run_update` holding the work means an early return inside it still reaches the
        # rollback flag in `handle`. The flag additionally sits in a finally block, which no
        # test can distinguish: every path it covers is already covered by the extraction or
        # by atomic() rolling back on an exception.
        country = self.country

        def early_return(command_self, **kwargs):
            HouseholdSize.objects.create(
                country=country,
                year=1999,
                size=9.9,
                is_active=True,
                data_source_category="probe",
                source="probe",
            )
            return

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        with mock.patch.object(UpdateAhhsCommand, "run_update", early_return):
            call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none", dry_run=True)

        self.assertFalse(HouseholdSize.objects.filter(year=1999).exists())

    def test_a_real_run_keeps_what_the_body_wrote_before_returning_early(self):
        # The mirror image, and the half that would catch a finally block firing unconditionally.
        country = self.country

        def early_return(command_self, **kwargs):
            HouseholdSize.objects.create(
                country=country,
                year=1999,
                size=9.9,
                is_active=True,
                data_source_category="probe",
                source="probe",
            )
            return

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        with mock.patch.object(UpdateAhhsCommand, "run_update", early_return):
            call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none")

        self.assertTrue(HouseholdSize.objects.filter(year=1999).exists())

    def test_dry_run_rolls_back_all_changes(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", dry_run=True)

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().pk, self.active_hhs.pk)
        self.assertEqual(active.get().size, 5.0)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 5.0)
        self.assertEqual(self.figure.total_figures, 50)

    def test_numbers_and_note_mode_requires_retroactive_update_date(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        with self.assertRaises(CommandError):
            call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers_and_note")

    def test_dirty_duplicate_active_records_are_all_replaced(self):
        # A second active record for the same country/year makes the set "dirty"; the
        # unchanged-skip only trusts a lone active record, so both must be deactivated.
        HouseholdSizeFactory.create(
            country=self.country,
            year=self.YEAR,
            size=9.0,
            is_active=True,
            reference_date=date(self.YEAR, 1, 1),
            gap_filling_method=HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR,
        )
        csv_path = self._write_csv([self._default_row(ahhs="7")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none")

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().size, 7.0)
        # Two previous actives deactivated + one freshly created.
        self.assertEqual(HouseholdSize.objects.filter(country=self.country, year=self.YEAR).count(), 3)

    def test_zero_ahhs_leaves_figure_untouched(self):
        # A zero AHHS is a legitimate import (some regions lack permanent residence),
        # but it must never rewrite figures to zero.
        csv_path = self._write_csv([self._default_row(ahhs="")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers")

        self.assertEqual(self._active_hhs_qs().get().size, 0.0)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 5.0)
        self.assertEqual(self.figure.total_figures, 50)

    def test_skipped_figure_is_logged_for_verification_with_its_own_reason(self):
        # A figure whose household size cannot be reconciled is left alone and flagged.
        self.figure.household_size = 9.0
        self.figure.total_figures = 54
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 9.0)
        self.assertEqual(self.figure.total_figures, 54)
        self.assertIn(f"MANUAL_VERIFICATION\tfigure={self.figure.pk}", output)
        self.assertIn("does not match the AHHS on record", output)
        self.assertIn("Figures needing manual verification: 1", output)

    def test_figure_with_mismatched_household_size_is_skipped(self):
        # A figure whose stored household_size diverges from the active AHHS was computed
        # against a different value, so the command must leave it alone.
        mismatched = FigureFactory.create(
            event=self.figure.event,
            country=self.country,
            unit=Figure.UNIT.HOUSEHOLD,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            start_date=date(self.YEAR, 6, 1),
            end_date=date(self.YEAR, 6, 30),
            reported=10,
            household_size=4.0,
            total_figures=40,
            excerpt_idu="A total of 40 people were displaced.",
        )
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers")

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 4.0)
        self.assertEqual(mismatched.total_figures, 40)

    def test_numbers_mode_rewrites_comma_separated_excerpt_value(self):
        # The excerpt rewrite matches a value written with thousands separators and keeps them.
        self.figure.reported = 200
        self.figure.household_size = 5.0
        self.figure.total_figures = 1000
        self.figure.excerpt_idu = "A total of 1,000 people were displaced."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers")

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.total_figures, 1200)
        self.assertEqual(self.figure.excerpt_idu, "A total of 1,200 people were displaced.")

    def test_figure_whose_excerpt_cannot_be_updated_is_logged_for_verification(self):
        # The excerpt states the total only as a date, so it is left alone and flagged.
        self.figure.reported = 6
        self.figure.household_size = 5.0
        self.figure.total_figures = 30
        self.figure.excerpt_idu = "On 30 June 2020, families were displaced."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.total_figures, 36)
        self.assertEqual(self.figure.excerpt_idu, "On 30 June 2020, families were displaced.")
        self.assertIn(f"MANUAL_VERIFICATION\tfigure={self.figure.pk}", output)
        self.assertIn("total=30->36", output)
        self.assertIn("Figures needing manual verification: 1", output)

    def test_figure_whose_excerpt_is_updated_is_not_logged_for_verification(self):
        self.figure.reported = 6
        self.figure.household_size = 5.0
        self.figure.total_figures = 30
        self.figure.excerpt_idu = "A total of 30 people were displaced."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.excerpt_idu, "A total of 36 people were displaced.")
        self.assertNotIn("MANUAL_VERIFICATION", output)
        self.assertIn("Figures needing manual verification: 0", output)

    def test_changelog_names_only_the_fields_that_moved(self):
        self.figure.reported = 6
        self.figure.household_size = 5.0
        self.figure.total_figures = 30
        self.figure.excerpt_idu = "A total of 30 people were displaced."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.assertIn(f"FIGURE_CHANGED\tfigure={self.figure.pk}\t", output)
        self.assertIn("household_size=5.0->6.0\ttotal_figures=30->36\texcerpt_idu=rewritten", output)
        # Untouched in this mode, so absent rather than reported as unchanged.
        self.assertNotIn("calculation_logic=", output)

    def test_changelog_omits_a_total_that_rounding_left_alone(self):
        self.figure.reported = 1
        self.figure.household_size = 5.0
        self.figure.total_figures = 5
        self.figure.excerpt_idu = None
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="5.4")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.assertIn("household_size=5.0->5.4", output)
        self.assertNotIn("total_figures=", output)
        self.assertNotIn("excerpt_idu=", output)

    def test_changelog_records_the_note_without_quoting_it(self):
        self.figure.reported = 6
        self.figure.household_size = 5.0
        self.figure.total_figures = 30
        self.figure.calculation_logic = "Existing logic."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers_and_note",
            retroactive_update_date="2026-01-15",
            stdout=out,
        )
        output = out.getvalue()

        self.assertIn("calculation_logic=note_appended", output)
        self.assertNotIn("Existing logic.->", output)

    def test_the_ahhs_pass_emits_no_per_row_line_of_its_own(self):
        # The archived row records what this country-year held before, so the run reports counts.
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none", stdout=out)
        output = out.getvalue()

        self.assertNotIn("Deactivated", output)
        self.assertNotIn("Created AHHS item", output)
        self.assertNotIn("is unchanged. Skipping", output)
        self.assertIn("AHHS: created 1 (value changed 1, metadata only 0), unchanged 0", output)

    def test_the_figure_pass_emits_no_per_figure_line_of_its_own(self):
        # One log only: everything per-figure appears in the end blocks, nothing during the pass.
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", stdout=out)
        output = out.getvalue()

        self.assertNotIn("updating household size", output)
        self.assertNotIn("updating total figures", output)
        self.assertNotIn("household size does not match", output)

    def test_note_appends_to_existing_calculation_logic(self):
        # An existing calculation_logic must survive and the retrospective note be appended.
        self.figure.calculation_logic = "Existing calculation logic."
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers_and_note",
            retroactive_update_date="2024-03-27",
        )

        self.figure.refresh_from_db()
        self.assertIn("Existing calculation logic.", self.figure.calculation_logic)
        self.assertIn("retrospective update in AHHS", self.figure.calculation_logic)
        self.assertIn("\n\n", self.figure.calculation_logic)

    def _mismatched_figure(self, household_size, total_figures, excerpt_idu=None):
        """A household figure whose stored household size disagrees with the active AHHS of 5.0."""
        return FigureFactory.create(
            event=self.figure.event,
            country=self.country,
            unit=Figure.UNIT.HOUSEHOLD,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            start_date=date(self.YEAR, 6, 1),
            end_date=date(self.YEAR, 6, 30),
            reported=10,
            household_size=household_size,
            total_figures=total_figures,
            excerpt_idu=excerpt_idu,
        )

    def test_force_rewrites_a_figure_whose_household_size_does_not_match_the_ahhs(self):
        # The mirror of test_figure_with_mismatched_household_size_is_skipped.
        mismatched = self._mismatched_figure(4.0, 40, "A total of 40 people were displaced.")

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", force_all_figures=True)

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 6.0)
        self.assertEqual(mismatched.total_figures, 60)
        self.assertEqual(mismatched.excerpt_idu, "A total of 60 people were displaced.")

    def test_force_reconciles_a_figure_when_the_csv_row_is_identical(self):
        # Nothing about the AHHS record changes, so without force the country is out of scope
        # entirely. Force answers for every country the CSV named.
        mismatched = self._mismatched_figure(4.0, 40)

        csv_path = self._write_csv([self._default_row(ahhs="5")])
        call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="numbers", force_all_figures=True)

        active = self._active_hhs_qs()
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().pk, self.active_hhs.pk)

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 5.0)
        self.assertEqual(mismatched.total_figures, 50)

    def test_force_is_rejected_with_none_mode(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        with self.assertRaises(CommandError):
            call_command("update_ahhs", csv_path, year=self.YEAR, figure_update_mode="none", force_all_figures=True)

    def test_force_dry_run_rolls_back(self):
        mismatched = self._mismatched_figure(4.0, 40)

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            dry_run=True,
        )

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 4.0)
        self.assertEqual(mismatched.total_figures, 40)

    def test_forced_figure_matching_an_archived_ahhs_is_a_catch_up_and_is_not_flagged(self):
        # 4.0 stood for this country-year at some point, so overwriting the figure needs no review.
        HouseholdSizeFactory.create(
            country=self.country,
            year=self.YEAR,
            size=4.0,
            is_active=False,
            reference_date=date(self.YEAR, 1, 1),
            gap_filling_method=HouseholdSize.GAP_FILLING_METHOD.EXACT_YEAR,
        )
        mismatched = self._mismatched_figure(4.0, 40, "A total of 40 people were displaced.")

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            stdout=out,
        )
        output = out.getvalue()

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 6.0)
        self.assertIn("caught up with a superseded AHHS 1", output)
        self.assertIn("no AHHS on record ever matched 0", output)
        self.assertIn(f"FIGURE_CHANGED\tfigure={mismatched.pk}\t", output)
        self.assertIn("forced=ahhs_on_record_was_5.0", output)
        self.assertNotIn("matches no AHHS ever recorded", output)

    def test_forced_figure_matching_no_recorded_ahhs_is_overwritten_and_flagged(self):
        # 3.3 was never on record for this country-year, so nothing explains where it came from.
        mismatched = self._mismatched_figure(3.3, 33, "A total of 33 people were displaced.")

        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            stdout=out,
        )
        output = out.getvalue()

        mismatched.refresh_from_db()
        self.assertEqual(mismatched.household_size, 6.0)
        self.assertEqual(mismatched.total_figures, 60)
        self.assertIn("caught up with a superseded AHHS 0", output)
        self.assertIn("no AHHS on record ever matched 1", output)
        self.assertIn("1 figures: stored household size matches no AHHS ever recorded", output)
        self.assertIn(f"MANUAL_VERIFICATION\tfigure={mismatched.pk}", output)
        self.assertIn("total=33->60", output)
        self.assertIn("Figures needing manual verification: 1", output)

    def test_force_leaves_a_figure_untouched_when_the_ahhs_is_zero(self):
        csv_path = self._write_csv([self._default_row(ahhs="")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            stdout=out,
        )
        output = out.getvalue()

        self.assertEqual(self._active_hhs_qs().get().size, 0.0)

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.household_size, 5.0)
        self.assertEqual(self.figure.total_figures, 50)
        self.assertIn("1 figures: AHHS is zero; figure left untouched rather than zeroed", output)
        self.assertIn(f"MANUAL_VERIFICATION\tfigure={self.figure.pk}", output)

    def test_an_inconsistent_total_is_reported_without_being_rewritten(self):
        # household_size already agrees with the AHHS, so nothing here justifies a rewrite.
        self.figure.total_figures = 999
        self.figure.save()

        csv_path = self._write_csv([self._default_row(ahhs="5")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            stdout=out,
        )
        output = out.getvalue()

        self.figure.refresh_from_db()
        self.assertEqual(self.figure.total_figures, 999)
        self.assertIn("1 figures: total_figures does not equal reported x household_size", output)
        self.assertIn("does not equal reported 10 x household size 5.0 (50)", output)

    def test_force_states_its_scope_before_writing(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            stdout=out,
        )
        output = out.getvalue()

        self.assertIn(f"FORCE: reconciling every household figure in {self.YEAR} against the active AHHS.", output)
        self.assertIn("countries in scope: 1 (from CSV)", output)
        self.assertIn("figures matched: 1", output)
        self.assertIn("writes will be committed", output)

    def test_the_force_scope_says_when_nothing_will_be_committed(self):
        csv_path = self._write_csv([self._default_row(ahhs="6")])
        out = StringIO()
        call_command(
            "update_ahhs",
            csv_path,
            year=self.YEAR,
            figure_update_mode="numbers",
            force_all_figures=True,
            dry_run=True,
            stdout=out,
        )

        self.assertIn("dry run: nothing will be committed", out.getvalue())


class TestUpdateFigureEventMigrations(HelixGraphQLTestCase):
    def test_update_figure_event_migrations(self):
        country = CountryFactory.create()
        event1, event2, event_with_no_figure = EventFactory.create_batch(3, countries=[country])

        command_figure_kwargs = dict(
            country=country,
            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
            total_figures=100,
            start_date="2022-05-09",
            end_date="2022-05-14",
        )
        figure1 = FigureFactory.create(
            **command_figure_kwargs,
            event=event1,
        )
        figure2 = FigureFactory(
            **command_figure_kwargs,
            event=event2,
        )
        figure3 = FigureFactory(
            **command_figure_kwargs,
            event=event_with_no_figure,
        )
        unified_review_comment1 = UnifiedReviewCommentFactory.create(
            figure=figure1,
            event=event1,
        )
        unified_review_comment2 = UnifiedReviewCommentFactory.create(
            figure=figure2,
            event=event2,
        )

        fields = ["ID", "Event ID", "New Event ID", "Event to be deleted"]
        data = [
            {
                "ID": figure1.id,
                "Event ID": event1.id,
                "New Event ID": event2.id,
                "Event to be deleted": event1.id,
            },
            {
                "ID": figure2.id,
                "Event ID": event2.id,
                "New Event ID": event1.id,
                "Event to be deleted": event2.id,
            },
            {
                "ID": figure3.id,
                "Event ID": event_with_no_figure.id,
                "New Event ID": event1.id,
                "Event to be deleted": event_with_no_figure,
            },
        ]

        # Generate CSV file
        with tempfile.NamedTemporaryFile(mode="w", delete=True) as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data)
            csv_file.seek(0)
            csv_file_path = csv_file.name

            # Run the command
            with self.captureOnCommitCallbacks(execute=True):
                UpdateFigureEventCommand().handle(csv_file_path=csv_file_path, delete_empty_events=True)

        # Check if the figures have been updated
        figure1.refresh_from_db()
        figure2.refresh_from_db()
        figure3.refresh_from_db()

        self.assertEqual(
            {
                (figure1.id, figure1.event_id),
                (figure2.id, figure2.event_id),
                (figure3.id, figure3.event_id),
            },
            {
                (figure1.id, event2.id),
                (figure2.id, event1.id),
                (figure3.id, event1.id),
            },
            BulkApiOperation.objects.order_by("id").last().failure_list,
        )

        # Check if the events have been deleted
        self.assertFalse(Event.objects.filter(id=event_with_no_figure.id).exists())

        # Check the unified review comments
        unified_review_comment1.refresh_from_db()
        unified_review_comment2.refresh_from_db()

        self.assertEqual(unified_review_comment1.event_id, event2.id)
        self.assertEqual(unified_review_comment2.event_id, event1.id)
