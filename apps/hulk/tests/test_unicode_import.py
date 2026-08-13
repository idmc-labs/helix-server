"""
Encoding coverage for the pyhelix → helix bulk-import chain.

Source datasets carry place names and narratives in scripts cp1252 cannot
represent: Arabic/Persian, romanised transliterations with combining
diacritics, U+2017. Writing those rows with the platform's default encoding
(cp1252 on Windows) fails with ``UnicodeEncodeError`` before anything reaches
helix, which is what ``pyhelix.hulk.open_jsonl_writer`` pins to UTF-8.

What is covered here:

* the JSONL pyhelix writes is UTF-8 whatever the platform locale says, for
  both the success and the error files;
* the whole chain — pyhelix models → JSONL bytes → ``HulkBulkImportDataset``
  → ``HulkBulkImportHandler`` → real helix mutations — preserves the text
  byte-for-byte in ``Entry.article_title``, ``Event.name``,
  ``Event.event_narrative``, ``Figure.calculation_logic`` /
  ``source_excerpt`` / ``excerpt_idu`` and ``OSMName.display_name``.
"""

from __future__ import annotations

import datetime
import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.files.base import ContentFile
from django.test import SimpleTestCase
from pydantic import ValidationError
from pyhelix.hulk import HulkDataHandler, open_jsonl_writer
from pyhelix.models import (
    HulkAttachmentImport,
    HulkEntryImport,
    HulkEventImport,
    HulkFigureImport,
    HulkFigureImportLocation,
)

from apps.entry.models import Entry, Figure
from apps.event.models import Event
from apps.hulk.bulk.handler import HulkBulkImportHandler
from apps.hulk.models import HulkBulkImport, HulkBulkImportDataset, HulkEntry, HulkEvent, HulkFigure
from apps.users.enums import USER_ROLE
from utils.factories import CountryFactory, DisasterSubTypeFactory, OrganizationFactory
from utils.tests import HelixGraphQLTestCase, create_user_with_role

from .test_handler import _patch_download_file

# One sample per dataset that crashed a cp1252 writer, quoting the characters
# that broke it. Every value here is unrepresentable in cp1252 — asserted by
# ``test_samples_are_unrepresentable_in_cp1252`` so the coverage can't be
# silently weakened by editing a string.
UNICODE_SAMPLES = {
    # Afghanistan: Arabic/Persian script + romanised diacritics.
    "arabic_script": "Kandahār (قندهار) ولسوالی",
    # Haiti: U+2017 DOUBLE LOW LINE.
    "double_low_line": "Ouanaminthe‗, Nord-Est‗",
    # Iraq: combining cedilla (U+0327) + macrons.
    "combining_cedilla": "Ḩadīthah, Al-Anbār, Żumar",
    # Nepal: Devanagari transliteration diacritics + combining marks.
    "devanagari_translit": "Kāthmān̄ḍaū, Sindhupālcok",
    # Palestine: Arabic transliteration diacritics.
    "arabic_translit": "Ṭūbās, Şamāl al-Ḑiffah",
    # Yemen: modifier hamza / ayin (U+02BE, U+02BF).
    "hamza_ayin": "Ḩajjah (ʿAbs), Miʿyān, ʾAmrān",
}

ALL_SAMPLES = " | ".join(UNICODE_SAMPLES.values())

_NS = uuid.UUID("00000000-0000-0000-0000-000000000888")


def _u(label: str) -> str:
    return str(uuid.uuid5(_NS, label))


ATTACHMENT_UUID = _u("attachment")
ENTRY_UUID = _u("entry")
EVENT_UUID = _u("event")
FIGURE_UUID = _u("figure")
LOCATION_UUID = _u("location")

_IMPORT_TYPE_FOR_RESOURCE = {
    "attachments": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ATTACHMENT,
    "entries": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.ENTRY,
    "events": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.EVENT,
    "figures": HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE.FIGURE,
}


def _stub_helix_client() -> MagicMock:
    """
    Stand-in for the remote ``HelixClient`` pyhelix models resolve through.

    Only the ``*_sub_type_manager.validate_id_exists`` calls are reached while
    building rows offline; the ids these tests use are created by factories and
    validated for real once the handler replays the JSONL server-side.
    """
    return MagicMock()


