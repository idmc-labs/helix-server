import csv
import tempfile
from datetime import date

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from apps.contrib.models import BulkApiOperation
from apps.country.models import HouseholdSize
from apps.entry.management.commands.update_ahhs import calculate_gap_filling_method
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
