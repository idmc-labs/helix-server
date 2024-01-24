from collections import defaultdict
from django.test import TestCase

from utils.factories import (
    EventFactory,
    FigureFactory,
    ViolenceSubTypeFactory,
    ViolenceFactory,
    ReportFactory,
    ExtractionQueryFactory,
)

from apps.event.models import (
    Event,
    Violence,
    ViolenceSubType,
)
from apps.report.models import Report
from apps.extraction.models import ExtractionQuery
from apps.entry.models import Figure


from apps.event.migrations.change_violence_types_and_sub_types import migrate_data


class ViolenceChangeTestCase(TestCase):
    def test_change_violence_types_and_sub_types(self):
        CONFLICT_TYPES = {
            "International armed conflict(IAC)": [
                "Military Occupation",
                "IAC (other than occupation)",
                "Other (IAC)",
                "Unclear (IAC)",
                "Unknown (IAC)"
            ],
            "Non-International armed conflict (NIAC)": [
                "NSAG(s) vs. State actor(s)",
                "NSAG(s) vs. NSAG(s)",
                "Other (NIAC)",
                "Unclear (NIAC)",
                "Unknown (NIAC)"
            ],
            "Other situations of violence (OSV)": [
                "Civilian-state violence",
                "Crime-related",
                "Communal violence",
                "Other (OSV)",
                "Unclear (OSV)",
                "Unknown (OSV)"
            ],
            "Other": [
                "Other (Other)",
                "Unclear (Other)",
                "Unknown (Other)",
            ],
            "Unknown": [
                "Unclear (Unknown)",
                "Unknown (Unknown)",
            ]
        }

        def _get_table_counts_by_violence(_id):
            return {
                'event': Event.objects.filter(violence=_id).count(),
                'figure': Figure.objects.filter(violence=_id).count(),
                'report': Report.filter_figure_violence_types.through.objects.filter(violence=_id).count(),
                'extractionquery': ExtractionQuery.filter_figure_violence_types.through.objects.filter(violence=_id).count()
            }

        def _get_table_counts_by_sub_violence(_id):
            return {
                'event': Event.objects.filter(violence_sub_type=_id).count(),
                'figure': Figure.objects.filter(violence_sub_type=_id).count(),
                'report': Report.filter_figure_violence_sub_types.through.objects.filter(violencesubtype=_id).count(),
                'extractionquery': (
                    ExtractionQuery.filter_figure_violence_sub_types.through.objects.filter(violencesubtype=_id).count()
                ),
            }

        def _create_objs_in_bulk(model, related_objs, related_obj_key, **kwargs):
            return model.objects.bulk_create([
                model(**{
                    **kwargs,
                    related_obj_key: related_obj,
                })
                for related_obj in related_objs
            ])

        event = EventFactory.create()
        reports = ReportFactory.create_batch(5)
        extraction_queries = ExtractionQueryFactory.create_batch(6)
        for name, violence_sub_types_name in CONFLICT_TYPES.items():
            violence_type = ViolenceFactory.create(name=name)
            EventFactory.create_batch(10, violence=violence_type)
            FigureFactory.create_batch(20, event=event, violence=violence_type)
            _create_objs_in_bulk(
                Report.filter_figure_violence_types.through, reports, 'report',
                violence=violence_type,
            )
            _create_objs_in_bulk(
                ExtractionQuery.filter_figure_violence_types.through, extraction_queries, 'extractionquery',
                violence=violence_type,
            )

            for sub_name in violence_sub_types_name:
                violence_sub_type = ViolenceSubTypeFactory.create(name=sub_name, violence=violence_type)
                EventFactory.create_batch(50, violence_sub_type=violence_sub_type)
                FigureFactory.create_batch(60, event=event, violence_sub_type=violence_sub_type)
                _create_objs_in_bulk(
                    Report.filter_figure_violence_sub_types.through, reports, 'report',
                    violencesubtype=violence_sub_type,
                )
                _create_objs_in_bulk(
                    ExtractionQuery.filter_figure_violence_sub_types.through, extraction_queries, 'extractionquery',
                    violencesubtype=violence_sub_type,
                )

        migrate_data(Event, Figure, Violence, ViolenceSubType, Report, ExtractionQuery)

        def _counts_by_violence(multiplier):
            return {
                'event': 10 * multiplier,
                'figure': 20 * multiplier,
                'report': 5,
                'extractionquery': 6,
            }

        def _counts_by_sub_violence(multiplier):
            return {
                'event': 50 * multiplier,
                'figure': 60 * multiplier,
                'report': 5,
                'extractionquery': 6,
            }

        VIOLENCE_TYPES_WITH_EXPECTED_COUNTS = {
            "International armed conflict(IAC)": _counts_by_violence(1),
            "Non-International armed conflict (NIAC)": _counts_by_violence(1),
            "Other situations of violence (OSV)": _counts_by_violence(1),
            "Unclear/Unknown": _counts_by_violence(2),
        }

        VIOLENCE_SUB_TYPES_WITH_EXPECTED_COUNTS = {
            "International armed conflict(IAC)": {
                "International armed conflict(IAC)": _counts_by_sub_violence(5),
            },
            "Non-International armed conflict (NIAC)": {
                "Non-International armed conflict (NIAC)": _counts_by_sub_violence(5),
            },
            "Other situations of violence (OSV)": {
                "Civilian-state violence": _counts_by_sub_violence(1),
                "Crime-related": _counts_by_sub_violence(1),
                "Communal violence": _counts_by_sub_violence(1),
                "Other": _counts_by_sub_violence(3),
            },
            "Unclear/Unknown": {
                "Unclear/Unknown": _counts_by_sub_violence(5),
            },
        }

        violence_types_with_counts = {}
        violence_sub_types_with_counts = defaultdict(dict)

        for name, violence_sub_types_data in VIOLENCE_SUB_TYPES_WITH_EXPECTED_COUNTS.items():
            violence_type = Violence.objects.get(name=name)
            violence_types_with_counts[violence_type.name] = _get_table_counts_by_violence(violence_type.pk)

            for sub_name in violence_sub_types_data.keys():
                violence_sub_type = ViolenceSubType.objects.get(name=sub_name)
                violence_sub_types_with_counts[violence_type.name][violence_sub_type.name] = (
                    _get_table_counts_by_sub_violence(violence_sub_type.pk)
                )

        assert VIOLENCE_TYPES_WITH_EXPECTED_COUNTS == violence_types_with_counts
        assert VIOLENCE_SUB_TYPES_WITH_EXPECTED_COUNTS == dict(violence_sub_types_with_counts)
