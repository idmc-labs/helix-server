from django.utils.functional import cached_property

from utils.graphene.dataloaders import OneToManyLoader, CountLoader
from apps.entry.dataloaders import TotalIDPFigureByEntryLoader, TotalNDFigureByEntryLoader


class GQLContext:
    def __init__(self, request):
        self.request = request
        self.one_to_many_dataloaders = {}
        self.count_dataloaders = {}

    @cached_property
    def user(self):
        return self.request.user

    def get_dataloader(self, parent: str, child: str):
        # TODO: rename to get OneToManyLoader?
        # return a different dataloader for each ref
        ref = f'{parent}_{child}'
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
