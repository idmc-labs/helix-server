from django.db import models
from promise import Promise
from promise.dataloader import DataLoader

from apps.entry.models import Figure, FigureCategory


class TotalIDPFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Figure.objects.filter(
            entry__in=keys
        ).order_by().values(
            'entry'
        ).annotate(
            total_idp_figures=models.Sum(
                'total_figures',
                filter=models.Q(
                    role=Figure.ROLE.RECOMMENDED,
                    category=FigureCategory.stock_idp_id(),
                ),
            )
        ).values('entry', 'total_idp_figures')

        batch_load = {
            item['entry']: item['total_idp_figures']
            for item in qs
        }

        return Promise.resolve([
            batch_load.get(key, 0) for key in keys
        ])


class TotalNDFigureByEntryLoader(DataLoader):
    def batch_load_fn(self, keys):
        qs = Figure.objects.filter(
            entry__in=keys
        ).order_by().values(
            'entry'
        ).annotate(
            total_nd_figures=models.Sum(
                'total_figures',
                filter=models.Q(
                    role=Figure.ROLE.RECOMMENDED,
                    category=FigureCategory.flow_new_displacement_id(),
                ),
            )
        ).values('entry', 'total_nd_figures')

        batch_load = {
            item['entry']: item['total_nd_figures']
            for item in qs
        }

        return Promise.resolve([
            batch_load.get(key, 0) for key in keys
        ])
