import graphene

from utils.enums import enum_description

from .models import HulkBulkImport, HulkBulkImportDataset

HulkBulkImportStatusEnum = graphene.Enum.from_enum(HulkBulkImport.HULK_BULK_IMPORT_STATUS, description=enum_description)
HulkBulkImportDatasetImportTypeEnum = graphene.Enum.from_enum(
    HulkBulkImportDataset.HULK_BULK_IMPORT_DATASET_IMPORT_TYPE, description=enum_description
)

enum_map = dict(
    HULK_BULK_IMPORT_STATUS=HulkBulkImportStatusEnum,
    HULK_BULK_IMPORT_DATASET_IMPORT_TYPE=HulkBulkImportDatasetImportTypeEnum,
)
