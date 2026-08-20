import typing
from collections import OrderedDict
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.postgres.aggregates.general import ArrayAgg, StringAgg
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Cast, Coalesce
from django.db.models.sql.constants import LOUTER
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _
from django_cte import CTEManager, With
from django_enumfield import enum

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR, format_event_codes_as_string
from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.models import (
    MetaInformationAbstractModel,
    MetaInformationArchiveAbstractModel,
    UUIDAbstractModel,
)
from apps.crisis.models import Crisis
from apps.entry.models import Figure
from apps.users.models import USER_ROLE, User
from utils.common import add_clone_prefix
from utils.db import Array


class NameAttributedModels(models.Model):
    name = models.CharField(_("Name"), max_length=256)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


# Models related to displacement caused by conflict


class Violence(NameAttributedModels):
    """
    Holds the possible violence choices
    """

    # violenceList
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )


class ViolenceSubType(NameAttributedModels):
    """
    Holds the possible violence sub types
    """

    # violence.subTypes
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )

    violence = models.ForeignKey("Violence", related_name="sub_types", on_delete=models.CASCADE)
    idu_name = models.CharField(_("IDU name"), max_length=256, null=True, blank=True)


class ContextOfViolence(MetaInformationAbstractModel, NameAttributedModels):
    """
    Holds the context of violence
    """

    # contextOfViolenceList
    ORDERING_ALLOWLIST = frozenset(
        {
            "created_at",
            "created_by__full_name",
            "id",
            "modified_at",
            "name",
        }
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import ContextOfViolenceFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id="ID",
            created_at="Created at",
            created_by__full_name="Created by",
            name="Name",
            modified_at="Modified At",
            last_modified_by__full_name="Last Modified By",
        )
        data = ContextOfViolenceFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.order_by("created_at")

        return {
            "headers": headers,
            "data": data.values(*[header for header in headers.keys()]),
            "formulae": None,
            "transformer": None,
        }


class OtherSubType(MetaInformationAbstractModel, NameAttributedModels):
    """
    Holds the other sub type
    """

    # otherSubTypeList
    ORDERING_ALLOWLIST = frozenset(
        {
            "created_at",
            "id",
            "modified_at",
            "name",
        }
    )

    idu_name = models.CharField(_("IDU name"), max_length=256, null=True, blank=True)


class Actor(MetaInformationAbstractModel, NameAttributedModels):
    """
    Conflict related actors
    """

    # actorList
    ORDERING_ALLOWLIST = frozenset(
        {
            "country__idmc_short_name",
            "created_at",
            "id",
            "modified_at",
            "name",
            "torg",
        }
    )

    country = models.ForeignKey(
        "country.Country", verbose_name=_("Country"), null=True, on_delete=models.SET_NULL, related_name="actors"
    )
    # NOTE: torg is used to map actors in the system to it's external source
    torg = models.CharField(verbose_name=_("Torg"), max_length=10, null=True)

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import ActorFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id="ID",
            created_at="Created at",
            created_by__full_name="Created by",
            name="Name",
            country__idmc_short_name="Country",
            country__iso3="ISO3",
            torg="TORG",
        )
        data = ActorFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.order_by("id")

        return {
            "headers": headers,
            "data": data.values(*[header for header in headers.keys()]),
            "formulae": None,
            "transformer": None,
        }


# Models related to displacement caused by disaster


class DisasterCategory(NameAttributedModels):
    """
    Holds the possible hazard category choices
    """

    # disasterCategoryList
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )


class DisasterSubCategory(NameAttributedModels):
    """
    Holds the possible hazard sub categories
    """

    # disasterSubCategoryList, disasterCategory.subCategories
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )

    category = models.ForeignKey(
        "DisasterCategory", verbose_name=_("Hazard Category"), related_name="sub_categories", on_delete=models.CASCADE
    )


class DisasterType(NameAttributedModels):
    """
    Holds the possible hazard types
    """

    # disasterTypeList, disasterSubCategory.types
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )

    disaster_sub_category = models.ForeignKey(
        "DisasterSubCategory", verbose_name=_("Hazard Sub Category"), related_name="types", on_delete=models.CASCADE
    )


class DisasterSubType(NameAttributedModels):
    """
    Holds the possible hazard sub types
    """

    # disasterSubTypeList, disasterType.subTypes
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )

    idu_name = models.CharField(_("IDU name"), max_length=256, null=True, blank=True)
    type = models.ForeignKey(
        "DisasterType", verbose_name=_("Hazard Type"), related_name="sub_types", on_delete=models.CASCADE
    )


