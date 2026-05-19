"""
Regression tests for the ``hulk_uuid`` column in figure/entry/event exports.

The original export wiring annotated the queryset as ``hulk_id`` while the
header + transformer expected ``hulk_uuid`` — so the column was emitted but
always empty. These tests pin the annotation name end-to-end so the column
actually carries the linked ``HulkFigure``/``HulkEntry``/``HulkEvent`` UUID.
"""

from __future__ import annotations

from apps.entry.models import Entry, Figure
from apps.event.models import Event
from apps.hulk.models import HulkBulkImport, HulkEntry, HulkEvent, HulkFigure
from apps.users.enums import USER_ROLE
from utils.factories import EntryFactory, EventFactory, FigureFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role


class TestFigureExportHulkUuid(HelixGraphQLTestCase):
    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.bulk = HulkBulkImport.objects.create(created_by=self.user)

    def _make_figure(self) -> Figure:
        # FigureFactory has no event SubFactory and event is NOT NULL on Figure.
        return FigureFactory.create(event=EventFactory.create())

    def test_hulk_uuid_column_populated_when_hulk_figure_exists(self):
        figure = self._make_figure()
        hulk_figure = HulkFigure.objects.create(bulk_import=self.bulk, entity=figure)

        sheets = Figure.get_figure_excel_sheets_data(Figure.objects.filter(id=figure.id))
        rows = list(sheets["data"])

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["hulk_uuid"], hulk_figure.uuid)

    def test_hulk_uuid_column_is_none_without_hulk_figure(self):
        figure = self._make_figure()

        sheets = Figure.get_figure_excel_sheets_data(Figure.objects.filter(id=figure.id))
        rows = list(sheets["data"])

        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["hulk_uuid"])

    def test_hulk_uuid_header_and_data_keys_match(self):
        """Header key must equal the annotation name — otherwise ``.values(*headers)``
        would either ``FieldError`` or silently drop the column."""
        figure = self._make_figure()
        HulkFigure.objects.create(bulk_import=self.bulk, entity=figure)

        sheets = Figure.get_figure_excel_sheets_data(Figure.objects.filter(id=figure.id))
        self.assertIn("hulk_uuid", sheets["headers"])
        self.assertIn("hulk_uuid", list(sheets["data"])[0])


class TestEntryExportHulkUuid(HelixGraphQLTestCase):
    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.bulk = HulkBulkImport.objects.create(created_by=self.user)

    def test_hulk_uuid_column_populated_when_hulk_entry_exists(self):
        entry = EntryFactory.create()
        hulk_entry = HulkEntry.objects.create(bulk_import=self.bulk, entity=entry)

        sheets = Entry.get_excel_sheets_data(self.user.id, {})
        rows = [r for r in sheets["data"] if r["id"] == entry.id]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["hulk_uuid"], hulk_entry.uuid)


class TestEventExportHulkUuid(HelixGraphQLTestCase):
    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.bulk = HulkBulkImport.objects.create(created_by=self.user)

    def test_hulk_uuid_column_populated_when_hulk_event_exists(self):
        event = EventFactory.create()
        hulk_event = HulkEvent.objects.create(bulk_import=self.bulk, entity=event)

        sheets = Event.get_excel_sheets_data(self.user.id, {})
        rows = [r for r in sheets["data"] if r["id"] == event.id]

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["hulk_uuid"], hulk_event.uuid)
