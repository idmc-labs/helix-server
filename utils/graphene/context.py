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
    EventCountLoader,
    MaxStockIDPFigureEndDateByCrisisLoader,
    TotalIDPFigureByCrisisLoader,
    TotalNDFigureByCrisisLoader,
)
from apps.entry.dataloaders import (
    FigureGeoLocationLoader,
    FigureLastReviewCommentStatusLoader,
    FigureSourcesReliability,
    FigureTypologyLoader,
    TotalIDPFigureByEntryLoader,
    TotalNDFigureByEntryLoader,
)
from apps.event.dataloaders import (
    EventEntryCountLoader,
    EventFigureTypologyLoader,
    EventReviewCountLoader,
    EventTypologyLoader,
    MaxStockIDPFigureEndDateByEventLoader,
    TotalIDPFigureByEventLoader,
    TotalNDFigureByEventLoader,
)
from apps.hulk.dataloaders import (
    HulkBulkImportDatasetsLoader,
    HulkBulkImportFailureCountLoader,
    HulkBulkImportSuccessCountLoader,
)
from apps.report.dataloaders import (
    ReportGenerationApprovedLoader,
    ReportLastGenerationLoader,
    ReportTotalDisaggregationLoader,
)
from apps.users.dataloaders import UserPortfoliosMetadataLoader
from utils.graphene.dataloaders import CountLoader, OneToManyLoader
from utils.graphene.relation_loaders import RelationNodeLoader


class GQLContext:
    def __init__(self, request):
        self.request = request
        # global dataloaders
        self.one_to_many_dataloaders = {}
        self.count_dataloaders = {}
        # one RelationNodeLoader per related model (forward FK / O2O batching)
        self.relation_node_loaders = {}
        # one reverse-FK / M2M list loader per (parent, accessor) ref
        self.relation_list_loaders = {}

    @cached_property
    def user(self):
        return self.request.user

    def get_dataloader(self, parent: str, related_name: str):
        # TODO: rename to get OneToManyLoader?
        # returns a different dataloader for each ref
        ref = f"{parent}_{related_name}"
        if ref not in self.one_to_many_dataloaders:
            self.one_to_many_dataloaders[ref] = OneToManyLoader()
        return self.one_to_many_dataloaders[ref]

    def get_count_loader(self, parent: str, child: str):
        ref = f"{parent}_{child}"
        if ref not in self.count_dataloaders:
            self.count_dataloaders[ref] = CountLoader()
        return self.count_dataloaders[ref]

    def get_relation_node_loader(self, model):
        # one RelationNodeLoader per related model (batches forward FK / O2O loads by PK)
        ref = model._meta.label
        if ref not in self.relation_node_loaders:
            self.relation_node_loaders[ref] = RelationNodeLoader(model)
        return self.relation_node_loaders[ref]

    def get_relation_list_loader(self, ref, factory):
        # one reverse-FK / M2M list loader per relation ref (keyed by what the loader
        # queries: child/through model + FK names); factory() builds it once
        if ref not in self.relation_list_loaders:
            self.relation_list_loaders[ref] = factory()
        return self.relation_list_loaders[ref]

    """
    NOTE: As a convention, data loader should have the name as:
    AppName_NodeType_FieldName
    """

    @cached_property
    def entry_entry_total_stock_idp_figures(self):
        return TotalIDPFigureByEntryLoader()

    @cached_property
    def entry_entry_total_flow_nd_figures(self):
        return TotalNDFigureByEntryLoader()

    @cached_property
    def crisis_crisis_total_stock_idp_figures(self):
        return TotalIDPFigureByCrisisLoader()

    @cached_property
    def crisis_crisis_total_flow_nd_figures(self):
        return TotalNDFigureByCrisisLoader()

    @cached_property
    def crisis_stock_idp_figures_max_end_date(self):
        return MaxStockIDPFigureEndDateByCrisisLoader()

    @cached_property
    def event_event_total_stock_idp_figures(self):
        return TotalIDPFigureByEventLoader()

    @cached_property
    def event_event_total_flow_nd_figures(self):
        return TotalNDFigureByEventLoader()

    @cached_property
    def event_stock_idp_figures_max_end_date(self):
        return MaxStockIDPFigureEndDateByEventLoader()

    @cached_property
    def country_total_figure_disaggregation_loader(self):
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
