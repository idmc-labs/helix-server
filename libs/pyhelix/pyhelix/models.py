from __future__ import annotations

import datetime
import enum
import typing
import uuid

import typing_extensions
from pydantic import BaseModel as OgBaseModel
from pydantic import PrivateAttr, field_validator, model_validator
from pydantic.fields import Field

from pyhelix.api.api import get_active_helix_client

from .constants import (
    ATTACHMENT_FOR_CHOICES,
    CRISIS_TYPE,
    FIGURE_FLOW_LIST,
    FIGURE_STOCK_LIST,
    FIGURE_UNIT,
    MAX_FUTURE_YEARS,
)
from .enums import (
    HulkDataTypeEnum,
    HulkEntryImportTypeEnum,
)
from .parsers import enum_parser, validate_and_parse_enum
from .types import (
    DateAccuracy,
    EventCodeType,
    EventType,
    FigureCategoryType,
    FigureDisplacementOccurredType,
    FigureLocationAccuracyType,
    FigureLocationGeocoderType,
    FigureLocationIdentifierType,
    FigureQuantifierType,
    FigureRoleType,
    FigureTermType,
    FigureUnitType,
    ListOfIds,
)

AttachmentForChoicesType = typing_extensions.Annotated[ATTACHMENT_FOR_CHOICES, enum_parser(ATTACHMENT_FOR_CHOICES)]

# MAX_FUTURE_YEARS is generated into .constants from utils.validations (the
# Django-side single source of truth) by ./manage.py update_pyhelix_constants.


def _max_allowed_future_date() -> datetime.date:
    today = datetime.date.today()
    try:
        return today.replace(year=today.year + MAX_FUTURE_YEARS)
    except ValueError:
        # Feb 29 -> Feb 28 on a non-leap target year
        return today.replace(year=today.year + MAX_FUTURE_YEARS, day=28)


# TODO: Support partial data input for optional fields
class BaseModel(OgBaseModel):
    extra_context: typing.Optional[dict] = None
    """
    Optional: Just for adding extra context, this is not validated or used
    """

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            # NOTE: Using enum name instead of value for json dumps
            enum.Enum: lambda c: c.name
        }


class HulkBaseModel(BaseModel):
    uuid: uuid.UUID
    _hulk_data_type: HulkDataTypeEnum = PrivateAttr()
    """
    UUID used by Hulk and Helix for referencing created entities.
    Useful for backtracking and mapping Helix responses to Hulk data.
    """

    impersonate_as: typing.Optional[int] = None
    """
    Optional Helix User PK. When set, the row is created as if this user ran the
    import (per-row login is reused across the bulk run). Unset rows fall back
    to the user who triggered the bulk import.
    """


class HulkAttachmentImport(HulkBaseModel):
    _hulk_data_type = HulkDataTypeEnum.ATTACHMENT
    attachment_for: AttachmentForChoicesType = ATTACHMENT_FOR_CHOICES.ENTRY
    file_url: str
    """
    Only S3 url supported
    """


class HulkSourcePreviewImport(HulkBaseModel):
    _hulk_data_type = HulkDataTypeEnum.SOURCE_PREVIEW
    file_url: str


class HulkEntryImport(HulkBaseModel):
    _hulk_data_type = HulkDataTypeEnum.ENTRY
    hulk_import_type: HulkEntryImportTypeEnum

    # DOCUMENT
    attachment_uuid: typing.Optional[uuid.UUID] = None
    document_url: typing.Optional[str] = None
    # URL
    url: typing.Optional[str] = None
    source_preview_uuid: typing.Optional[uuid.UUID] = None
    # TODO: We also need a "URL" if the entry source/import type is URL

    entry_title: str
    publish_date: datetime.date
    is_confidential: bool

    publishers_id: typing_extensions.Annotated[ListOfIds, Field(min_length=1)]
    """
    FK: organization.Organization
    """

    @model_validator(mode="after")
    def _validate_publish_date(self):
        if self.publish_date and self.publish_date > _max_allowed_future_date():
            raise ValueError(f"publish_date: This date cannot be more than {MAX_FUTURE_YEARS} years in the future.")
        return self

    @model_validator(mode="after")
    def parse_import_data(self):
        if self.hulk_import_type == HulkEntryImportTypeEnum.DOCUMENT:
            if self.attachment_uuid is None:
                raise ValueError(f"attachment_uuid is required for {self.hulk_import_type=}")
        elif self.hulk_import_type == HulkEntryImportTypeEnum.URL:
            if self.source_preview_uuid is None:
                raise ValueError(f"source_preview_uuid is required for {self.hulk_import_type=}")
        return self


