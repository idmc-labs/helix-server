from django.utils.functional import cached_property

from apps.contrib.dataloaders import (
    BulkApiOperationFailureListLoader,
    BulkApiOperationSuccessListLoader,
)
from apps.country.dataloaders import (
    CountryLastContextualAnalysisLoader,
    CountryLastSummaryLoader,
    CountryMonitoringExpertLoader,
    CountryTotalFigureDisaggregationLoader,
    MonitoringSubRegionCountryCountLoader,
    MonitoringSubRegionRegionalCoordinatorLoader,
)
from apps.crisis.dataloaders import (
    CrisisReviewCountLoader,
    CrisisTotalFigureDisaggregationLoader,
    EventCountLoader,
    MaxStockIDPFigureEndDateByCrisisLoader,
)
from apps.entry.dataloaders import (
    FigureGeoLocationLoader,
    FigureLastReviewCommentStatusLoader,
    FigureSourcesReliability,
    FigureTypologyLoader,
)
from apps.event.dataloaders import (
    EventEntryCountLoader,
    EventFigureTypologyLoader,
    EventReviewCountLoader,
    EventTotalFigureDisaggregationLoader,
    EventTypologyLoader,
    MaxStockIDPFigureEndDateByEventLoader,
)
from apps.hulk.dataloaders import (
    AttachmentHulkLoader,
    EntryHulkLoader,
    EventHulkLoader,
    FigureHulkLoader,
    HulkBulkImportDatasetsLoader,
    HulkBulkImportFailureCountLoader,
    HulkBulkImportSkipCountLoader,
    HulkBulkImportSuccessCountLoader,
    SourcePreviewHulkLoader,
)
from apps.report.dataloaders import (
    ReportGenerationApprovedLoader,
    ReportLastGenerationLoader,
    ReportTotalDisaggregationLoader,
)
from apps.users.dataloaders import UserPortfoliosMetadataLoader
from utils.graphene.dataloaders import FilteredRelationCountLoader, FilteredRelationListLoader, call_signature
from utils.graphene.relation_loaders import RelationNodeLoader


