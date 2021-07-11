from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, SoftDeleteModel

User = get_user_model()


class OrganizationKind(MetaInformationArchiveAbstractModel, models.Model):
    name = models.CharField(verbose_name=_('Title'), max_length=256)

    def __str__(self):
        return self.name


class Organization(MetaInformationArchiveAbstractModel,
                   SoftDeleteModel,
                   models.Model):
    class ORGANIZATION_CATEGORY(enum.Enum):
        UNKNOWN = 0
        REGIONAL = 1
        INTERNATIONAL = 2

        __labels__ = {
            UNKNOWN: _("Unknown"),
            REGIONAL: _("Regional"),
            INTERNATIONAL: _("International"),
        }
    name = models.CharField(verbose_name=_('Title'), max_length=512)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=64,
                                  null=True)
    category = enum.EnumField(ORGANIZATION_CATEGORY, verbose_name=_('Crisis Type'),
                              default=ORGANIZATION_CATEGORY.UNKNOWN)
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='organizations')
    organization_kind = models.ForeignKey('OrganizationKind', verbose_name=_('Organization Type'),
                                          blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='organizations')
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
    breakdown = models.TextField(verbose_name=_('Source Breakdown and Reliability'), blank=True, null=True)
    parent = models.ForeignKey('Organization', verbose_name=_('Organization'),
                               null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.organization.filters import OrganizationFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='Id',
            name='Name',
            short_name='Short name',
            organization_kind__name='Organization Type',
            countries_iso3='ISO3',
            methodology='Methodology',
            breakdown='Breakdown',
            sourced_entries_count='Sourced Entries Count',
            published_entries_count='Published Entries Count',
            created_by__full_name='Created By',
            created_at='Created At',
            last_modified_by__full_name='Modified By',
            modified_at='Modified At',
        )
        data = OrganizationFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=StringAgg('countries__iso3', '; ', distinct=True),
            sourced_entries_count=models.Count('sourced_entries', distinct=True),
            published_entries_count=models.Count('published_entries', distinct=True),
        ).order_by('-created_at').select_related(
            'organization_kind'
            'created_by',
            'last_modified_by',
        ).prefetch_related(
            'countries'
        )

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': None,
        }

    def __str__(self):
        return self.name