class HulkEventImportEventCode(BaseModel):
    uuid: uuid.UUID
    country_id: int  # FK
    event_code: str
    event_code_type: EventCodeType


class HulkEventImport(HulkBaseModel):
    _hulk_data_type = HulkDataTypeEnum.EVENT
    event_name: str

    event_cause: EventType
    violence_sub_type_id: typing.Optional[int] = None  # ViolenceSubType
    """For Conflict"""
    disaster_sub_type_id: typing.Optional[int] = None  # DisasterSubType
    """For Disaster"""
    other_sub_type_id: typing.Optional[int] = None  # OtherSubType
    """For Other"""

    start_date: datetime.date
    start_date_accuracy: DateAccuracy
    end_date: datetime.date
    end_date_accuracy: DateAccuracy

    event_narrative: str

    countries_id: typing_extensions.Annotated[ListOfIds, Field(min_length=1)]
    """
    FK: country.Country
    """

    event_codes: typing.List[HulkEventImportEventCode]

    @field_validator("event_narrative")
    @classmethod
    def _validate_event_narrative(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("event_narrative must not be blank")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def parse_event_cause(cls, data: dict):
        helix_client = get_active_helix_client()
        raw_event_type = data.get("event_cause") or ""
        event_type = validate_and_parse_enum(CRISIS_TYPE, raw_event_type, is_required=True)
        data["event_type"] = event_type.name

        if event_type == CRISIS_TYPE.CONFLICT:
            helix_client.violence_sub_type_manager.validate_id_exists(data.get("violence_sub_type_id"))
        elif event_type == CRISIS_TYPE.DISASTER:
            helix_client.disaster_sub_type_manager.validate_id_exists(data.get("disaster_sub_type_id"))
        elif event_type == CRISIS_TYPE.OTHER:
            helix_client.other_sub_type_manager.validate_id_exists(data.get("other_sub_type_id"))
        else:
            typing_extensions.assert_never(event_type)

        return data

    @model_validator(mode="after")
    def _validate_dates(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("The start date must be earlier than end date.")
        max_future_date = _max_allowed_future_date()
        if self.start_date and self.start_date > max_future_date:
            raise ValueError(f"start_date: This date cannot be more than {MAX_FUTURE_YEARS} years in the future.")
        if self.end_date and self.end_date > max_future_date:
            raise ValueError(f"end_date: This date cannot be more than {MAX_FUTURE_YEARS} years in the future.")
        return self


class HulkFigureImportLocation(BaseModel):
    uuid: uuid.UUID

    bounding_box: typing.Optional[typing.Tuple[float, float, float, float]] = None  # TODO: Correct structure?
    display_name: str
    country_name: str
    country_code: str = Field(max_length=8)

    identifier: FigureLocationIdentifierType
    accuracy: FigureLocationAccuracyType
    geocoder: FigureLocationGeocoderType

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    # TODO: We should also add the metadata field to store raw information that can be later used to fill gazetteer


class HulkFigureImport(HulkBaseModel):
    _hulk_data_type = HulkDataTypeEnum.FIGURE

    # Entry
    entry_id: typing.Optional[int] = None
    entry_uuid: typing.Optional[uuid.UUID] = None

    # Event
    event_id: typing.Optional[int] = None
    event_uuid: typing.Optional[uuid.UUID] = None

    # event_type=CONFLICT
    violence_sub_type_id: typing.Optional[int] = None  # ViolenceSubType
    context_of_violences_id: typing.Optional[ListOfIds] = None
    """FK: event.ContextOfViolence"""
    osv_sub_type_id: typing.Optional[int] = None
    """FK: event.OsvSubType"""
    # event_type=DISASTER
    disaster_sub_type_id: typing.Optional[int] = None  # DisasterSubType
    # event_type=OTHER
    other_sub_type_id: typing.Optional[int] = None  # OtherSubType

    figure_cause: EventType
    category: FigureCategoryType
    term: FigureTermType
    quantifier: FigureQuantifierType
    unit: FigureUnitType
    figure_role: FigureRoleType
    country_id: int  # FK

    # figure_category in Flow
    start_date: typing.Optional[datetime.date] = None
    start_date_accuracy: typing.Optional[DateAccuracy] = None
    end_date: typing.Optional[datetime.date] = None
    end_date_accuracy: typing.Optional[DateAccuracy] = None
    # figure_category in Stock
    stock_date: typing.Optional[datetime.date] = None
    """Saved as start_date"""
    stock_date_accuracy: typing.Optional[DateAccuracy] = None
    """Saved as start_date_accuracy"""
    stock_reporting_date: typing.Optional[datetime.date] = None
    """Saved as end_date"""
    # NOTE: Used to internally map from flow/stock date
    _start_date: datetime.date = PrivateAttr()
    _start_date_accuracy: DateAccuracy = PrivateAttr()
    _end_date: datetime.date = PrivateAttr()
    _end_date_accuracy: typing.Optional[DateAccuracy] = PrivateAttr(default=None)

    reported_figure: int
    is_housing_destruction: bool
    household_size: typing.Optional[float] = None
    displacement_occurred: FigureDisplacementOccurredType
    is_disaggregated: bool
    analysis_text: str
    source_excerpt_text: str
    include_idu: bool
    idu_text: str

    locations: typing_extensions.Annotated[
        typing.List[HulkFigureImportLocation],
        Field(min_length=1),
    ]

    tags_id: typing.Optional[ListOfIds] = []
    """
    FK: entry.FigureTag
    """

    sources_id: typing_extensions.Annotated[ListOfIds, Field(min_length=1)]
    """
    FK: organization.Organization
    """

    @field_validator("analysis_text")
    @classmethod
    def _validate_analysis_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("analysis_text must not be blank")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def parse_figure_cause(cls, data):
        if not isinstance(data, dict):
            return data
        helix_client = get_active_helix_client()
        raw_figure_cause = data.get("figure_cause") or ""
        figure_cause = validate_and_parse_enum(CRISIS_TYPE, raw_figure_cause, is_required=True)

        if figure_cause == CRISIS_TYPE.CONFLICT:
            helix_client.violence_sub_type_manager.validate_id_exists(data.get("violence_sub_type_id"))
        elif figure_cause == CRISIS_TYPE.DISASTER:
            helix_client.disaster_sub_type_manager.validate_id_exists(data.get("disaster_sub_type_id"))
        elif figure_cause == CRISIS_TYPE.OTHER:
            helix_client.other_sub_type_manager.validate_id_exists(data.get("other_sub_type_id"))
        else:
            typing_extensions.assert_never(figure_cause)

        return data

    @model_validator(mode="after")
    def _validate_household_size(self):
        if self.unit == FIGURE_UNIT.HOUSEHOLD and self.household_size is None:
            raise ValueError("household_size is required when unit is HOUSEHOLD")
        return self

    @model_validator(mode="after")
    def _validate_idu(self):
        if self.include_idu and (not self.idu_text or not self.idu_text.strip()):
            raise ValueError("idu_text is required (non-blank) when include_idu is True")
        return self

    @model_validator(mode="after")
    def parse_entry(self):
        if self.entry_id is None and self.entry_uuid is None:
            raise ValueError("either entry_id or entry_uuid is required")
        return self

    @model_validator(mode="after")
    def parse_event(self):
        if self.event_id is None and self.event_uuid is None:
            raise ValueError("either event_id or event_uuid is required")
        # TODO: Check if we can validate violence_sub_type_id, disaster_sub_type_id and other_sub_type_id using event_id?
        return self

    @model_validator(mode="after")
    def parse_dates(self):
        if self.category.value in FIGURE_FLOW_LIST:
            if (
                self.start_date is None
                or self.end_date is None
                or self.start_date_accuracy is None
                or self.end_date_accuracy is None
            ):
                raise ValueError(
                    "start_date/end_date/start_date_accuracy/end_date_accuracy are all required for flow category"
                )
            self._start_date = self.start_date
            self._start_date_accuracy = self.start_date_accuracy
            self._end_date = self.end_date
            self._end_date_accuracy = self.end_date_accuracy

        elif self.category.value in FIGURE_STOCK_LIST:
            if self.stock_date is None or self.stock_reporting_date is None or self.stock_date_accuracy is None:
                raise ValueError("stock_date/stock_reporting_date/stock_date_accuracy are all required for stock category")
            self._start_date = self.stock_date
            self._start_date_accuracy = self.stock_date_accuracy
            self._end_date = self.stock_reporting_date

        return self
