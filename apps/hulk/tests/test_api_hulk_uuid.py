"""
GraphQL-level tests for the ``hulkUuid`` field on entry/event/figure types.

``hulkUuid`` is present (non-null) iff the entity was created through the
hulk/bulk pipeline, in which case it carries the linked hulk relation row's
UUID (used by the frontend to tally against the bulk-import input dataset).
It resolves ``null`` for entities created any other way.
"""

import json

from apps.hulk.models import HulkBulkImport, HulkEntry, HulkEvent, HulkFigure
from apps.users.enums import USER_ROLE
from utils.factories import EntryFactory, EventFactory, FigureFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

ENTRY_QUERY = "query($id: ID!) { entry(id: $id) { id hulkUuid } }"
EVENT_QUERY = "query($id: ID!) { event(id: $id) { id hulkUuid } }"
FIGURE_QUERY = "query($id: ID!) { figure(id: $id) { id hulkUuid } }"


class TestHulkUuidField(HelixGraphQLTestCase):
    def setUp(self) -> None:
        self.user = create_user_with_role(USER_ROLE.MONITORING_EXPERT.name)
        self.bulk = HulkBulkImport.objects.create(created_by=self.user)
        self.force_login(self.user)

    def _resolve(self, query: str, entity_id: int):
        response = self.query(query, variables={"id": str(entity_id)})
        self.assertResponseNoErrors(response)
        return json.loads(response.content)["data"]

    def test_entry_hulk_uuid_present(self):
        entry = EntryFactory.create(created_by=self.user)
        hulk_entry = HulkEntry.objects.create(bulk_import=self.bulk, entity=entry)
        data = self._resolve(ENTRY_QUERY, entry.id)
        self.assertEqual(data["entry"]["hulkUuid"], str(hulk_entry.uuid))

    def test_entry_hulk_uuid_null(self):
        entry = EntryFactory.create(created_by=self.user)
        data = self._resolve(ENTRY_QUERY, entry.id)
        self.assertIsNone(data["entry"]["hulkUuid"])

    def test_event_hulk_uuid_present(self):
        event = EventFactory.create()
        hulk_event = HulkEvent.objects.create(bulk_import=self.bulk, entity=event)
        data = self._resolve(EVENT_QUERY, event.id)
        self.assertEqual(data["event"]["hulkUuid"], str(hulk_event.uuid))

    def test_event_hulk_uuid_null(self):
        event = EventFactory.create()
        data = self._resolve(EVENT_QUERY, event.id)
        self.assertIsNone(data["event"]["hulkUuid"])

    def test_figure_hulk_uuid_present(self):
        figure = FigureFactory.create(event=EventFactory.create())
        hulk_figure = HulkFigure.objects.create(bulk_import=self.bulk, entity=figure)
        data = self._resolve(FIGURE_QUERY, figure.id)
        self.assertEqual(data["figure"]["hulkUuid"], str(hulk_figure.uuid))

    def test_figure_hulk_uuid_null(self):
        figure = FigureFactory.create(event=EventFactory.create())
        data = self._resolve(FIGURE_QUERY, figure.id)
        self.assertIsNone(data["figure"]["hulkUuid"])
