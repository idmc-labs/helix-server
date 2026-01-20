import logging

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


def double_data(Model, queryset, mutate=None):
    logger.info(f"Copying {Model.__name__} data")

    new_entities_with_old_entity_id = []

    for old_entity in queryset:
        old_entity_id = old_entity.pk
        new_entity = Model(
            **{field.name: getattr(old_entity, field.name) for field in old_entity._meta.fields if field.name != "id"}
        )
        if mutate:
            mutate(new_entity, old_entity)
        new_entities_with_old_entity_id.append((old_entity_id, new_entity))

    new_entities = [item[1] for item in new_entities_with_old_entity_id]
    created_entities_count = 0

    created_objects = []
    for i in range(0, len(new_entities), 1000):
        batch = new_entities[i : i + 1000]
        objects = Model.objects.bulk_create(batch)
        created_entities_count += len(objects)
        created_objects.extend(objects)

    # # FIXME: Do we need to read from created_entities instead?
    mapping = {}
    for (old_id, _), created in zip(new_entities_with_old_entity_id, created_objects):
        mapping[old_id] = created.id

    logger.info(f"Created {created_entities_count} {Model.__name__} items")

    return mapping


def double_crisis():
    def mutate_new_crisis(new_crisis, old_crisis=None):
        if new_crisis.start_date and new_crisis.end_date:
            new_crisis.start_date -= relativedelta(years=8)
            new_crisis.end_date -= relativedelta(years=8)

    crisis_queryset = Crisis.objects.iterator(chunk_size=1000)
    old_to_new_crisis_map = double_data(Crisis, crisis_queryset, mutate_new_crisis)

    return old_to_new_crisis_map


def double_event(old_to_new_crisis_map):
    def mutate_new_event(new_event, old_event=None):
        new_event.start_date -= relativedelta(years=8)
        new_event.end_date -= relativedelta(years=8)
        # NOTE: Attach new crisis to new event
        new_event_crisis_id = old_to_new_crisis_map.get(new_event.crisis_id)
        new_event.crisis = Crisis.objects.filter(id=new_event_crisis_id).first()

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
        new_entry.associated_parked_item = None
        if old_entry.preview:
            new_entry_preview_id = old_to_new_preview_map.get(old_entry.preview.id)
            new_entry.preview = SourcePreview.objects.filter(id=new_entry_preview_id).first()
        else:
            new_entry.preview = None
        if old_entry.document:
            new_entry_document_id = old_to_new_attachment_map.get(old_entry.document.id)
            new_entry.document = Attachment.objects.filter(id=new_entry_document_id).first()
        else:
            new_entry.document = None

    entry_queryset = Entry.objects.filter(figures__isnull=False).distinct().order_by("id").iterator(chunk_size=1000)
    old_to_new_entry_map = double_data(Entry, entry_queryset, mutate_entry)

    return old_to_new_entry_map


def double_figure_location():
    figure_location_queryset = FigureLocation.objects.iterator(chunk_size=1000)
    old_to_new_location_map = double_data(FigureLocation, figure_location_queryset)

    return old_to_new_location_map


def double_report():
    def mutate_new_report(new_report, old_report=None):
        if new_report.filter_figure_start_after and new_report.filter_figure_end_before:
            new_report.filter_figure_start_after -= relativedelta(years=8)
            new_report.filter_figure_end_before -= relativedelta(years=8)

        if new_report.gidd_report_year:
            if new_report.gidd_report_year >= 2024:
                new_report.gidd_report_year = None
            else:
                new_report.gidd_report_year -= 8

        if new_report.gidd_published_date:
            new_report.gidd_published_date -= relativedelta(years=8)

    report_queryset = Report.objects.iterator(chunk_size=1000)
    double_data(Report, report_queryset, mutate_new_report)


def double_figure_data(old_to_new_entry_map, old_to_new_location_map, old_to_new_event_map):
    def chunked_queryset(qs, chunk_size):
        last_id = 0
        while True:
            chunk = list(qs.filter(id__gt=last_id).order_by("id")[:chunk_size])
            if not chunk:
                break
            yield chunk
            last_id = chunk[-1].id

    # Double Figure data
    logger.info("Copying Figure data")
    figure_location_map = []  # [(new_figure_obj, new_locations),]
    figure_qs = Figure.objects.all()
    new_figure_count = 0
    for figure_chunk in chunked_queryset(figure_qs, 1000):
        new_figure_objects = []
        for figure in figure_chunk:
            old_entry_id = figure.entry.id

            new_figure_obj = Figure(
                **{field.name: getattr(figure, field.name) for field in figure._meta.fields if field.name != "id"}
            )
            new_entry_id = old_to_new_entry_map.get(old_entry_id)
            new_figure_obj.entry = Entry.objects.filter(id=new_entry_id).first()
            if not new_figure_obj.entry:
                continue

            old_figure_event_id = figure.event.id
            new_event_id = old_to_new_event_map.get(old_figure_event_id)
            new_figure_obj.event = Event.objects.filter(id=new_event_id).first()
            if not new_figure_obj.event:
                continue

            new_figure_obj.start_date -= relativedelta(years=8)
            new_figure_obj.end_date -= relativedelta(years=8)
            new_figure_objects.append(new_figure_obj)

            # map new figure and new locations
            old_locations = figure.geo_locations.all()
            new_locations_uuids = [old_to_new_location_map.get(old_loc.id) for old_loc in old_locations]
            figure_location_map.append((new_figure_obj, new_locations_uuids))

        objects = Figure.objects.bulk_create(new_figure_objects, batch_size=1000)
        new_figure_count += len(objects)

    # set new locations to new figures
    for new_figure, locations_uuids in figure_location_map:
        locations = FigureLocation.objects.filter(uuid__in=locations_uuids)
        new_figure.geo_locations.set(locations)

    logger.info(f"Created {new_figure_count} Figure items")


class Command(BaseCommand):
    help = "Generate IDUS dump files"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.ENABLE_DANGER_MODE:
            logger.warning("ENABLE_DANGER_MODE needs to be enabled to use this command")
            return

        # Crisis
        old_to_new_crisis_map = double_crisis()

        # Event
        old_to_new_event_map = double_event(old_to_new_crisis_map)
        del old_to_new_crisis_map

        # Source preview
        old_to_new_preview_map = double_source_preview()

        # Document
        old_to_new_attachment_map = double_attachment()

        # Entry
        old_to_new_entry_map = double_entry(old_to_new_preview_map, old_to_new_attachment_map)

        del old_to_new_preview_map
        del old_to_new_attachment_map

        # FiugreLocation
        old_to_new_location_map = double_figure_location()

        # Figure
        double_figure_data(old_to_new_entry_map, old_to_new_location_map, old_to_new_event_map)
        del old_to_new_entry_map
        del old_to_new_location_map
        del old_to_new_event_map

        # Report
        double_report()

        logger.info("Generating double data SUCCESS")
