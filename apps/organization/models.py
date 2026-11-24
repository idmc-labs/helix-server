from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.contrib.models import MetaInformationArchiveAbstractModel, SoftDeleteModel

User = get_user_model()


class SourceType(MetaInformationArchiveAbstractModel, models.Model):
    """IDMC source type. Each OrganizationKind is one of its subtypes.
    Its level is the Source Type Classification of every organization whose kind links here.
    """

    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "level",
            "name",
        }
    )

    class SOURCE_TYPE_CLASSIFICATION(enum.Enum):
        LEVEL_1 = 1
        LEVEL_2 = 2
        LEVEL_3 = 3

        __labels__ = {
            LEVEL_1: _("High"),
            LEVEL_2: _("Medium"),
            LEVEL_3: _("Low"),
        }

    name = models.CharField(verbose_name=_("Name"), max_length=256)
    level = enum.EnumField(SOURCE_TYPE_CLASSIFICATION, verbose_name=_("Source type classification"))

    class Meta:
        ordering = ["level", "name"]

    def __str__(self):
        return self.name


class OrganizationKind(MetaInformationArchiveAbstractModel, models.Model):
    # organizationKindList
    ORDERING_ALLOWLIST = frozenset(
        {
            "created_at",
            "id",
            "modified_at",
            "name",
            "source_type__level",
            "source_type__name",
        }
    )

    # NOTE: the reliability field removed. The enum stays only because migration 0008
    # imports it (migrations are not edited). Do not use it.
    class ORGANIZATION_RELIABILITY(enum.Enum):
        LOW = 0
        MEDIUM = 1
        HIGH = 2

    name = models.CharField(verbose_name=_("Title"), max_length=256)
    source_type = models.ForeignKey(
        SourceType,
        verbose_name=_("Source type"),
        on_delete=models.PROTECT,
        related_name="organization_kinds",
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name


class Organization(MetaInformationArchiveAbstractModel, SoftDeleteModel, models.Model):
    # organizationList
    ORDERING_ALLOWLIST = frozenset(
        {
            "category",
            "countries__idmc_short_name",
            "created_at",
            "id",
            "modified_at",
            "name",
            "organization_kind__name",
            "short_name",
        }
    )

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

    name = models.CharField(verbose_name=_("Title"), max_length=512)
    short_name = models.CharField(verbose_name=_("Short Name"), max_length=64, null=True)
    category = enum.EnumField(
        ORGANIZATION_CATEGORY, verbose_name=_("Geographical Coverage"), default=ORGANIZATION_CATEGORY.UNKNOWN
    )
    countries = models.ManyToManyField(
        "country.Country", blank=True, verbose_name=_("Countries"), related_name="organizations"
    )
    organization_kind = models.ForeignKey(
        "OrganizationKind",
        verbose_name=_("Organization Type"),
        blank=True,
        null=True,
        on_delete=models.PROTECT,  # A kind still used by an organization cannot be deleted.
        related_name="organizations",
    )
    methodology = models.TextField(verbose_name=_("Methodology"), blank=True, null=True)
    parent = models.ForeignKey(
        "Organization",
        verbose_name=_("Organization"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="sub_organizations",
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["short_name"]),
        ]

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.organization.filters import OrganizationFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id="ID",
            created_by__full_name="Created by",
            created_at="Created at",
            last_modified_by__full_name="Updated by",
            modified_at="Updated at",
            name="Name",
            organization_kind__name="Organization type",
            # Extra added fields
            countries_iso3="ISO3",
            category="Geographical coverage",
            countries_name="Countries",
            # Extra added fields
            old_id="Old ID",
            short_name="Short name",
            methodology="Methodology",
        )
        data = (
            OrganizationFilter(
                data=filters,
                request=DummyRequest(user=User.objects.get(id=user_id)),
            )
            .qs.annotate(
                countries_iso3=StringAgg("countries__iso3", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
                # sourced_entries_count=models.Count('sourced_entries', distinct=True),
                # published_entries_count=models.Count('published_entries', distinct=True),
                countries_name=StringAgg("countries__idmc_short_name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            )
            .order_by("created_at")
        )

        def transformer(datum):
            return {
                **datum,
                **dict(
                    category=getattr(Organization.ORGANIZATION_CATEGORY.get(datum["category"]), "label", ""),
                ),
            }

        return {
            "headers": headers,
            "data": data.values(*[header for header in headers.keys()]),
            "formulae": None,
            "transformer": transformer,
        }

    def __str__(self):
        return self.name
