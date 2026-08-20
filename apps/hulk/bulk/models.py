from __future__ import annotations

import abc
import typing
import uuid

import typing_extensions
from django.db import models
from pydantic import Field, model_validator
from pyhelix import models as pyhelix_models
from pyhelix.constants import MAX_EVENT_CODES
from pyhelix.enums import HulkEntryImportTypeEnum
from pyhelix.parsers import validate_and_parse_enum

from apps.contrib.models import Attachment, SourcePreview
from apps.country.models import Country
from apps.crisis.models import Crisis
from apps.entry.models import Entry, FigureTag
from apps.event.models import (
    ContextOfViolence,
    DisasterSubType,
    Event,
    OsvSubType,
    OtherSubType,
    ViolenceSubType,
)
from apps.hulk.models import HulkAttachment, HulkEntityRelationBase, HulkEntry, HulkEvent, HulkSourcePreview

from .parsers import (
    get_date_for_graphql,
    get_name_attributed_model,
    validate_ids_exist,
)


# TODO: Cache this
def get_hulk_entity_id(
    helix_model: typing.Type[models.Model],
    hulk_model: typing.Type[HulkEntityRelationBase],
    _id: int | None,
    _uuid: uuid.UUID | None,
) -> int | None:
    if _id and (helix_entity := helix_model.objects.filter(pk=_id).first()):
        return helix_entity.pk
    if _uuid and (hulk_entry := hulk_model.objects.filter(uuid=_uuid).first()):
        return hulk_entry.entity_id
    return None


# TODO: Cache this
def get_event(_id: int | None, _uuid: uuid.UUID | None) -> Event | None:
    if _id and (event := Event.objects.filter(pk=_id).first()):
        return event
    if _uuid and (hulk_event := HulkEvent.objects.select_related("entity").filter(uuid=_uuid).first()):
        return hulk_event.entity
    return None


class HulkBaseModel(pyhelix_models.BaseModel):
    @abc.abstractmethod
    def generate_for_graphql_mutation(self):
        raise NotImplementedError("generate_for_graphql_mutation is missing")


class HulkAttachmentImport(HulkBaseModel, pyhelix_models.HulkAttachmentImport):
    def generate_for_graphql_mutation(self):
        return {
            # XXX: File import logic is in the HulkHelixAttachmentImportHandler
            "attachmentFor": self.attachment_for.value,
        }


class HulkSourcePreviewImport(HulkBaseModel, pyhelix_models.HulkSourcePreviewImport):
    def generate_for_graphql_mutation(self):
        return {
            # TODO: Is file_url it a local path?
            "url": self.file_url,
            # Skip the recent in-progress preview reuse: each hulk row must map to its
            # own SourcePreview entity (HulkSourcePreview.entity is OneToOne). Reusing
            # would make two uuids point at one entity and violate the unique on entity_id.
            "skipRecentReuse": True,
            # TODO: Other fields?
            # - versionId
            # - token
            # - pdf
            # - status
            # - remark
        }


# TODO: Support partial data input for optional fields
class HulkEntryImport(HulkBaseModel, pyhelix_models.HulkEntryImport):
    _attachment_id: typing.Optional[int] = None
    _source_preview_id: typing.Optional[int] = None

    @model_validator(mode="after")
    def parse_document(self):
        if self.hulk_import_type != HulkEntryImportTypeEnum.DOCUMENT:
            return self

        if self.attachment_uuid is None:
            raise ValueError("attachment_uuid is required")
        attachment_id = get_hulk_entity_id(Attachment, HulkAttachment, None, self.attachment_uuid)
        if attachment_id is None:
            raise ValueError(f"Unknown attachment: {self.attachment_uuid=}")
        self._attachment_id = attachment_id
        return self

    @model_validator(mode="after")
    def parse_url(self):
        if self.hulk_import_type != HulkEntryImportTypeEnum.URL:
            return self

        if self.source_preview_uuid is None or self.url is None:
            raise ValueError("Both source_preview_uuid and url are required")
        source_preview_id = get_hulk_entity_id(SourcePreview, HulkSourcePreview, None, self.source_preview_uuid)
        if source_preview_id is None:
            raise ValueError(f"Unknown source_preview: {self.source_preview_uuid=}")
        self._source_preview_id = source_preview_id
        return self

    def generate_for_graphql_mutation(self):
        return {
            # -- Attachment
            "document": self._attachment_id and str(self._attachment_id),
            "documentUrl": self.document_url,
            # -- URL
            "url": self.url,
            "preview": self._source_preview_id and str(self._source_preview_id),
            # Other fields
            "articleTitle": self.entry_title,
            "publishDate": get_date_for_graphql(self.publish_date),
            "isConfidential": self.is_confidential,
            "publishers": self.publishers_id or [],
            # TODO: Other fields?
        }


