import logging
import typing

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contrib.models import Attachment, SourcePreview
from apps.crisis.models import Crisis
from apps.entry.models import Entry, Figure, FigureLocation
from apps.event.models import Event
from apps.report.models import Report

logger = logging.getLogger(__name__)


YEAR_DIFF = 9


def double_data(Model, queryset, mutate=None, post_mutate=None):
    logger.info(f"Copying {Model.__name__} data")

    old_entities_with_new_entities: typing.List[typing.Tuple[typing.Any, typing.Any]] = []

    for old_entity in queryset:
        new_entity = Model(
            **{field.name: getattr(old_entity, field.name) for field in old_entity._meta.fields if field.name != "id"}
        )
        if mutate:
            mutate(new_entity, old_entity)

        old_entities_with_new_entities.append((old_entity, new_entity))

    new_entities = [item[1] for item in old_entities_with_new_entities]

    created_entities: typing.List[typing.Any] = Model.objects.bulk_create(
        new_entities,
        batch_size=1000,
    )

    assert len(new_entities) == len(created_entities), f"All {Model.__name__} items must be created."

    # NOTE: We can use bulk update here.
    if post_mutate:
        logger.info(f"Adding relationship for {Model.__name__}")
        for (old_entity, _), created_entity in zip(old_entities_with_new_entities, created_entities):
            post_mutate(created_entity, old_entity)

    mapping: typing.Dict[int, int] = {}
    for (old_entity, _), created_entity in zip(old_entities_with_new_entities, created_entities):
        mapping[old_entity.pk] = created_entity.pk

    logger.info(f"Created {len(created_entities)} {Model.__name__} items")
    return mapping


def double_crisis():
    def mutate_new_crisis(new_crisis, old_crisis):
        if new_crisis.start_date and new_crisis.end_date:
            new_crisis.start_date -= relativedelta(years=YEAR_DIFF)
            new_crisis.end_date -= relativedelta(years=YEAR_DIFF)

    crisis_qs = Crisis.objects.iterator(chunk_size=1000)
    old_to_new_crisis_map = double_data(Crisis, crisis_qs, mutate_new_crisis)

    return old_to_new_crisis_map


def double_event(old_to_new_crisis_map):
    def mutate_new_event(new_event, old_event):
        # FIXME: Currently, we are not duplicating event codes.
        new_event.start_date -= relativedelta(years=YEAR_DIFF)
        new_event.end_date -= relativedelta(years=YEAR_DIFF)
        # NOTE: Attach new crisis to new event
        new_event.crisis_id = old_to_new_crisis_map.get(new_event.crisis_id)

    event_queryset = Event.objects.iterator(chunk_size=1000)
    old_to_new_event_map = double_data(Event, event_queryset, mutate_new_event)

    return old_to_new_event_map


def double_source_preview():
    preview_queryset = SourcePreview.objects.filter(entry__isnull=False).iterator(chunk_size=1000)
    old_to_new_preview_map = double_data(SourcePreview, preview_queryset)

    return old_to_new_preview_map


def double_attachment():
    entry_attachments_ids = Entry.objects.filter(document__isnull=False).values_list("document__id", flat=True)
    attachment_queryset = Attachment.objects.filter(id__in=entry_attachments_ids).iterator(chunk_size=1000)
    old_to_new_attachment_map = double_data(Attachment, attachment_queryset)

    return old_to_new_attachment_map


def double_entry(old_to_new_preview_map, old_to_new_attachment_map):
    def mutate_entry(new_entry, old_entry):
        new_entry.associated_parked_item_id = None

        if old_entry.preview:
            new_entry.preview_id = old_to_new_preview_map.get(old_entry.preview.id)
        else:
            new_entry.preview_id = None

        if old_entry.document:
            new_entry.document_id = old_to_new_attachment_map.get(old_entry.document.id)
        else:
            new_entry.document_id = None

    entry_queryset = Entry.objects.iterator(chunk_size=1000)
    old_to_new_entry_map = double_data(Entry, entry_queryset, mutate_entry)

    return old_to_new_entry_map


def double_figure_location():
    figure_location_queryset = FigureLocation.objects.iterator(chunk_size=1000)
    old_to_new_location_map = double_data(FigureLocation, figure_location_queryset)

    return old_to_new_location_map


def double_figure(
    old_to_new_entry_map,
    old_to_new_location_map,
    old_to_new_event_map,
):
    def mutate_figure(new_figure_obj, old_figure):
        new_figure_obj.start_date -= relativedelta(years=YEAR_DIFF)
        new_figure_obj.end_date -= relativedelta(years=YEAR_DIFF)

        old_entry_id = new_figure_obj.entry_id
        new_figure_obj.entry_id = old_to_new_entry_map.get(old_entry_id)

        old_event_id = new_figure_obj.event_id
        new_figure_obj.event_id = old_to_new_event_map.get(old_event_id)

    def post_mutate_figure(new_figure, old_figure):
        old_location_ids = old_figure.geo_locations.values_list("id", flat=True)
        new_location_ids = [old_to_new_location_map.get(old_location_id) for old_location_id in old_location_ids]
        new_figure.geo_locations.set(new_location_ids)

    figure_qs = Figure.objects.iterator(chunk_size=1000)
    double_data(Figure, figure_qs, mutate_figure, post_mutate_figure)


def double_report():
    def mutate_new_report(new_report, old_report=None):
        if new_report.filter_figure_start_after and new_report.filter_figure_end_before:
            new_report.filter_figure_start_after -= relativedelta(years=YEAR_DIFF)
            new_report.filter_figure_end_before -= relativedelta(years=YEAR_DIFF)

        if new_report.gidd_report_year:
            new_report.gidd_report_year -= YEAR_DIFF

        if new_report.gidd_published_date:
            new_report.gidd_published_date -= relativedelta(years=YEAR_DIFF)

    report_queryset = Report.objects.iterator(chunk_size=1000)
    double_data(Report, report_queryset, mutate_new_report)


class Command(BaseCommand):
    help = "Clone the data in the system"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.ENABLE_DANGER_MODE:
            logger.warning("ENABLE_DANGER_MODE needs to be enabled to use this command")
            return

        # Source preview
        old_to_new_preview_map = double_source_preview()

        # Document
        old_to_new_attachment_map = double_attachment()

        # Entry
        old_to_new_entry_map = double_entry(old_to_new_preview_map, old_to_new_attachment_map)
        del old_to_new_preview_map
        del old_to_new_attachment_map

        # Crisis
        old_to_new_crisis_map = double_crisis()

        # Event
        old_to_new_event_map = double_event(old_to_new_crisis_map)
        del old_to_new_crisis_map

        # Figure Location
        old_to_new_location_map = double_figure_location()

        # Figure
        double_figure(old_to_new_entry_map, old_to_new_location_map, old_to_new_event_map)
        del old_to_new_entry_map
        del old_to_new_location_map
        del old_to_new_event_map

        # Report
        double_report()

        logger.info("Generated data!")
