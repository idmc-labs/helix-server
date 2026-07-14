import json

from django.core.files.base import ContentFile
from rest_framework import status

from apps.contrib.tasks import generate_external_endpoint_dump_file
from apps.entry.models import ExternalApiDump, Figure
from apps.entry.serializers import FigureReadOnlySerializer
from apps.entry.views import get_idu_data, get_idu_data_geojson
from utils.factories import (
    ClientFactory,
    CountryFactory,
    EntryFactory,
    EventFactory,
    FigureFactory,
    FigureLocationFactory,
    OrganizationFactory,
)
from utils.tests import HelixAPITestCase, HelixTestCase


class TestGetIduData(HelixTestCase):
    """The IDU export must only publish source links when the requesting client
    has 'share_source' enabled"""

    def setUp(self):
        super().setUp()
        self.country = CountryFactory.create()
        self.event = EventFactory.create()
        self.source = OrganizationFactory.create(name="ACLED")
        self.source_url = "https://example.com/source-report"
        self.entry = EntryFactory.create(url=self.source_url, is_confidential=False)
        self.figure = FigureFactory.create(
            entry=self.entry,
            country=self.country,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            role=Figure.ROLE.RECOMMENDED.value,
            include_idu=True,
            excerpt_idu="Some displacement happened.",
        )
        self.figure.sources.add(self.source)

    def _get_rows(self, include_sources):
        return list(get_idu_data({"include_sources": include_sources, "id": self.figure.id}))

    def test_source_links_excluded_when_sharing_disabled(self):
        rows = self._get_rows(include_sources=False)
        self.assertEqual(len(rows), 1)
        row = rows[0]

        # The source URL must be blanked out and no anchor/url must be included in
        # the popup text
        self.assertEqual(row["entry_url_or_document_url"], "")
        self.assertNotIn("<a href", row["standard_popup_text"])
        self.assertNotIn(self.source_url, row["standard_popup_text"])
        self.assertNotIn(self.source_url, row["custom_link_text"])

        # Source names are not blanked out only the links
        self.assertIn(self.source.name, row["sources_name"])

    def test_source_links_included_when_sharing_enabled(self):
        rows = self._get_rows(include_sources=True)
        self.assertEqual(len(rows), 1)
        row = rows[0]

        self.assertEqual(row["entry_url_or_document_url"], self.source_url)
        self.assertIn("<a href", row["standard_popup_text"])
        self.assertIn(self.source_url, row["standard_popup_text"])
        self.assertIn(self.source_url, row["custom_link_text"])

        self.assertIn(self.source.name, row["sources_name"])


class TestIduDumpGeneration(HelixTestCase):
    """The streamed dumps must stay valid, parseable, and value-identical to the
    per-record serializer output"""

    def setUp(self):
        super().setUp()
        self.country = CountryFactory.create()
        self.event = EventFactory.create()
        self.entry = EntryFactory.create(url="https://example.com/source-report", is_confidential=False)
        self.location = FigureLocationFactory.create()
        self.figure = FigureFactory.create(
            entry=self.entry,
            country=self.country,
            event=self.event,
            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            role=Figure.ROLE.RECOMMENDED.value,
            include_idu=True,
            excerpt_idu="Some displacement happened.",
            geo_locations=[self.location],
        )

    def test_json_dump_matches_per_record_serializer_output(self):
        generate_external_endpoint_dump_file(
            ExternalApiDump.ExternalApiType.IDUS_ALL,
            FigureReadOnlySerializer,
            get_idu_data,
            "idus_all.json",
            ExternalApiDump.Format.JSON,
        )

        dump = ExternalApiDump.objects.get(
            api_type=ExternalApiDump.ExternalApiType.IDUS_ALL,
            format=ExternalApiDump.Format.JSON,
            include_sources=False,
        )
        self.assertEqual(dump.status, ExternalApiDump.Status.COMPLETED)
        with dump.dump_file.open("rb") as fp:
            payload = json.load(fp)

        expected = FigureReadOnlySerializer(get_idu_data({"include_sources": False}), many=True).data
        self.assertEqual(payload, json.loads(json.dumps(expected)))
        self.assertEqual(payload[0]["id"], self.figure.id)

    def test_geojson_dump_is_valid_with_expected_feature(self):
        doc = json.loads(b"".join(get_idu_data_geojson({"include_sources": False})))

        self.assertEqual(doc["type"], "FeatureCollection")
        self.assertEqual(len(doc["features"]), 1)
        feature = doc["features"][0]
        self.assertEqual(feature["geometry"]["type"], "MultiPoint")
        self.assertTrue(feature["geometry"]["coordinates"])
        self.assertEqual(feature["properties"]["id"], self.figure.id)


class TestIduExportSourceRouting(HelixAPITestCase):
    """The IDU endpoint must serve the dump that matches the client's
    'share_source' flag"""

    def setUp(self):
        super().setUp()
        self.url = "/external-api/idus/last-180-days/"
        self.client_with_sources = ClientFactory.create(code="share-on", is_active=True, share_source=True)
        self.client_without_sources = ClientFactory.create(code="share-off", is_active=True, share_source=False)
        self.dump_with_sources = self._create_dump(include_sources=True, filename="idus_with_sources.json")
        self.dump_without_sources = self._create_dump(include_sources=False, filename="idus_without_sources.json")

    def _create_dump(self, include_sources, filename):
        dump = ExternalApiDump.objects.create(
            api_type=ExternalApiDump.ExternalApiType.IDUS,
            format=ExternalApiDump.Format.JSON,
            include_sources=include_sources,
            status=ExternalApiDump.Status.COMPLETED,
        )
        dump.dump_file.save(filename, ContentFile(b"[]"), save=True)
        return dump

    def test_client_without_share_source_is_served_dump_without_sources(self):
        response = self.client.get(f"{self.url}?client_id={self.client_without_sources.code}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("idus_without_sources", response.url)
        self.assertNotIn("idus_with_sources", response.url)

    def test_client_with_share_source_is_served_dump_with_sources(self):
        response = self.client.get(f"{self.url}?client_id={self.client_with_sources.code}")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("idus_with_sources", response.url)
        self.assertNotIn("idus_without_sources", response.url)
