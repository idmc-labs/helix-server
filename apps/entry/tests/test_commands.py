import csv
import tempfile

from django.test import SimpleTestCase

from apps.contrib.models import BulkApiOperation
from apps.country.models import HouseholdSize
from apps.entry.management.commands.update_ahhs import calculate_gap_filling_method
from apps.entry.management.commands.update_figure_event import Command as UpdateFigureEventCommand
from apps.entry.models import Figure
from apps.event.models import Event
from utils.factories import CountryFactory, EventFactory, FigureFactory, UnifiedReviewCommentFactory
from utils.tests import HelixGraphQLTestCase


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
