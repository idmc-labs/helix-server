from django.db import models
from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _

from apps.contrib.models import MetaInformationArchiveAbstractModel
from apps.crisis.models import Crisis
from apps.entry.constants import STOCK, FLOW
from apps.entry.models import FigureDisaggregationAbstractModel, Figure
from apps.extraction.models import QueryAbstractModel


class Report(MetaInformationArchiveAbstractModel,
             QueryAbstractModel,
             FigureDisaggregationAbstractModel,
             models.Model):
    # migrated or generated
    generated = models.BooleanField(verbose_name=_('Generated'), default=True,
                                    editable=False)
    reports = models.ManyToManyField('self', verbose_name=_('Reports (old groups)'),
                                     blank=True, related_name='masterfact_reports',
                                     symmetrical=False)
    figures = models.ManyToManyField('entry.Figure',
                                     blank=True)
    # user entered fields
    analysis = models.TextField(verbose_name=_('Analysis'),
                                blank=True, null=True)
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
    significant_updates = models.TextField(verbose_name=_('Significant Updates'),
                                           blank=True, null=True)
    challenges = models.TextField(verbose_name=_('Challenges'), blank=True, null=True)

    reported = models.PositiveIntegerField(verbose_name=_('Reported Figures'))
    total_figures = models.PositiveIntegerField(verbose_name=_('Total Figures'), default=0,
                                                editable=False)
    # old fields will be migrated into summary
    summary = models.TextField(verbose_name=_('Summary'), blank=True, null=True,
                               help_text=_('It will store master fact information:'
                                           'Comment, Source Excerpt, IDU Excerpt, Breakdown & '
                                           'Reliability, and Caveats'))

    @property
    def countries_report(self) -> list:
        if not self.generated:
            return (Figure.objects.filter(
                id__in=(
                    Report.objects.filter(id=self.id) |
                    Report.objects.get(id=self.id).masterfact_reports.all()
                ))
            ).select_related('country').values('country').order_by().annotate(
                total_stock_conflict=Sum(
                    'total_figures',
                    filter=Q(category__type=STOCK,
                             role=Figure.ROLE.RECOMMENDED,
                             entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
                ),
                total_flow_conflict=Sum(
                    'total_figures',
                    filter=Q(category__type=FLOW,
                             role=Figure.ROLE.RECOMMENDED,
                             entry__event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
                ),
                total_stock_disaster=Sum(
                    'total_figures',
                    filter=Q(category__type=STOCK,
                             role=Figure.ROLE.RECOMMENDED,
                             entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER)
                ),
                total_flow_disaster=Sum(
                    'total_figures',
                    filter=Q(category__type=FLOW,
                             role=Figure.ROLE.RECOMMENDED,
                             entry__event__event_type=Crisis.CRISIS_TYPE.DISASTER)
                ),
            )
        return []

    def __str__(self):
        return self.name
