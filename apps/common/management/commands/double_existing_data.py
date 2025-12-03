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


class Command(BaseCommand):
    help = "Generate IDUS dump files"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.ENABLE_DANGER_MODE:
            logger.warning("ENABLE_DANGER_MODE needs to be enabled to use this command")
            return
        logger.info("Generating double data")

        # Double crisis data
        logger.info("Generating Crisis data")
        new_crisis_objects = []
        old_to_new_crisis_map = {}
        for crisis in Crisis.objects.all():
            copy_of_old_crisis_id = crisis.pk
            new_crisis = Crisis(
                **{field.name: getattr(crisis, field.name) for field in crisis._meta.fields if field.name != "id"}
            )
            if crisis.start_date and crisis.end_date:
                new_crisis.start_date = crisis.start_date - relativedelta(years=8)
                new_crisis.end_date = crisis.end_date - relativedelta(years=8)
            new_crisis_objects.append((copy_of_old_crisis_id, new_crisis))

        crisis_instances_to_create = [item[1] for item in new_crisis_objects]
        Crisis.objects.bulk_create(crisis_instances_to_create)

        for copy_of_old_id, new_crisis in zip([item[0] for item in new_crisis_objects], crisis_instances_to_create):
            old_to_new_crisis_map[copy_of_old_id] = new_crisis

        # Double Event data and attach the new crisis with new events
        logger.info("Generating Event data")
        new_event_input_data = []
        for event in Event.objects.all():
            old_crisis_id = event.crisis_id
            new_crisis = old_to_new_crisis_map.get(old_crisis_id)
            new_event_obj = Event(
                **{field.name: getattr(event, field.name) for field in event._meta.fields if field.name != "id"}
            )
            new_event_obj.start_date = event.start_date - relativedelta(years=8)
            new_event_obj.end_date = event.end_date - relativedelta(years=8)
            new_event_obj.crisis = new_crisis
            new_event_input_data.append(new_event_obj)

        Event.objects.bulk_create(new_event_input_data)

        # Double Source preview data
        logger.info("Generating Source preview data")
        new_preview_objects = []
        old_to_new_preview_map = {}
        entry_previews = SourcePreview.objects.filter(entry__isnull=False)
        for preview in entry_previews:
            copy_of_old_preview_id = preview.pk
            new_preview = SourcePreview(
                **{field.name: getattr(preview, field.name) for field in preview._meta.fields if field.name != "id"}
            )
            new_preview_objects.append((copy_of_old_preview_id, new_preview))

        preview_instance_to_create = [item[1] for item in new_preview_objects]
        SourcePreview.objects.bulk_create(preview_instance_to_create)
        for copy_of_old_id, new_preview in zip([item[0] for item in new_preview_objects], preview_instance_to_create):
            old_to_new_preview_map[copy_of_old_id] = new_preview

        # Double Document data
        logger.info("Generating Attachment data")
        new_attachment_objects = []
        old_to_new_attachment_map = {}
        entry_attachments_ids = Entry.objects.filter(document__isnull=False).values_list("document__id", flat=True)
        for attachment in Attachment.objects.filter(id__in=entry_attachments_ids):
            copy_of_old_attachment_id = attachment.pk
            new_attachment = Attachment(
                **{field.name: getattr(attachment, field.name) for field in attachment._meta.fields if field.name != "id"}
            )
            new_attachment_objects.append((copy_of_old_attachment_id, new_attachment))

        attachment_instance_to_create = [item[1] for item in new_attachment_objects]
        Attachment.objects.bulk_create(attachment_instance_to_create)

        # map old attachment with new attachment
        for copy_of_old_id, new_attachment in zip(
            [item[0] for item in new_attachment_objects], attachment_instance_to_create
        ):
            old_to_new_attachment_map[copy_of_old_id] = new_attachment

        # Double Entry data attach the new entry with new parked items
        logger.info("Generating Entry data")
        new_entry_objects = []
        old_to_new_entry_map = {}
        for entry in Entry.objects.all():
            copy_of_old_entry_id = entry.pk
            new_entry = Entry(
                **{field.name: getattr(entry, field.name) for field in entry._meta.fields if field.name != "id"}
            )
            new_entry.associated_parked_item = None
            if entry.preview:
                new_entry.preview = old_to_new_preview_map.get(entry.preview.id)
            else:
                new_entry.preview = None
            if entry.document:
                new_entry.document = old_to_new_attachment_map.get(entry.document.id)
            else:
                new_entry.document = None
            new_entry_objects.append((copy_of_old_entry_id, new_entry))

        entry_instances_to_create = [item[1] for item in new_entry_objects]
        Entry.objects.bulk_create(entry_instances_to_create)

        # match old entry with new entry
        for copy_of_old_id, new_entry in zip([item[0] for item in new_entry_objects], entry_instances_to_create):
            old_to_new_entry_map[copy_of_old_id] = new_entry

        # Double Fiugre Location data
        logger.info("Generating Figure Location data")
        new_location_objects = []
        old_to_new_location_map = {}
        for location in FigureLocation.objects.all():
            copy_of_old_location_id = location.pk
            new_location = FigureLocation(
                **{field.name: getattr(location, field.name) for field in location._meta.fields if field.name != "id"}
            )
            new_attachment_objects.append((copy_of_old_location_id, new_location))

        location_instance_to_create = [item[1] for item in new_location_objects]
        FigureLocation.objects.bulk_create(location_instance_to_create)

        # match old location with new location
        for copy_of_old_id, new_location in zip([item[0] for item in new_location_objects], location_instance_to_create):
            old_to_new_location_map[copy_of_old_id] = new_location

        # Double Figure data
        logger.info("Generating Figure data")
        new_figure_objects = []
        figure_location_map = []  # [(new_figure_obj, new_locations),]
        for figure in Figure.objects.all():
            old_entry_id = figure.entry.id

            new_figure_obj = Figure(
                **{field.name: getattr(figure, field.name) for field in figure._meta.fields if field.name != "id"}
            )
            new_entry = old_to_new_entry_map.get(old_entry_id)
            new_figure_obj.entry = new_entry
            new_figure_obj.start_date = figure.start_date - relativedelta(years=8)
            new_figure_obj.end_date = figure.end_date - relativedelta(years=8)
            new_figure_objects.append(new_figure_obj)

            # map new figure and new locations
            old_locations = figure.geo_locations.all()
            new_location_ids = [old_to_new_location_map.get(old_loc.id) for old_loc in old_locations]
            new_locations = FigureLocation.objects.filter(id__in=new_location_ids)
            figure_location_map.append((new_figure_obj, new_locations))

        Figure.objects.bulk_create(new_figure_objects)
        # set new locations to new figures
        for new_figure, locations in figure_location_map:
            new_figure.geo_locations.set(locations)

        # Double Report Data
        logger.info("Generating Report data")
        new_reports = []
        for report in Report.objects.all():
            data = {field.name: getattr(report, field.name) for field in report._meta.fields if field.name != "id"}
            new_report = Report(**data)
            # generate report for year 2008 to 2016
            if report.gidd_report_year:
                if report.gidd_report_year >= 2024:
                    continue
                new_report.gidd_report_year = report.gidd_report_year - 8
            else:
                new_report.gidd_report_year = None
            new_reports.append(new_report)
        Report.objects.bulk_create(new_reports)

        logger.info("Generating double data SUCCESS")
