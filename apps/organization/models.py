from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel, SoftDeleteModel

User = get_user_model()


class OrganizationKind(MetaInformationArchiveAbstractModel, models.Model):
    class ORGANIZATION_RELIABILITY(enum.Enum):
        LOW = 0
        MEDIUM = 1
        HIGH = 2
    name = models.CharField(verbose_name=_('Title'), max_length=256)
    reliability = enum.EnumField(
        ORGANIZATION_RELIABILITY, verbose_name=_('Reliability'),
        default=ORGANIZATION_RELIABILITY.LOW
    )

    def __str__(self):
        return self.name


class Organization(MetaInformationArchiveAbstractModel,
                   SoftDeleteModel,
                   models.Model):
    class ORGANIZATION_CATEGORY(enum.Enum):
        UNKNOWN = 0
        REGIONAL = 1
        INTERNATIONAL = 2
        NATIONAL = 3
        LOCAL = 4
        OTHER = 5

        __labels__ = {
            UNKNOWN: _("Unknown"),
            REGIONAL: _("Regional"),
            INTERNATIONAL: _("International"),
            NATIONAL: _("National"),
            LOCAL: _("Local"),
            OTHER: _("Other"),
        }
    name = models.CharField(verbose_name=_('Title'), max_length=512)
    short_name = models.CharField(verbose_name=_('Short Name'), max_length=64,
                                  null=True)
    category = enum.EnumField(ORGANIZATION_CATEGORY, verbose_name=_('Geographical Coverage'),
                              default=ORGANIZATION_CATEGORY.UNKNOWN)
    countries = models.ManyToManyField('country.Country', verbose_name=_('Countries'),
                                       related_name='organizations')
    organization_kind = models.ForeignKey('OrganizationKind', verbose_name=_('Organization Type'),
                                          blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='organizations')
    methodology = models.TextField(verbose_name=_('Methodology'), blank=True, null=True)
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
            created_by__full_name='Created by',
            created_at='Created at',
            last_modified_by__full_name='Updated by',
            modified_at='Updated at',
            name='Name',
            organization_kind__name='Organization Type',
            # Extra added fields
            countries_iso3='ISO3',
            category='Geographical Coverage',
            countries_name='Countries',
            # Extra added fields
            old_id='Old Id',
            short_name='Short Name',
            methodology='Methodology',
        )
        data = OrganizationFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            countries_iso3=StringAgg('countries__iso3', '; ', distinct=True),
            # sourced_entries_count=models.Count('sourced_entries', distinct=True),
            # published_entries_count=models.Count('published_entries', distinct=True),
            countries_name=StringAgg('countries__name', '; ', distinct=True),
        ).order_by('-id')

        def transformer(datum):
            return {
                **datum,
                **dict(
                    category=getattr(Organization.ORGANIZATION_CATEGORY.get(datum['category']), 'name', ''),
                )
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    def __str__(self):
        return self.name
