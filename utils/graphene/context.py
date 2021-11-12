from django.utils.functional import cached_property

from apps.country.dataloaders import TotalFigureThisYearByCountryCategoryEventTypeLoader
from apps.crisis.dataloaders import TotalIDPFigureByCrisisLoader, TotalNDFigureByCrisisLoader
from apps.entry.dataloaders import TotalIDPFigureByEntryLoader, TotalNDFigureByEntryLoader
from apps.event.dataloaders import (
    TotalIDPFigureByEventLoader,
    TotalNDFigureByEventLoader,
    EventReviewCountLoader,
    EventEntryCountLoader,
)
from apps.crisis.dataloaders import CrisisReviewCountLoader
from utils.graphene.dataloaders import OneToManyLoader, CountLoader
from apps.entry.models import Figure


class GQLContext:
    def __init__(self, request):
        self.request = request
        # global dataloaders
        self.one_to_many_dataloaders = {}
        self.count_dataloaders = {}

    @cached_property
    def user(self):
        return self.request.user

    def get_dataloader(self, parent: str, related_name: str):
        # TODO: rename to get OneToManyLoader?
        # returns a different dataloader for each ref
        ref = f'{parent}_{related_name}'
        if ref not in self.one_to_many_dataloaders:
            self.one_to_many_dataloaders[ref] = OneToManyLoader()
        return self.one_to_many_dataloaders[ref]

    def get_count_loader(self, parent: str, child: str):
        ref = f'{parent}_{child}'
        if ref not in self.count_dataloaders:
            self.count_dataloaders[ref] = CountLoader()
        return self.count_dataloaders[ref]

    '''
    NOTE: As a convention, data loader should have the name as:
    AppName_NodeType_FieldName
    '''

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
    def event_event_total_stock_idp_figures(self):
        return TotalIDPFigureByEventLoader()

    @cached_property
    def event_event_total_flow_nd_figures(self):
        return TotalNDFigureByEventLoader()

    @cached_property
    def country_country_this_year_idps_disaster_loader(self):
        from apps.crisis.models import Crisis
        return TotalFigureThisYearByCountryCategoryEventTypeLoader(
            category__in=Figure.stock_ids(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
        )

    @cached_property
    def country_country_this_year_idps_conflict_loader(self):
        from apps.crisis.models import Crisis
        return TotalFigureThisYearByCountryCategoryEventTypeLoader(
            category__in=Figure.stock_ids(),
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
        )

    @cached_property
    def country_country_this_year_nd_conflict_loader(self):
        from apps.crisis.models import Crisis
        return TotalFigureThisYearByCountryCategoryEventTypeLoader(
            category__in=Figure.flow_list(),
            event_type=Crisis.CRISIS_TYPE.CONFLICT.value,
        )

    @cached_property
    def country_country_this_year_nd_disaster_loader(self):
        from apps.crisis.models import Crisis
        return TotalFigureThisYearByCountryCategoryEventTypeLoader(
            category__in=Figure.flow_list(),
            event_type=Crisis.CRISIS_TYPE.DISASTER.value,
        )

    @cached_property
    def event_event_review_count_dataloader(self):
        return EventReviewCountLoader()

    @cached_property
    def event_entry_count_dataloader(self):
        return EventEntryCountLoader()

    @cached_property
    def crisis_crisis_review_count_dataloader(self):
        return CrisisReviewCountLoader()
