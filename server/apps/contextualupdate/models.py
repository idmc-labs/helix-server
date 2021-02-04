from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel
from apps.crisis.models import Crisis


class ContextualUpdate(MetaInformationArchiveAbstractModel, models.Model):
    url = models.URLField(verbose_name=_('Source URL'), max_length=2000,
                          blank=True, null=True)
    preview = models.OneToOneField('contrib.SourcePreview',
                                   related_name='contextual_update', on_delete=models.SET_NULL,
                                   blank=True, null=True,
                                   help_text=_('After the preview has been generated pass its id'
                                               'along during entry creation, so that during entry '
                                               'update the preview can be obtained.'))
    document = models.ForeignKey('contrib.Attachment', verbose_name='Attachment',
                                 on_delete=models.CASCADE, related_name='+',
                                 null=True, blank=True)
    article_title = models.TextField(verbose_name=_('Article Title'))
    sources = models.ManyToManyField('organization.Organization', verbose_name=_('Source'),
                                     blank=True, related_name='sourced_contextual_updates')
    publishers = models.ManyToManyField('organization.Organization', verbose_name=_('Publisher'),
                                        blank=True, related_name='published_contextual_updates')
    publish_date = models.DateTimeField(verbose_name=_('Published DateTime'))
    source_excerpt = models.TextField(verbose_name=_('Excerpt from Source'),
                                      blank=True, null=True)

    idmc_analysis = models.TextField(verbose_name=_('IDMC Analysis'),
                                     blank=False, null=True)
    is_confidential = models.BooleanField(
        verbose_name=_('Confidential Source'),
        default=False,
    )
    tags = models.ManyToManyField('entry.FigureTag', blank=True)
    countries = models.ManyToManyField('country.Country', blank=True)
    crisis_types = ArrayField(
        base_field=enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_('Crisis Type'))
    )