class TestUnicodeSamples(SimpleTestCase):
    def test_samples_are_unrepresentable_in_cp1252(self):
        for name, sample in UNICODE_SAMPLES.items():
            with self.subTest(sample=name):
                with self.assertRaises(UnicodeEncodeError):
                    sample.encode("cp1252")


class TestPyhelixJsonlWriterEncoding(SimpleTestCase):
    """
    ``HulkDataHandler`` must not inherit the platform's text encoding — on
    Windows that is cp1252 and every row above would fail to write.
    """

    def test_open_jsonl_writer_pins_utf8_and_newline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            with open_jsonl_writer(path) as fh:
                self.assertEqual(fh.encoding.lower().replace("-", ""), "utf8")
                fh.write(ALL_SAMPLES + "\n")
            self.assertEqual(path.read_bytes(), (ALL_SAMPLES + "\n").encode("utf-8"))

    def test_every_writer_pins_the_encoding_rather_than_inheriting_it(self):
        """
        The regression guard proper. A run on a UTF-8 machine cannot tell a
        pinned encoding from an inherited one, so assert what the writers ask
        ``open`` for — that is what differs on a cp1252 box.
        """
        opened = []
        real_open = Path.open

        def recording_open(path, *args, **kwargs):
            # Path.open is patched process-wide; only the JSONL the handler
            # writes is under test.
            if path.suffix == ".jsonl":
                opened.append((path.name, kwargs))
            return real_open(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmp, patch.object(Path, "open", recording_open):
            handler = HulkDataHandler(export_dir=Path(tmp), helix_client=_stub_helix_client())
            with handler:
                pass

        # Every resource gets a rows file and an errors file.
        self.assertEqual(len(opened), 2 * len(handler._export_path_names))
        for name, kwargs in opened:
            with self.subTest(file=name):
                self.assertEqual(kwargs.get("encoding"), "utf-8")
                self.assertEqual(kwargs.get("newline"), "\n")

    def test_handler_writes_utf8_success_and_error_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            export_dir = Path(tmp)
            with HulkDataHandler(export_dir=export_dir, helix_client=_stub_helix_client()) as handler:
                for fh in (*handler._export_path_ref.values(), *handler._export_error_path_ref.values()):
                    self.assertEqual(fh.encoding.lower().replace("-", ""), "utf8")

                handler.handle_import_object(
                    HulkEventImport(
                        uuid=EVENT_UUID,
                        event_name=ALL_SAMPLES,
                        event_cause="DISASTER",
                        disaster_sub_type_id=1,
                        start_date=datetime.date(2024, 1, 1),
                        start_date_accuracy="DAY",
                        end_date=datetime.date(2024, 1, 31),
                        end_date_accuracy="DAY",
                        event_narrative=ALL_SAMPLES,
                        countries_id=[1],
                        event_codes=[],
                    )
                )

                # Both error paths run.py uses: a pydantic failure whose message
                # quotes the offending value, and a hand-built raw error row.
                with self.assertRaises(ValidationError) as ctx:
                    HulkEventImport(
                        uuid=EVENT_UUID,
                        event_name=ALL_SAMPLES,
                        # Not a CRISIS_TYPE — the raised message quotes it back.
                        event_cause=UNICODE_SAMPLES["arabic_script"],
                        start_date=datetime.date(2024, 1, 1),
                        start_date_accuracy="DAY",
                        end_date=datetime.date(2024, 1, 31),
                        end_date_accuracy="DAY",
                        event_narrative=ALL_SAMPLES,
                        countries_id=[1],
                        event_codes=[],
                    )
                handler.handle_import_error(HulkEventImport, ctx.exception)
                handler.handle_import_error_raw(
                    HulkFigureImport,
                    {"uuid": FIGURE_UUID, "error": f"country not found for: {ALL_SAMPLES}"},
                )

            events = (export_dir / "events.jsonl").read_bytes().decode("utf-8")
            self.assertEqual(json.loads(events)["event_narrative"], ALL_SAMPLES)

            event_errors = (export_dir / "errors_events.jsonl").read_bytes().decode("utf-8")
            self.assertIn(UNICODE_SAMPLES["arabic_script"], event_errors)

            figure_errors = (export_dir / "errors_figures.jsonl").read_bytes().decode("utf-8")
            self.assertEqual(json.loads(figure_errors)["raw"]["error"], f"country not found for: {ALL_SAMPLES}")


class TestUnicodeBulkImportEndToEnd(HelixGraphQLTestCase):
    """
    Full chain, no GraphQL mock: rows are built with the pyhelix models an
    integration script uses, serialised by ``HulkDataHandler``, uploaded as
    dataset files and replayed by the handler against the real helix
    mutations. Only the attachment download is stubbed (no network).
    """

    def setUp(self):
        self.user = create_user_with_role(USER_ROLE.ADMIN.name)
        self.country = CountryFactory.create(iso2="AF", iso3="AFG", idmc_short_name="Afghanistan")
        self.organization = OrganizationFactory.create()
        self.disaster_sub_type = DisasterSubTypeFactory.create()

    def _build_jsonl(self, export_dir: Path) -> dict:
        """Write the five JSONL files exactly as an integration script would."""
        with HulkDataHandler(export_dir=export_dir, helix_client=_stub_helix_client()) as handler:
            handler.handle_import_object(
                HulkAttachmentImport(
                    uuid=ATTACHMENT_UUID,
                    attachment_for="ENTRY",
                    file_url="https://example.invalid/report.pdf",
                )
            )
            handler.handle_import_object(
                HulkEntryImport(
                    uuid=ENTRY_UUID,
                    hulk_import_type="DOCUMENT",
                    attachment_uuid=ATTACHMENT_UUID,
                    entry_title=UNICODE_SAMPLES["arabic_script"],
                    publish_date=datetime.date(2024, 1, 15),
                    is_confidential=False,
                    publishers_id=[self.organization.id],
                )
            )
            handler.handle_import_object(
                HulkEventImport(
                    uuid=EVENT_UUID,
                    event_name=UNICODE_SAMPLES["devanagari_translit"],
                    event_cause="DISASTER",
                    disaster_sub_type_id=self.disaster_sub_type.id,
                    start_date=datetime.date(2024, 1, 1),
                    start_date_accuracy="DAY",
                    end_date=datetime.date(2024, 1, 31),
                    end_date_accuracy="DAY",
                    event_narrative=UNICODE_SAMPLES["double_low_line"],
                    countries_id=[self.country.id],
                    event_codes=[],
                )
            )
            handler.handle_import_object(
                HulkFigureImport(
                    uuid=FIGURE_UUID,
                    entry_uuid=ENTRY_UUID,
                    event_uuid=EVENT_UUID,
                    figure_cause="DISASTER",
                    disaster_sub_type_id=self.disaster_sub_type.id,
                    category="NEW_DISPLACEMENT",
                    term="DISPLACED",
                    quantifier="EXACT",
                    unit="PERSON",
                    figure_role="RECOMMENDED",
                    country_id=self.country.id,
                    start_date=datetime.date(2024, 1, 5),
                    start_date_accuracy="DAY",
                    end_date=datetime.date(2024, 1, 10),
                    end_date_accuracy="DAY",
                    reported_figure=100,
                    is_housing_destruction=False,
                    displacement_occurred="UNKNOWN",
                    is_disaggregated=False,
                    analysis_text=UNICODE_SAMPLES["combining_cedilla"],
                    source_excerpt_text=UNICODE_SAMPLES["arabic_translit"],
                    include_idu=True,
                    idu_text=UNICODE_SAMPLES["hamza_ayin"],
                    sources_id=[self.organization.id],
                    locations=[
                        HulkFigureImportLocation(
                            uuid=LOCATION_UUID,
                            display_name=ALL_SAMPLES,
                            country_name=self.country.idmc_short_name,
                            country_code=self.country.iso2,
                            identifier="ORIGIN",
                            accuracy="ADM0",
                            geocoder="CUSTOM_SOURCE",
                            latitude=33.9391,
                            longitude=67.71,
                        )
                    ],
                )
            )

        return {
            "attachments": (export_dir / "attachments.jsonl").read_bytes(),
            "entries": (export_dir / "entries.jsonl").read_bytes(),
            "events": (export_dir / "events.jsonl").read_bytes(),
            "figures": (export_dir / "figures.jsonl").read_bytes(),
        }

    def _attach(self, bulk: HulkBulkImport, resource: str, payload: bytes) -> HulkBulkImportDataset:
        dataset = HulkBulkImportDataset.objects.create(
            bulk_import=bulk,
            import_type=_IMPORT_TYPE_FOR_RESOURCE[resource].value,
        )
        dataset.import_file.save(f"{resource}.jsonl", ContentFile(payload), save=True)
        return dataset

    def test_unicode_survives_pyhelix_to_helix(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._build_jsonl(Path(tmp))

        # The bytes leaving pyhelix are UTF-8, not the platform encoding.
        for resource, payload in bundle.items():
            with self.subTest(resource=resource):
                payload.decode("utf-8")

        bulk = HulkBulkImport.objects.create(created_by=self.user)
        for resource, payload in bundle.items():
            self._attach(bulk, resource, payload)

        with _patch_download_file():
            HulkBulkImportHandler(bulk).handle()

        bulk.refresh_from_db()
        self.assertEqual(bulk.status, HulkBulkImport.HULK_BULK_IMPORT_STATUS.COMPLETED)
        success_count = sum(ds.success_count or 0 for ds in bulk.datasets.all())
        failure_count = sum(ds.failure_count or 0 for ds in bulk.datasets.all())
        self.assertEqual(
            (success_count, failure_count),
            (4, 0),
            [(ds.import_type, ds.failure_file.read() if ds.failure_file else None) for ds in bulk.datasets.all()],
        )

        entry = Entry.objects.get(pk=HulkEntry.objects.get(uuid=ENTRY_UUID).entity_id)
        self.assertEqual(entry.article_title, UNICODE_SAMPLES["arabic_script"])

        event = Event.objects.get(pk=HulkEvent.objects.get(uuid=EVENT_UUID).entity_id)
        self.assertEqual(event.name, UNICODE_SAMPLES["devanagari_translit"])
        self.assertEqual(event.event_narrative, UNICODE_SAMPLES["double_low_line"])

        figure = Figure.objects.get(pk=HulkFigure.objects.get(uuid=FIGURE_UUID).entity_id)
        self.assertEqual(figure.calculation_logic, UNICODE_SAMPLES["combining_cedilla"])
        self.assertEqual(figure.source_excerpt, UNICODE_SAMPLES["arabic_translit"])
        self.assertEqual(figure.excerpt_idu, UNICODE_SAMPLES["hamza_ayin"])
        self.assertEqual([loc.display_name for loc in figure.geo_locations.all()], [ALL_SAMPLES])

    def test_unicode_error_row_survives_into_the_failure_artifact(self):
        """
        The rejection path has to carry the text too: a row whose value cannot
        be parsed is quoted back in the error, and that error is written to
        ``failure_events.jsonl`` for the operator to read.
        """
        row = {
            "uuid": _u("event:unparsable-cause"),
            "event_name": UNICODE_SAMPLES["arabic_script"],
            # Not a CRISIS_TYPE — validate_and_parse_enum quotes the value back.
            "event_cause": UNICODE_SAMPLES["hamza_ayin"],
            "start_date": "2024-01-01",
            "start_date_accuracy": "DAY",
            "end_date": "2024-01-31",
            "end_date_accuracy": "DAY",
            "event_narrative": UNICODE_SAMPLES["double_low_line"],
            "countries_id": [self.country.id],
            "event_codes": [],
        }
        # pydantic's model_dump_json leaves non-ASCII unescaped, so the upload
        # helix has to decode is genuinely multi-byte UTF-8 — not \\u escapes.
        payload = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        self.assertNotEqual(payload, payload.decode("utf-8").encode("ascii", "backslashreplace"))

        bulk = HulkBulkImport.objects.create(created_by=self.user)
        dataset = self._attach(bulk, "events", payload)

        HulkBulkImportHandler(bulk).handle()

        dataset.refresh_from_db()
        self.assertEqual((dataset.success_count, dataset.failure_count), (0, 1))
        failure_rows = [json.loads(line) for line in dataset.failure_file.read().decode("utf-8").splitlines() if line]
        self.assertEqual(len(failure_rows), 1)
        error = json.dumps(failure_rows[0]["error"], ensure_ascii=False)
        self.assertIn(UNICODE_SAMPLES["hamza_ayin"], error)