class HulkEventImportEventCode(HulkBaseModel, pyhelix_models.HulkEventImportEventCode):
    def generate_for_graphql_mutation(self):
        return {
            "uuid": str(self.uuid),
            "country": self.country_id,
            "eventCode": self.event_code,
            "eventCodeType": self.event_code_type.name,
            # TODO: Other fields?
        }


# TODO: Support partial data input for optional fields
class HulkEventImport(HulkBaseModel, pyhelix_models.HulkEventImport):
    event_codes: typing_extensions.Annotated[  # type: ignore[reportIncompatibleVariableOverride]
        typing.List[HulkEventImportEventCode],
        Field(max_length=MAX_EVENT_CODES),
    ]

    @model_validator(mode="after")
    @typing_extensions.override
    def validate_related_ids(self):
        validate_ids_exist(Country, self.countries_id, "countries_id")
        validate_ids_exist(
            Country,
            [event_code.country_id for event_code in self.event_codes],
            "event_codes[].country_id",
        )
        return self

    @model_validator(mode="before")
    @classmethod
    @typing_extensions.override
    def parse_event_cause(cls, data: dict):
        raw_event_type = data.get("event_cause") or ""
        event_type = validate_and_parse_enum(Crisis.CRISIS_TYPE, raw_event_type, is_required=True, field_name="event_cause")
        data["event_type"] = event_type.name

        if event_type == Crisis.CRISIS_TYPE.CONFLICT:
            # TODO: Instead of get_name_attributed_model, use helix_client with custom function for _managers?
            data["violence_sub_type_id"] = get_name_attributed_model(ViolenceSubType, data.get("violence_sub_type_id")).pk
        elif event_type == Crisis.CRISIS_TYPE.DISASTER:
            data["disaster_sub_type_id"] = get_name_attributed_model(DisasterSubType, data.get("disaster_sub_type_id")).pk
        elif event_type == Crisis.CRISIS_TYPE.OTHER:
            data["other_sub_type_id"] = get_name_attributed_model(OtherSubType, data.get("other_sub_type_id")).pk
        else:
            typing_extensions.assert_never(event_type)

        return data

    def generate_for_graphql_mutation(self):
        return {
            "name": self.event_name,
            "eventType": self.event_cause.name,
            "violenceSubType": self.violence_sub_type_id,
            "disasterSubType": self.disaster_sub_type_id,
            "otherSubType": self.other_sub_type_id,
            "countries": self.countries_id or [],
            "startDate": get_date_for_graphql(self.start_date),
            "startDateAccuracy": self.start_date_accuracy.name,
            "endDate": get_date_for_graphql(self.end_date),
            "endDateAccuracy": self.end_date_accuracy.name,
            "eventNarrative": self.event_narrative,
            "eventCodes": [ec.generate_for_graphql_mutation() for ec in self.event_codes],
            # TODO: Other fields?
        }


class HulkFigureImportLocation(HulkBaseModel, pyhelix_models.HulkFigureImportLocation):
    def generate_for_graphql_mutation(self):
        return {
            "uuid": str(self.uuid),
            "boundingBox": self.bounding_box,
            "displayName": self.display_name,
            "country": self.country_name,
            "countryCode": self.country_code,
            "identifier": self.identifier.name,
            "accuracy": self.accuracy.name,
            "geocoder": self.geocoder.name,
            "lat": self.latitude,
            "lon": self.longitude,
            "pcode": self.pcode,
            "pcodeSource": self.pcode_source,
            "pcodeAccuracy": self.pcode_accuracy.name if self.pcode_accuracy else None,
        }