class Event(MetaInformationArchiveAbstractModel, models.Model):
    # eventList
    ORDERING_ALLOWLIST = frozenset(
        {
            "countries__idmc_short_name",
            "created_at",
            "created_by__full_name",
            "crisis__name",
            "end_date",
            "entry_count",
            "event_type",
            "id",
            "modified_at",
            "name",
            "progress",
            "review_approved_count",
            "review_in_progress_count",
            "review_not_started_count",
            "review_re_request_count",
            "start_date",
            "total_count",
            "total_flow_nd_figures",
            "total_stock_idp_figures",
        }
    )

    class EVENT_REVIEW_STATUS(enum.Enum):
        REVIEW_NOT_STARTED = 0
        REVIEW_IN_PROGRESS = 1
        APPROVED = 2
        SIGNED_OFF = 3
        # NOTE: these two statuses should be hidden to the client
        APPROVED_BUT_CHANGED = 4
        SIGNED_OFF_BUT_CHANGED = 5

        __labels__ = {
            REVIEW_NOT_STARTED: _("Review not started"),
            REVIEW_IN_PROGRESS: _("Review in progress"),
            APPROVED: _("Approved"),
            SIGNED_OFF: _("Signed-off"),
            APPROVED_BUT_CHANGED: _("Approved but changed"),
            SIGNED_OFF_BUT_CHANGED: _("Signed-off but changed"),
        }

    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = "total_flow_nd_figures"
    IDP_FIGURES_ANNOTATE = "total_stock_idp_figures"
    IDP_FIGURES_REFERENCE_DATE_ANNOTATE = "idp_figures_reference_date"

    # CTEManager so the list queryset can render WITH clauses (used by the figure-count
    # ordering CTE in annotate_total_figure_disaggregation_via_cte), matching Figure.
    objects = CTEManager()

    crisis = models.ForeignKey(
        "crisis.Crisis", verbose_name=_("Crisis"), blank=True, null=True, related_name="events", on_delete=models.CASCADE
    )
    name = models.CharField(verbose_name=_("Event Name"), max_length=256)
    event_type = enum.EnumField(Crisis.CRISIS_TYPE, verbose_name=_("Event Cause"))

    other_sub_type = models.ForeignKey(
        "OtherSubType",
        verbose_name=_("Other sub type"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )
    glide_numbers = ArrayField(
        models.CharField(verbose_name=_("Event Codes"), max_length=256, null=True, blank=True),
        default=list,
        null=True,
        blank=True,
    )
    violence = models.ForeignKey(
        "Violence", verbose_name=_("Violence"), blank=False, null=True, related_name="events", on_delete=models.SET_NULL
    )
    violence_sub_type = models.ForeignKey(
        "ViolenceSubType",
        verbose_name=_("Violence Sub Type"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )
    actor = models.ForeignKey(
        "Actor", verbose_name=_("Actors"), blank=True, null=True, related_name="events", on_delete=models.SET_NULL
    )
    # disaster related fields
    disaster_category = models.ForeignKey(
        "DisasterCategory",
        verbose_name=_("Hazard Category"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )
    disaster_sub_category = models.ForeignKey(
        "DisasterSubCategory",
        verbose_name=_("Hazard Sub Category"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )
    disaster_type = models.ForeignKey(
        "DisasterType",
        verbose_name=_("Hazard Type"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )
    disaster_sub_type = models.ForeignKey(
        "DisasterSubType",
        verbose_name=_("Hazard Sub Type"),
        blank=True,
        null=True,
        related_name="events",
        on_delete=models.SET_NULL,
    )

    countries = models.ManyToManyField("country.Country", verbose_name=_("Countries"), related_name="events", blank=True)
    start_date = models.DateField(verbose_name=_("Start Date"))
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("Start Date Accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(verbose_name=_("End Date"))
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("End date accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    event_narrative = models.TextField(verbose_name=_("Event Narrative"), null=True)
    osv_sub_type = models.ForeignKey(
        "OsvSubType", verbose_name=_("OSV sub type"), blank=True, null=True, related_name="events", on_delete=models.SET_NULL
    )
    ignore_qa = models.BooleanField(verbose_name=_("Ignore QA"), default=False)
    context_of_violence = models.ManyToManyField(
        "ContextOfViolence", verbose_name=_("Context of violence"), blank=True, related_name="events"
    )
    assigner = models.ForeignKey(
        "users.User",
        verbose_name=_("Assigner"),
        null=True,
        blank=True,
        related_name="event_assigner",
        on_delete=models.SET_NULL,
    )
    assignee = models.ForeignKey(
        "users.User",
        verbose_name=_("Assignee"),
        null=True,
        blank=True,
        related_name="event_assignee",
        on_delete=models.SET_NULL,
    )
    assigned_at = models.DateTimeField(verbose_name="Assigned at", null=True, blank=True)
    review_status = enum.EnumField(
        EVENT_REVIEW_STATUS,
        verbose_name=_("Event status"),
        default=EVENT_REVIEW_STATUS.REVIEW_NOT_STARTED,
    )
    include_triangulation_in_qa = models.BooleanField(
        verbose_name="Include triangulation in qa?",
        default=False,
    )

    assignee_id: typing.Optional[int]

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["start_date"]),
            models.Index(fields=["end_date"]),
            models.Index(fields=["start_date_accuracy"]),
            models.Index(fields=["end_date_accuracy"]),
            models.Index(fields=["review_status"]),
            # The event list default ordering is created_at DESC NULLS LAST (applied by
            # nulls_last_order_queryset). A plain ascending index cannot serve DESC NULLS
            # LAST, so the list seq-scanned all events + top-N sorted. This expression
            # index matches the ordering, turning it into an index scan.
            models.Index(models.F("created_at").desc(nulls_last=True), name="event_created_at_desc_idx"),
        ]

        permissions = (
            ("assign_event", "Can assign on event level"),
            ("self_assign_event", "Can assign self on event level"),
            ("clear_assignee_event", "Can clear any assignee from event"),
            ("clear_self_assignee_event", "Can clear self assigned event"),
            ("sign_off_event", "Can sign-off event"),
        )

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None, reference_date=None):
        if figures is None:
            figures = Figure.objects.all()

        if reference_date is None:
            reference_date_qs = models.Subquery(
                figures.filter(
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    role=Figure.ROLE.RECOMMENDED,
                    event=models.OuterRef("pk"),
                )
                .order_by(models.F("end_date").desc(nulls_last=True))
                .values("end_date")[:1]
            )
        else:
            reference_date_qs = models.Value(reference_date)

        return {
            cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE: reference_date_qs,
            cls.ND_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_nd_figures(
                    figures.filter(
                        event=models.OuterRef("pk"),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    # TODO: what about date range
                    start_date=None,
                    end_date=None,
                )
                .order_by()
                .values("event")
                .annotate(_total=models.Sum("total_figures"))
                .values("_total")[:1],
                output_field=models.IntegerField(),
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        event=models.OuterRef("pk"),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=None,
                    end_date=models.OuterRef(cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE),
                )
                .order_by()
                .values("event")
                .annotate(_total=models.Sum("total_figures"))
                .values("_total")[:1],
                output_field=models.IntegerField(),
            ),
        }

    @classmethod
    def annotate_total_figure_disaggregation_via_cte(cls, queryset):
        """Set-based equivalent of `_total_figure_disaggregation_subquery` (default scope) for the
        list sort path: replaces ~40k per-event correlated subqueries with two chained CTEs over
        `entry_figure`, LEFT-JOINed onto `queryset` under the same `total_flow_nd_figures` /
        `total_stock_idp_figures` names (resolvers read them via getattr-fallback).

        The IDP reference date is MAX(end_date) over the event's IDPS/RECOMMENDED figures (NULLs
        ignored, matching the subquery's `end_date DESC NULLS LAST` pick); ND sums all
        NEW_DISPLACEMENT/RECOMMENDED figures. Figures always have start_date/end_date (so no NULL
        guards are needed).

        Default scope only — `aggregate_figures` (filtered set + explicit reference_date) must use
        the subquery.
        """
        rec = Figure.ROLE.RECOMMENDED.value
        idps = Figure.FIGURE_CATEGORY_TYPES.IDPS.value
        nd = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value

        # CTE1: reference date per event = MAX(end_date) over IDPS/RECOMMENDED figures.
        reference_date_cte = With(
            Figure.objects.filter(category=idps, role=rec)
            .values("event")
            .annotate(reference_date=models.Max("end_date"))
            .values("event", "reference_date"),
            name="event_figure_reference_date",
        )

        # CTE2: nd/idp counts per event, joined to the reference date from CTE1.
        figure_with_reference = reference_date_cte.join(
            Figure.objects.all(),
            event=reference_date_cte.col.event_id,
            _join_type=LOUTER,
        ).with_cte(reference_date_cte)
        figure_count_cte = With(
            figure_with_reference.values("event")
            .annotate(
                **{
                    cls.ND_FIGURES_ANNOTATE: models.Sum(
                        "total_figures",
                        filter=models.Q(category=nd, role=rec),
                    ),
                    cls.IDP_FIGURES_ANNOTATE: models.Sum(
                        "total_figures",
                        filter=models.Q(category=idps, role=rec) & models.Q(end_date=reference_date_cte.col.reference_date),
                    ),
                }
            )
            .values("event", cls.ND_FIGURES_ANNOTATE, cls.IDP_FIGURES_ANNOTATE),
            name="event_figure_count",
        )

        # queryset is a CTEQuerySet (Event.objects = CTEManager()), so the join renders
        # the WITH clause directly — same pattern as the figure ordering CTE.
        return (
            figure_count_cte.join(queryset, id=figure_count_cte.col.event_id, _join_type=LOUTER)
            .with_cte(figure_count_cte)
            .annotate(
                **{
                    cls.ND_FIGURES_ANNOTATE: figure_count_cte.col.total_flow_nd_figures,
                    cls.IDP_FIGURES_ANNOTATE: figure_count_cte.col.total_stock_idp_figures,
                }
            )
        )

    # Annotation name -> the figure review status it counts. `total_count` and `progress` are
    # derived from these four.
    REVIEW_FIGURE_COUNT_STATUSES = {
        "review_not_started_count": Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
        "review_in_progress_count": Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
        "review_re_request_count": Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
        "review_approved_count": Figure.FIGURE_REVIEW_STATUS.APPROVED,
    }
    REVIEW_FIGURES_COUNT_ANNOTATIONS = frozenset(REVIEW_FIGURE_COUNT_STATUSES) | {"total_count", "progress"}

    @classmethod
    def _review_figures_count_filters(cls, figure_prefix, event_prefix):
        """One `Q` per review count: the figure carries the status AND is either RECOMMENDED or
        attached to an event that includes triangulation in QA.

        `include_triangulation_in_qa` is a field on the EVENT, so the two arms need separate
        prefixes: they are reached from the event row itself when the count aggregates over
        `figures`, and through `event` when it aggregates over figures directly.
        """
        return {
            name: models.Q(
                **{
                    f"{figure_prefix}review_status": status,
                    f"{figure_prefix}role": Figure.ROLE.RECOMMENDED,
                }
            )
            | models.Q(
                **{
                    f"{figure_prefix}review_status": status,
                    f"{event_prefix}include_triangulation_in_qa": True,
                }
            )
            for name, status in cls.REVIEW_FIGURE_COUNT_STATUSES.items()
        }

    @classmethod
    def _review_figures_count_derived(cls):
        """`total_count` and `progress`, in terms of the four counts already annotated."""
        return {
            "total_count": (
                models.F("review_not_started_count")
                + models.F("review_in_progress_count")
                + models.F("review_re_request_count")
                + models.F("review_approved_count")
            ),
            "progress": models.Case(
                # Cast: both counts are integers, so the division truncates and every partially
                # approved row reads 0 -- the FloatField on the Case only labels the result.
                models.When(
                    total_count__gt=0,
                    then=Cast(models.F("review_approved_count"), models.FloatField()) / models.F("total_count"),
                ),
                default=models.Value(0),
                output_field=models.FloatField(),
            ),
        }

    @classmethod
    def annotate_review_figures_count(cls):
        """The six review counts as aggregates over the event's own `figures` join.

        For id-scoped callers (EventReviewCountLoader, the review-status update): the aggregate
        reads only the requested events' figures, where the whole-table CTE of
        `annotate_review_figures_count_via_cte` scans every figure (6ms -> 74ms on 50 ids).

        No `distinct`: these counts are only correct while nothing widens the `figures` join they
        share, and what keeps that true is the caller, not the filterset -- both live callers pass
        a single id, and the list's sort path goes through
        `annotate_review_figures_count_via_cte` instead, which groups inside the CTE and cannot
        be widened from outside. COUNT(DISTINCT) forbids hash aggregation, which is worth avoiding
        on a 186k-row table. `apps/event/tests/test_filters.py::TestEventReviewCountAggregation`
        pins the property by co-annotating a geolocation join and asserting the counts hold, so
        routing a multi-row queryset through this aggregate fails there.
        """
        return {
            **{
                name: models.Count("figures", filter=condition)
                for name, condition in cls._review_figures_count_filters(
                    figure_prefix="figures__",
                    event_prefix="",
                ).items()
            },
            **cls._review_figures_count_derived(),
        }

    @classmethod
    def annotate_review_figures_count_via_cte(cls, queryset):
        """Set-based equivalent of `annotate_review_figures_count` for the list sort path: one
        grouped pass over `entry_figure` keyed on `event_id`, LEFT-JOINed onto `queryset` under
        the same six names.

        Grouping figures on their own keeps every event column out of the 186k-row aggregation,
        so the planner hash-aggregates narrow rows instead of sorting wide ones (215ms -> 119ms
        on a 50-row page, temp spill 4752kB -> none).

        `Coalesce(..., 0)`: an event with no figures has no CTE row, while the aggregate this
        replaces counts 0 -- and `progress` divides by `total_count`.
        """
        counts = cls._review_figures_count_filters(figure_prefix="", event_prefix="event__")
        count_cte = With(
            Figure.objects.order_by()
            .values("event")
            .annotate(**{name: models.Count("id", filter=condition) for name, condition in counts.items()})
            .values("event", *counts),
            name="event_review_figure_count",
        )
        return (
            count_cte.join(queryset, id=count_cte.col.event_id, _join_type=LOUTER)
            .with_cte(count_cte)
            .annotate(**{name: Coalesce(getattr(count_cte.col, name), 0) for name in counts})
            .annotate(**cls._review_figures_count_derived())
        )

    # FIXME: this is wrong, this should see event and user not event and figure
    @staticmethod
    def regional_coordinators(event, actor=None):
        actor_regional_coordinators = User.objects.none()
        event_regional_coordinators = User.objects.none()

        if actor:
            actor_regional_coordinators = User.objects.filter(
                portfolios__role=USER_ROLE.REGIONAL_COORDINATOR,
                portfolios__monitoring_sub_region__in=actor.portfolios.values("monitoring_sub_region"),
            )

        if event.countries:
            event_regional_coordinators = User.objects.filter(
                portfolios__role=USER_ROLE.REGIONAL_COORDINATOR,
                portfolios__monitoring_sub_region__in=event.countries.values("portfolio__monitoring_sub_region"),
            )
        coordinators = actor_regional_coordinators | event_regional_coordinators
        return coordinators.values("id")

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.event.filters import EventFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id="ID",
            hulk_uuid="Hulk (UUID)",
            created_at="Created at",
            created_by__full_name="Created by",
            name="Name",
            start_date="Start date",
            start_date_accuracy="Start date accuracy",
            end_date="End date",
            end_date_accuracy="End date accuracy",
            event_type="Event cause",
            disaster_category__name="Hazard category",
            disaster_sub_category__name="Hazard sub category",
            disaster_type__name="Hazard type",
            disaster_sub_type__name="Hazard sub type",
            disaster_sub_type="Hazard sub type ID",
            countries_iso3="ISO3",
            countries_name="Countries",
            regions_name="Regions",
            figures_count="Figures count",
            entries_count="Entries count",
            # Extra added fields
            old_id="Old ID",
            crisis="Crisis ID",
            crisis__name="Crisis",
            **{
                cls.IDP_FIGURES_ANNOTATE: "IDPs figure",
                cls.ND_FIGURES_ANNOTATE: "ND figure",
            },
            other_sub_type__name="Other event sub type",
            violence__name="Violence type",
            violence_sub_type__name="Violence sub type",
            osv_sub_type__name="OSV sub type",
            actor_id="Actor ID",
            actor__name="Actor",
            context_of_violences="Context of violences",
            event_codes="Event codes (Code:Type:ISO3)",
            event_narrative="Event description",
            event_link="Event Link",
        )
        exclude_headers = ["event_link"]
        event_qs = EventFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs
        # The filter qs no longer annotates the figure disaggregation by default (it is
        # dataloader-resolved for the list); the excel export reads these columns directly.
        # When the export filter carries aggregate_figures the qs ALREADY annotates them
        # (dated to that aggregate), so only add the default (unfiltered) annotation when it
        # is absent — re-annotating unconditionally would overwrite the filtered values with
        # the whole-history default and silently export wrong figures.
        if cls.IDP_FIGURES_ANNOTATE not in event_qs.query.annotations:
            event_qs = event_qs.annotate(**cls._total_figure_disaggregation_subquery())
        data = (
            event_qs.annotate(
                hulk_uuid=models.F("hulkevent__uuid"),
                countries_iso3=StringAgg("countries__iso3", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
                countries_name=StringAgg("countries__idmc_short_name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
                regions_name=StringAgg("countries__region__name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
                figures_count=models.Count("figures", distinct=True),
                entries_count=models.Count("figures__entry", distinct=True),
                context_of_violences=StringAgg("context_of_violence__name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
                event_codes=ArrayAgg(
                    Array(
                        models.F("event_code__event_code"),
                        Cast(models.F("event_code__event_code_type"), models.CharField()),
                        models.F("event_code__country__iso3"),
                        output_field=ArrayField(models.CharField()),
                    ),
                    distinct=True,
                ),
            )
            .order_by("created_at")
            .values(*[header for header in headers.keys() if header not in exclude_headers])
        )

        def transformer(datum):
            return {
                **datum,
                **dict(
                    event_link=urljoin(settings.FRONTEND_BASE_URL, f"events/{datum['id']}"),
                    event_type=getattr(Crisis.CRISIS_TYPE.get(datum["event_type"]), "label", ""),
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum["start_date_accuracy"]), "label", ""),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum["end_date_accuracy"]), "label", ""),
                    event_codes=format_event_codes_as_string(datum["event_codes"]),
                ),
            }

        return {
            "headers": headers,
            "data": data,
            "formulae": None,
            "transformer": transformer,
        }

    def __str__(self):
        return self.name or str(self.id)

    def clone_and_save_event(self, user: "User"):
        event_data = model_to_dict(
            self,
            exclude=[
                "id",
                "created_at",
                "created_by",
                "last_modified_by",
            ],
        )
        # Clone m2m keys fields
        countries = event_data.pop("countries")
        context_of_violence = event_data.pop("context_of_violence")
        # Clone foreigh key fields
        foreign_key_fields_dict = {
            "crisis": Crisis,
            "violence": Violence,
            "violence_sub_type": ViolenceSubType,
            "actor": Actor,
            "disaster_category": DisasterCategory,
            "disaster_sub_category": DisasterSubCategory,
            "disaster_sub_type": DisasterSubType,
            "disaster_type": DisasterType,
            "osv_sub_type": OsvSubType,
            "other_sub_type": OtherSubType,
            "assigner": User,
            "assignee": User,
        }
        for field, model in foreign_key_fields_dict.items():
            if event_data[field]:
                event_data[field] = model.objects.get(pk=event_data[field])

        event_data["created_by"] = user
        event_data["name"] = add_clone_prefix(event_data["name"])
        cloned_event = Event.objects.create(**event_data)
        # Add m2m contires
        cloned_event.countries.set(countries)
        cloned_event.context_of_violence.set(context_of_violence)
        return cloned_event


class EventCode(UUIDAbstractModel, models.Model):
    class EVENT_CODE_TYPE(enum.Enum):
        GLIDE_NUMBER = 1
        GOV_ASSIGNED_IDENTIFIER = 2
        IFRC_APPEAL_ID = 3
        ACLED_ID = 4
        LOCAL_IDENTIFIER = 5

        __labels__ = {
            GLIDE_NUMBER: _("Glide Number"),
            GOV_ASSIGNED_IDENTIFIER: _("Government Assigned Identifier"),
            IFRC_APPEAL_ID: _("IFRC Appeal ID"),
            ACLED_ID: _("ACLED ID"),
            LOCAL_IDENTIFIER: _("Local Identifier"),
        }

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_code", verbose_name=_("Event"))
    country = models.ForeignKey(
        "country.Country", on_delete=models.CASCADE, related_name="event_code_country", verbose_name=_("Country")
    )
    event_code_type = enum.EnumField(EVENT_CODE_TYPE)
    event_code = models.CharField(max_length=256, verbose_name=_("Event Code"))

    event_id: int

    class Meta:
        ordering = ["event_code"]


class OsvSubType(NameAttributedModels):
    """
    Holds the possible OSV sub types
    """

    # osvSubTypeList
    ORDERING_ALLOWLIST = frozenset(
        {
            "id",
            "name",
        }
    )
