"""A figure's Source Type Classification is the lowest classification among its sources.

Level 1 is High and Level 3 is Low, so the lowest classification is the highest level number.
"""

import json
from datetime import date

from apps.entry.models import Figure
from apps.extraction.filters import FigureExtractionFilterSet
from apps.organization.models import OrganizationKind, SourceType
from apps.users.enums import USER_ROLE
from utils.factories import EventFactory, FigureFactory, OrganizationFactory, OrganizationKindFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

LEVEL = SourceType.SOURCE_TYPE_CLASSIFICATION
RELIABILITY = OrganizationKind.ORGANIZATION_RELIABILITY


class TestFigureSourcesClassification(HelixGraphQLTestCase):
    @classmethod
    def setUpTestData(cls):
        government = SourceType.objects.create(name="Government (test)", level=LEVEL.LEVEL_1)
        civilians = SourceType.objects.create(name="Civilians (test)", level=LEVEL.LEVEL_2)
        media = SourceType.objects.create(name="Media (test)", level=LEVEL.LEVEL_3)

        def source(source_type=None, reliability=RELIABILITY.LOW):
            kind = OrganizationKindFactory.create(source_type=source_type, reliability=reliability)
            return OrganizationFactory.create(organization_kind=kind)

        cls.level_1 = source(government, RELIABILITY.HIGH)
        cls.level_2 = source(civilians, RELIABILITY.MEDIUM)
        cls.level_3 = source(media, RELIABILITY.LOW)
        # A kind without a source type yet (retired in A7.2.3): falls back to its old reliability.
        cls.untyped_high = source(None, RELIABILITY.HIGH)
        cls.untyped_medium = source(None, RELIABILITY.MEDIUM)
        cls.no_kind = OrganizationFactory.create(organization_kind=None)

        event = EventFactory.create()
        common = dict(
            event=event,
            role=Figure.ROLE.RECOMMENDED,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
            start_date=date(2021, 3, 1),
            end_date=date(2021, 4, 1),
        )

        def figure(*sources):
            obj = FigureFactory.create(**common)
            obj.sources.set(sources)
            return obj

        cls.high_and_low = figure(cls.level_1, cls.level_3)
        cls.high_and_medium = figure(cls.level_1, cls.level_2)
        cls.only_high = figure(cls.level_1)
        cls.only_medium = figure(cls.level_2)
        cls.no_sources = figure()
        cls.untyped_only = figure(cls.untyped_high)
        cls.typed_high_and_untyped_medium = figure(cls.level_1, cls.untyped_medium)
        cls.no_kind_only = figure(cls.no_kind)
        cls.figures = [
            cls.high_and_low,
            cls.high_and_medium,
            cls.only_high,
            cls.only_medium,
            cls.no_sources,
            cls.untyped_only,
            cls.typed_high_and_untyped_medium,
            cls.no_kind_only,
        ]

    def _levels(self):
        return dict(
            Figure.objects.filter(id__in=[f.id for f in self.figures])
            .annotate(**Figure.annotate_sources_classification())
            .values_list("id", "sources_classification")
        )

    def test_lowest_classification_wins(self):
        levels = self._levels()
        self.assertEqual(levels[self.high_and_low.id], LEVEL.LEVEL_3.value)
        self.assertEqual(levels[self.high_and_medium.id], LEVEL.LEVEL_2.value)

    def test_single_source(self):
        levels = self._levels()
        self.assertEqual(levels[self.only_high.id], LEVEL.LEVEL_1.value)
        self.assertEqual(levels[self.only_medium.id], LEVEL.LEVEL_2.value)

    def test_no_classification(self):
        levels = self._levels()
        self.assertIsNone(levels[self.no_sources.id])
        self.assertIsNone(levels[self.no_kind_only.id])

    def test_kind_without_source_type_uses_old_reliability(self):
        levels = self._levels()
        self.assertEqual(levels[self.untyped_only.id], LEVEL.LEVEL_1.value)
        self.assertEqual(levels[self.typed_high_and_untyped_medium.id], LEVEL.LEVEL_2.value)

    def test_ordering(self):
        ids = [self.only_high.id, self.only_medium.id, self.high_and_low.id]
        qs = FigureExtractionFilterSet(data={}, ordering="sources_classification").qs.filter(id__in=ids)
        self.assertEqual(list(qs.order_by("sources_classification").values_list("id", flat=True)), ids)
        self.assertEqual(list(qs.order_by("-sources_classification").values_list("id", flat=True)), ids[::-1])

    def test_graphql_field(self):
        self.force_login(create_user_with_role(USER_ROLE.ADMIN.name))
        response = self.query(
            """
            query($id: ID!) {
                figure(id: $id) { sourcesClassification sourcesClassificationDisplay }
            }
            """,
            variables={"id": str(self.high_and_low.id)},
        )
        self.assertResponseNoErrors(response)
        self.assertEqual(
            json.loads(response.content)["data"]["figure"],
            {"sourcesClassification": "LEVEL_3", "sourcesClassificationDisplay": "Level 3 (Low)"},
        )

    def test_export_column(self):
        data = Figure.get_figure_excel_sheets_data(Figure.objects.filter(id__in=[self.high_and_low.id, self.no_sources.id]))
        headers = data["headers"]
        self.assertEqual(headers["sources_classification"], "Source type classification")
        self.assertNotIn("sources_reliability", headers)
        rows = {row["id"]: data["transformer"](row) for row in data["data"]}
        self.assertEqual(rows[self.high_and_low.id]["sources_classification"], "Level 3 (Low)")
        self.assertIsNone(rows[self.no_sources.id]["sources_classification"])