class HulkFigureImport(HulkBaseModel, pyhelix_models.HulkFigureImport):
    locations: typing_extensions.Annotated[  # type: ignore[reportIncompatibleVariableOverride]
        typing.List[HulkFigureImportLocation],
        Field(min_length=1),
    ]

    _entry_id: int
    _event_id: int

    @model_validator(mode="before")
    @classmethod
    @typing_extensions.override
    def parse_figure_cause(cls, data):
        if not isinstance(data, dict):
            return data
        raw_figure_cause = data.get("figure_cause") or ""
        figure_cause = validate_and_parse_enum(
            Crisis.CRISIS_TYPE, raw_figure_cause, is_required=True, field_name="figure_cause"
        )

        if figure_cause == Crisis.CRISIS_TYPE.CONFLICT:
            get_name_attributed_model(ViolenceSubType, data.get("violence_sub_type_id"))
        elif figure_cause == Crisis.CRISIS_TYPE.DISASTER:
            get_name_attributed_model(DisasterSubType, data.get("disaster_sub_type_id"))
        elif figure_cause == Crisis.CRISIS_TYPE.OTHER:
            get_name_attributed_model(OtherSubType, data.get("other_sub_type_id"))
        else:
            typing_extensions.assert_never(figure_cause)

        return data

    @model_validator(mode="after")
    @typing_extensions.override
    def validate_related_ids(self):
        """Existence checks for the FKs the cause branch does not cover."""
        validate_ids_exist(Country, [self.country_id], "country_id")
        validate_ids_exist(FigureTag, self.tags_id, "tags_id")
        validate_ids_exist(OsvSubType, [self.osv_sub_type_id] if self.osv_sub_type_id else [], "osv_sub_type_id")
        validate_ids_exist(ContextOfViolence, self.context_of_violences_id, "context_of_violences_id")
        return self

    @model_validator(mode="after")
    @typing_extensions.override
    def parse_entry(self):
        if self.entry_id is None and self.entry_uuid is None:
            raise ValueError("either entry_id or entry_uuid is required")
        entry_id = get_hulk_entity_id(Entry, HulkEntry, self.entry_id, self.entry_uuid)
        if entry_id is None:
            raise ValueError(f"Unknown entry: {self.entry_id=} {self.entry_uuid=}")
        self._entry_id = entry_id
        return self

    @model_validator(mode="after")
    @typing_extensions.override
    def parse_event(self):
        if self.event_id is None and self.event_uuid is None:
            raise ValueError("either event_id or event_uuid is required")
        event = get_event(self.event_id, self.event_uuid)
        if event is None:
            raise ValueError(f"Unknown event: {self.event_id=} {self.event_uuid=}")
        self._event_id = event.pk

        event_type = typing.cast("Crisis.CRISIS_TYPE", event.event_type)

        # The event's cause selects which sub_type field is required below, so a figure
        # whose own cause differs from its event's would fail on a sub_type it never
        # claimed to carry. helix rejects the mismatch as well
        # (FigureSerializer._validate_figure_cause).
        if event_type.value != self.figure_cause.value:
            raise ValueError(
                f"figure_cause {self.figure_cause.name} does not match the cause {event_type.name} of its event"
                f" (event_id={event.pk}, event_uuid={self.event_uuid})"
            )

        if event_type == Crisis.CRISIS_TYPE.CONFLICT:
            # TODO: Instead of get_name_attributed_model, use helix_client with custom function for _managers?
            self.violence_sub_type_id = get_name_attributed_model(ViolenceSubType, self.violence_sub_type_id).pk
        elif event_type == Crisis.CRISIS_TYPE.DISASTER:
            self.disaster_sub_type_id = get_name_attributed_model(DisasterSubType, self.disaster_sub_type_id).pk
        elif event_type == Crisis.CRISIS_TYPE.OTHER:
            self.other_sub_type_id = get_name_attributed_model(OtherSubType, self.other_sub_type_id).pk
        else:
            typing_extensions.assert_never(event_type)

        return self

    def generate_for_graphql_mutation(self):
        return {
            "uuid": str(self.uuid),
            "event": self._event_id,
            "entry": self._entry_id,
            "figureCause": self.figure_cause.name,
            "category": self.category.name,
            # Conflict
            "violenceSubType": self.violence_sub_type_id,
            "contextOfViolence": self.context_of_violences_id or [],
            "osvSubType": self.osv_sub_type_id,
            # Disaster
            "disasterSubType": self.disaster_sub_type_id,
            # Other
            "otherSubType": self.other_sub_type_id,
            "reported": self.reported_figure,
            "country": self.country_id,
            "startDate": get_date_for_graphql(self._start_date),
            "startDateAccuracy": self._start_date_accuracy.name if self._start_date_accuracy is not None else None,
            "endDate": get_date_for_graphql(self._end_date),
            "endDateAccuracy": self._end_date_accuracy.name if self._end_date_accuracy is not None else None,
            "term": self.term.name,
            "isHousingDestruction": self.is_housing_destruction,
            "quantifier": self.quantifier.name,
            "unit": self.unit.name,
            "householdSize": self.household_size,
            "role": self.figure_role.name,
            "displacementOccurred": self.displacement_occurred.name,
            "tags": self.tags_id or [],
            "sources": self.sources_id or [],
            "isDisaggregated": self.is_disaggregated,
            "calculationLogic": self.analysis_text,
            "sourceExcerpt": self.source_excerpt_text,
            "includeIdu": self.include_idu,
            "excerptIdu": self.idu_text,
            "geoLocations": [loc.generate_for_graphql_mutation() for loc in self.locations],
            # TODO: Other fields?
        }
