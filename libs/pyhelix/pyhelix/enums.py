import enum


# --- INTERNAL
class HulkDataTypeEnum(str, enum.Enum):
    ATTACHMENT = "ATTACHMENT"
    SOURCE_PREVIEW = "SOURCE_PREVIEW"
    EVENT = "EVENT"
    ENTRY = "ENTRY"
    FIGURE = "FIGURE"


# TODO: We should rename this to either EntryType or EntrySourceType.
class HulkEntryImportTypeEnum(enum.Enum):
    DOCUMENT = "DOCUMENT"
    URL = "URL"
