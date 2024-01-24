import typing
from django.db import migrations, connection
from django.conf import settings


def migrate_data(Event, Figure, Violence, ViolenceSubType, Report, ExtractionQuery):

    def _fetch_table_count_by_violence_type(_id: int):
        return {
            'violencesubtype': ViolenceSubType.objects.filter(violence=_id).count(),
            'event': Event.objects.filter(violence=_id).count(),
            'figure': Figure.objects.filter(violence=_id).count(),
            'report': Report.filter_figure_violence_types.through.objects.filter(violence=_id).count(),
            'extractionquery': ExtractionQuery.filter_figure_violence_types.through.objects.filter(violence=_id).count()
        }

    def _fetch_table_count_by_violence_sub_type(_id: int):
        return {
            'event': Event.objects.filter(violence_sub_type=_id).count(),
            'figure': Figure.objects.filter(violence_sub_type=_id).count(),
            'report': Report.filter_figure_violence_sub_types.through.objects.filter(violencesubtype=_id).count(),
            'extractionquery': ExtractionQuery.filter_figure_violence_sub_types.through.objects.filter(violencesubtype=_id).count()
        }

    def _migrate_filter_data(
        report_through_model,
        extraction_through_model,
        field,
        new_id,
        to_be_moved_ids,
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                f'''
                    INSERT into {report_through_model._meta.db_table} (
                        report_id,
                        {field}_id
                    )
                    SELECT
                        report_id,
                        %(new_id)s
                    FROM {report_through_model._meta.db_table}
                    WHERE
                        {field}_id = ANY(%(to_be_moved_ids)s)
                    ON CONFLICT DO NOTHING;
                ''',
                dict(
                    new_id=new_id,
                    to_be_moved_ids=to_be_moved_ids,
                ),
            )

        with connection.cursor() as cursor:
            cursor.execute(
                f'''
                    INSERT into {extraction_through_model._meta.db_table} (
                        extractionquery_id,
                        {field}_id
                    )
                    SELECT
                        extractionquery_id,
                        %(new_id)s
                    FROM {extraction_through_model._meta.db_table}
                    WHERE
                        {field}_id = ANY(%(to_be_moved_ids)s)
                    ON CONFLICT DO NOTHING;
                ''',
                dict(
                    new_id=new_id,
                    to_be_moved_ids=to_be_moved_ids,
                ),
            )

    def _move_violence_types(
        violence_names: typing.List[str],
        destination_violence_name: typing.Tuple[str],
        new_violence_name: typing.Tuple[str],
    ):
        to_be_moved_violence_types: typing.List[Violence] = []
        for violence_name in violence_names:
            to_be_moved_violence_type = (
                Violence.objects.get(
                    name__iexact=violence_name,
                )
            )
            assert to_be_moved_violence_type.name == violence_name
            to_be_moved_violence_types.append(to_be_moved_violence_type)

        assert len(to_be_moved_violence_types) == len(violence_names)
        to_be_moved_violence_types_ids = [i.pk for i in to_be_moved_violence_types]

        destination_violence = (
            Violence.objects.get(
                name__iexact=destination_violence_name,
            )
        )
        assert destination_violence.name == destination_violence_name

        # Fetch count by to_be_moved_violence_types
        to_be_moved_violence_types_ref_counts = {}
        for violence in to_be_moved_violence_types:
            to_be_moved_violence_types_ref_counts[violence.pk] = _fetch_table_count_by_violence_type(violence.pk)
        destination_ref_counts = _fetch_table_count_by_violence_type(destination_violence.pk)

        # Move the ref
        print(
            '-- Updating violence_type:',
            Event.objects.filter(violence__in=to_be_moved_violence_types).update(violence=destination_violence.pk),
            Figure.objects.filter(violence__in=to_be_moved_violence_types).update(violence=destination_violence.pk),
        )

        # M2M Relations
        _migrate_filter_data(
            Report.filter_figure_violence_types.through,
            ExtractionQuery.filter_figure_violence_types.through,
            'violence',
            destination_violence.pk,
            to_be_moved_violence_types_ids,
        )

        # Check if everything is moved
        moved_ref_counts = _fetch_table_count_by_violence_type(destination_violence.pk)
        for related_table_key, count in moved_ref_counts.items():
            if related_table_key in ['report', 'extractionquery']:
                continue

            assert count == destination_ref_counts[related_table_key] + sum([
                value
                for _, values in to_be_moved_violence_types_ref_counts.items()
                for _related_tab_key, value in values.items()
                if related_table_key == _related_tab_key
            ])

        # Update entity name
        destination_violence.name = new_violence_name
        destination_violence.save(update_fields=('name',))

        current_violence_type_count = Violence.objects.count()
        print('-- Deleting', Violence.objects.filter(id__in=[i.id for i in to_be_moved_violence_types]).all().delete())
        assert Violence.objects.count() == current_violence_type_count - len(to_be_moved_violence_types)

    def _move_sub_violence_types(
        sub_violence_names: typing.List[typing.Tuple[str, str]],
        destination_sub_violence_name: typing.Tuple[str, str],
        new_sub_violence_name: typing.Tuple[str, str],
    ):
        to_be_moved_sub_violence_types: typing.List[ViolenceSubType] = []
        for violence_name, sub_violence_name in sub_violence_names:
            to_be_moved_sub_violence_type = (
                ViolenceSubType.objects.get(
                    violence__name__iexact=violence_name,
                    name__iexact=sub_violence_name,
                )
            )
            assert to_be_moved_sub_violence_type.violence.name == violence_name
            assert to_be_moved_sub_violence_type.name == sub_violence_name
            to_be_moved_sub_violence_types.append(to_be_moved_sub_violence_type)

        assert len(to_be_moved_sub_violence_types) == len(sub_violence_names)
        to_be_moved_sub_violence_types_ids = [i.pk for i in to_be_moved_sub_violence_types]

        destination_sub_violence = (
            ViolenceSubType.objects.get(
                violence__name__iexact=destination_sub_violence_name[0],
                name__iexact=destination_sub_violence_name[1],
            )
        )
        assert destination_sub_violence.violence.name == destination_sub_violence_name[0]
        assert destination_sub_violence.name == destination_sub_violence_name[1]

        # Fetch count by to_be_moved_sub_violence_types
        to_be_moved_sub_violence_types_ref_counts = {}
        for sub_violence in to_be_moved_sub_violence_types:
            to_be_moved_sub_violence_types_ref_counts[sub_violence.pk] = _fetch_table_count_by_violence_sub_type(sub_violence.pk)
        destination_ref_counts = _fetch_table_count_by_violence_sub_type(destination_sub_violence.pk)

        # Move the ref
        print(
            '-- Updating violence_sub_type',
            [(i.name, i.violence.name) for i in to_be_moved_sub_violence_types],
            (
                Event.objects
                .filter(violence_sub_type__in=to_be_moved_sub_violence_types)
                .update(violence_sub_type=destination_sub_violence.pk)
            ),
            (
                Figure.objects
                .filter(violence_sub_type__in=to_be_moved_sub_violence_types)
                .update(violence_sub_type=destination_sub_violence.pk)
            ),
        )

        # M2M Relations
        _migrate_filter_data(
            Report.filter_figure_violence_sub_types.through,
            ExtractionQuery.filter_figure_violence_sub_types.through,
            'violencesubtype',
            destination_sub_violence.pk,
            to_be_moved_sub_violence_types_ids,
        )

        # Check if everything is moved
        moved_ref_counts = _fetch_table_count_by_violence_sub_type(destination_sub_violence.pk)
        for related_table_key, count in moved_ref_counts.items():
            if related_table_key in ['report', 'extractionquery']:
                continue

            assert count == destination_ref_counts[related_table_key] + sum([
                value
                for _, values in to_be_moved_sub_violence_types_ref_counts.items()
                for _related_tab_key, value in values.items()
                if related_table_key == _related_tab_key
            ])

        # Update entity name
        destination_sub_violence.name = new_sub_violence_name[1]
        destination_sub_violence.save(update_fields=('name',))

        current_violence_sub_type_count = ViolenceSubType.objects.count()
        print('-- Deleting', ViolenceSubType.objects.filter(id__in=[i.id for i in to_be_moved_sub_violence_types]).all().delete())
        assert ViolenceSubType.objects.count() == current_violence_sub_type_count - len(to_be_moved_sub_violence_types)

    for sub_violence_names, destination_sub_violence_name, new_sub_violence_name in [
            [
                [
                    ['International armed conflict(IAC)', 'Military Occupation'],
                    ['International armed conflict(IAC)', 'Other (IAC)'],
                    ['International armed conflict(IAC)', 'Unclear (IAC)'],
                    ['International armed conflict(IAC)', 'Unknown (IAC)'],
                ],
                ['International armed conflict(IAC)', 'IAC (other than occupation)'],
                ['International armed conflict(IAC)', 'International armed conflict(IAC)'],
            ], [
                [
                    ['Non-International armed conflict (NIAC)', 'NSAG(s) vs. State actor(s)'],
                    ['Non-International armed conflict (NIAC)', 'Other (NIAC)'],
                    ['Non-International armed conflict (NIAC)', 'Unclear (NIAC)'],
                    ['Non-International armed conflict (NIAC)', 'Unknown (NIAC)'],
                ],
                ['Non-International armed conflict (NIAC)', 'NSAG(s) vs. NSAG(s)'],
                ['Non-International armed conflict (NIAC)', 'Non-International armed conflict (NIAC)'],
            ], [
                [
                    ['Other situations of violence (OSV)', 'Unclear (OSV)'],
                    ['Other situations of violence (OSV)', 'Unknown (OSV)'],
                ],
                ['Other situations of violence (OSV)', 'Other (OSV)'],
                ['Other situations of violence (OSV)', 'Other'],
            ], [
                [
                    ['Other', 'Unclear (Other)'],
                    ['Other', 'Unknown (Other)'],
                    ['Unknown', 'Unclear (Unknown)'],
                    ['Unknown', 'Unknown (Unknown)'],
                ],
                ['Other', 'Other (Other)'],
                ['Other', 'Unclear/Unknown']
            ],
    ]:
        _move_sub_violence_types(sub_violence_names, destination_sub_violence_name, new_sub_violence_name)

    for violence_names, destination_violence_name, new_violence_name in [
            [
                ['Unknown'],
                'Other',
                'Unclear/Unknown',
            ],
    ]:
        _move_violence_types(violence_names, destination_violence_name, new_violence_name)


def migrate_violence_and_sub_types(apps, _):
    Event = apps.get_model('event', 'Event')
    Figure = apps.get_model('entry', 'Figure')
    Violence = apps.get_model('event', 'Violence')
    ViolenceSubType = apps.get_model('event', 'ViolenceSubType')
    Report = apps.get_model('report', 'Report')
    ExtractionQuery = apps.get_model('extraction', 'ExtractionQuery')

    if settings.TESTING:
        return
    migrate_data(Event, Figure, Violence, ViolenceSubType, Report, ExtractionQuery)


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0034_alter_eventcode_uuid'),
    ]

    operations = [
        migrations.RunPython(migrate_violence_and_sub_types, reverse_code=migrations.RunPython.noop),
    ]