class GQLContext:
    def __init__(self, request):
        self.request = request
        # one loader per (relation, call-arguments) pair
        self.filtered_relation_list_loaders = {}
        self.filtered_relation_count_loaders = {}
        # one RelationNodeLoader per related model (forward FK / O2O batching)
        self.relation_node_loaders = {}
        # one reverse-FK / M2M / reverse-O2O loader per relation ref
        self.relation_loaders = {}

    @cached_property
    def user(self):
        return self.request.user

    def get_filtered_relation_list_loader(self, parent: str, related_name: str, params: dict):
        # One loader per relation AND per set of call arguments: a loader resolves its whole
        # batch with the arguments it was built with and caches promises by parent id alone,
        # so two aliases of the same field with different filters/pagination each need their
        # own. Callers sharing an argument set share the loader, and so batch into one query.
        ref = f"{parent}_{related_name}_{call_signature(params)}"
        if ref not in self.filtered_relation_list_loaders:
            self.filtered_relation_list_loaders[ref] = FilteredRelationListLoader(**params)
        return self.filtered_relation_list_loaders[ref]

    def get_filtered_relation_count_loader(self, parent: str, child: str, params: dict):
        # `related_name` separates two relations running from the same parent to the same
        # child (ContextualUpdate sources/publishers, Country contacts/operatingContacts),
        # which count different rows. The loader is built with — and keyed by — only the
        # arguments a count is resolved with, so aliases that differ merely in page size
        # share one loader and one query.
        count_params = {key: params[key] for key in FilteredRelationCountLoader.CALL_PARAMS if key in params}
        ref = f"{parent}_{child}_{params.get('related_name')}_{call_signature(count_params)}"
        if ref not in self.filtered_relation_count_loaders:
            self.filtered_relation_count_loaders[ref] = FilteredRelationCountLoader(**count_params)
        return self.filtered_relation_count_loaders[ref]

    def get_relation_node_loader(self, model):
        # one RelationNodeLoader per related model (batches forward FK / O2O loads by PK)
        ref = model._meta.label
        if ref not in self.relation_node_loaders:
            self.relation_node_loaders[ref] = RelationNodeLoader(model)
        return self.relation_node_loaders[ref]

    def get_relation_loader(self, ref, factory):
        # one loader per relation ref (keyed by what the loader queries: child/through
        # model + FK names, prefixed by relation kind); factory() builds it once
        if ref not in self.relation_loaders:
            self.relation_loaders[ref] = factory()
        return self.relation_loaders[ref]

    """
    NOTE: As a convention, data loader should have the name as:
    AppName_NodeType_FieldName
    """

    @cached_property
    def crisis_total_figure_disaggregation_loader(self):
        return CrisisTotalFigureDisaggregationLoader()

    @cached_property
    def crisis_stock_idp_figures_max_end_date(self):
        return MaxStockIDPFigureEndDateByCrisisLoader()

    @cached_property
    def event_total_figure_disaggregation_loader(self):
        return EventTotalFigureDisaggregationLoader()

    @cached_property
    def event_stock_idp_figures_max_end_date(self):
        return MaxStockIDPFigureEndDateByEventLoader()

    @cached_property
    def country_total_figure_disaggregation_loader(self):
        # One loader for the four (category, event type) totals: they share a query, so
        # they must share the batch that runs it.
        return CountryTotalFigureDisaggregationLoader()

    @cached_property
    def monitoring_sub_region_country_count_loader(self):
        return MonitoringSubRegionCountryCountLoader()

    @cached_property
    def country_last_summary_loader(self):
        return CountryLastSummaryLoader()

    @cached_property
    def country_last_contextual_analysis_loader(self):
        return CountryLastContextualAnalysisLoader()

    @cached_property
    def country_monitoring_expert_loader(self):
        return CountryMonitoringExpertLoader()

    @cached_property
    def monitoring_subregion_regional_coordinator_loader(self):
        return MonitoringSubRegionRegionalCoordinatorLoader()

    @cached_property
    def event_entry_count_dataloader(self):
        return EventEntryCountLoader()

    @cached_property
    def event_hulk_dataloader(self):
        return EventHulkLoader()

    @cached_property
    def figure_hulk_dataloader(self):
        return FigureHulkLoader()

    @cached_property
    def entry_hulk_dataloader(self):
        return EntryHulkLoader()

    @cached_property
    def attachment_hulk_dataloader(self):
        return AttachmentHulkLoader()

    @cached_property
    def source_preview_hulk_dataloader(self):
        return SourcePreviewHulkLoader()

    @cached_property
    def event_typology_dataloader(self):
        return EventTypologyLoader()

    @cached_property
    def event_figure_typology_dataloader(self):
        return EventFigureTypologyLoader()

    @cached_property
    def figure_typology_dataloader(self):
        return FigureTypologyLoader()

    @cached_property
    def figure_geolocations_loader(self):
        return FigureGeoLocationLoader()

    @cached_property
    def figure_sources_reliability_loader(self):
        return FigureSourcesReliability()

    @cached_property
    def last_review_comment_status_loader(self):
        return FigureLastReviewCommentStatusLoader()

    @cached_property
    def event_count_dataloader(self):
        return EventCountLoader()

    @cached_property
    def event_review_count_dataloader(self):
        return EventReviewCountLoader()

    @cached_property
    def crisis_review_count_dataloader(self):
        return CrisisReviewCountLoader()

    @cached_property
    def bulk_api_operation_success_list_loader(self):
        return BulkApiOperationSuccessListLoader()

    @cached_property
    def bulk_api_operation_failure_list_loader(self):
        return BulkApiOperationFailureListLoader()

    @cached_property
    def hulk_bulk_import_success_count_loader(self):
        return HulkBulkImportSuccessCountLoader()

    @cached_property
    def hulk_bulk_import_failure_count_loader(self):
        return HulkBulkImportFailureCountLoader()

    @cached_property
    def hulk_bulk_import_skip_count_loader(self):
        return HulkBulkImportSkipCountLoader()

    @cached_property
    def hulk_bulk_import_datasets_loader(self):
        return HulkBulkImportDatasetsLoader()

    @cached_property
    def user_portfolios_metadata(self):
        return UserPortfoliosMetadataLoader()

    @cached_property
    def report_report_last_generation(self):
        return ReportLastGenerationLoader()

    @cached_property
    def report_report_total_disaggregation(self):
        return ReportTotalDisaggregationLoader()

    @cached_property
    def report_generation_approved_loader(self):
        return ReportGenerationApprovedLoader()
