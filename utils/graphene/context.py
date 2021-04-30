from django.utils.functional import cached_property

from apps.country.dataloaders import TotalFigureThisYearByCountryCategoryLoader
from apps.entry.dataloaders import TotalIDPFigureByEntryLoader, TotalNDFigureByEntryLoader
from apps.event.dataloaders import TotalIDPFigureByEventLoader, TotalNDFigureByEventLoader
from utils.graphene.dataloaders import OneToManyLoader, CountLoader


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
    def event_event_total_stock_idp_figures(self):
        return TotalIDPFigureByEventLoader()

    @cached_property
    def event_event_total_flow_nd_figures(self):
        return TotalNDFigureByEventLoader()

    @cached_property
    def country_country_this_year_idps_loader(self):
        from apps.entry.models import FigureCategory
        return TotalFigureThisYearByCountryCategoryLoader(
            category=FigureCategory.stock_idp_id()
        )

    @cached_property
    def country_country_this_year_nd_loader(self):
        from apps.entry.models import FigureCategory
        return TotalFigureThisYearByCountryCategoryLoader(
            category=FigureCategory.flow_new_displacement_id()
        )
