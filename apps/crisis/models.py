from collections import OrderedDict

from django.contrib.postgres.aggregates.general import StringAgg
from django.db import models
from django.db.models.functions import Cast
from django.db.models.sql.constants import LOUTER
from django.utils.translation import gettext_lazy as _
from django_cte import CTEManager, With
from django_enumfield import enum

from apps.common.utils import EXTERNAL_ARRAY_SEPARATOR
from apps.contrib.commons import DATE_ACCURACY
from apps.contrib.models import MetaInformationAbstractModel
from apps.users.models import User


class Crisis(MetaInformationAbstractModel, models.Model):
    # crisisList
    ORDERING_ALLOWLIST = frozenset(
        {
            "countries__idmc_short_name",
            "created_at",
            "created_by__full_name",
            "crisis_type",
            "end_date",
            "event_count",
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

    # NOTE figure disaggregation variable definitions
    ND_FIGURES_ANNOTATE = "total_flow_nd_figures"
    IDP_FIGURES_ANNOTATE = "total_stock_idp_figures"
    IDP_FIGURES_REFERENCE_DATE_ANNOTATE = "idp_figures_reference_date"

    # CTEManager so the list queryset can render WITH clauses (used by the figure-count
    # ordering CTE in annotate_total_figure_disaggregation_via_cte), matching Figure/Event.
    objects = CTEManager()

    class CRISIS_TYPE(enum.Enum):
        CONFLICT = 0
        DISASTER = 1
        OTHER = 2

        __labels__ = {
            CONFLICT: _("Conflict"),
            DISASTER: _("Disaster"),
            OTHER: _("Other"),
        }

    name = models.CharField(verbose_name=_("Name"), max_length=256)
    crisis_type = enum.EnumField(CRISIS_TYPE, verbose_name=_("Cause"))
    crisis_narrative = models.TextField(_("Crisis Narrative/Summary"))
    countries = models.ManyToManyField("country.Country", verbose_name=_("Countries"), related_name="crises")
    start_date = models.DateField(verbose_name=_("Start Date"), blank=True, null=True)
    start_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("Start Date Accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )
    end_date = models.DateField(verbose_name=_("End Date"), blank=True, null=True)
    end_date_accuracy = enum.EnumField(
        DATE_ACCURACY,
        verbose_name=_("End date accuracy"),
        default=DATE_ACCURACY.DAY,
        blank=True,
        null=True,
    )

    class Meta:
        indexes = [
            # The crisis list default ordering is created_at DESC NULLS LAST (applied by
            # nulls_last_order_queryset). A plain ascending index cannot serve DESC NULLS
            # LAST, so the list seq-scanned/sorted all crises. This expression index
            # matches the ordering, turning it into an index scan.
            models.Index(models.F("created_at").desc(nulls_last=True), name="crisis_created_at_desc_idx"),
        ]

    @classmethod
    def _total_figure_disaggregation_subquery(cls, figures=None, reference_date=None):
        from apps.entry.models import Figure

        if figures is None:
            figures = Figure.objects.all()

        if reference_date is None:
            reference_date_qs = models.Subquery(
                figures.filter(
                    category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                    role=Figure.ROLE.RECOMMENDED,
                    event__crisis=models.OuterRef("pk"),
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
                        event__crisis=models.OuterRef("pk"),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    # TODO: what about date range
                    start_date=None,
                    end_date=None,
                )
                .order_by()
                .values("event__crisis")
                .annotate(_total=models.Sum("total_figures"))
                .values("_total")[:1],
                output_field=models.IntegerField(),
            ),
            cls.IDP_FIGURES_ANNOTATE: models.Subquery(
                Figure.filtered_idp_figures(
                    figures.filter(
                        event__crisis=models.OuterRef("pk"),
                        role=Figure.ROLE.RECOMMENDED,
                    ),
                    start_date=None,
                    end_date=models.OuterRef(cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE),
                )
                .order_by()
                .values("event__crisis")
                .annotate(_total=models.Sum("total_figures"))
                .values("_total")[:1],
                output_field=models.IntegerField(),
            ),
        }

    @classmethod
    def annotate_total_figure_disaggregation_via_cte(cls, queryset, keys=None, figures=None, reference_date=None):
        """Crisis mirror of `Event.annotate_total_figure_disaggregation_via_cte`, grouping figures
        by `event__crisis` (the `figure -> event -> crisis` two-hop) instead of `event`.

        `figures`/`reference_date` default to all figures + the per-crisis MAX(end_date) reference
        date (sort + dataloader paths). `aggregate_figures` passes the *filtered* figure queryset
        and its own reference date (scalar for report scope, else the per-crisis max over the
        filtered set) so the scoped totals are one grouped scan instead of correlated subqueries
        re-scanned per page row, and the scoped reference date is exposed so
        `stock_idp_figures_max_end_date` still matches.

        ND sums all NEW_DISPLACEMENT/RECOMMENDED figures; IDP sums IDPS/RECOMMENDED figures whose
        end_date equals the reference date. Figures always have start_date/end_date (no NULL guards).
        """
        from apps.entry.models import Figure

        rec = Figure.ROLE.RECOMMENDED.value
        idps = Figure.FIGURE_CATEGORY_TYPES.IDPS.value
        nd = Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value

        # base figure set: the filtered aggregate_figures set when scoped, else all figures
        # (optionally narrowed to the dataloader's batch keys). Only figures reaching a crisis.
        # `role` sits in the scan, not only in the aggregate FILTERs: both totals require
        # RECOMMENDED, and the partial `WHERE role = 0` covering indexes are only provable from the
        # WHERE clause. A crisis with no recommended figure drops out of the count CTE rather than
        # carrying NULL sums, and its reference date is NULL either way -- CTE1 filters on role too.
        if figures is not None:
            count_figures = figures.filter(role=rec, event__crisis__isnull=False)
            ref_figures = figures.filter(category=idps, role=rec, event__crisis__isnull=False)
        else:
            count_figures = Figure.objects.filter(role=rec, event__crisis__isnull=False)
            ref_figures = Figure.objects.filter(category=idps, role=rec, event__crisis__isnull=False)
            if keys is not None:
                count_figures = count_figures.filter(event__crisis__in=keys)
                ref_figures = ref_figures.filter(event__crisis__in=keys)

        if reference_date is None:
            # CTE1: reference date per crisis = MAX(end_date) over IDPS/RECOMMENDED figures. The
            # group key is the spanned `event__crisis`, aliased to `crisis_id` so django_cte can
            # resolve `.col.crisis_id`.
            reference_date_cte = With(
                ref_figures.values("event__crisis")
                .annotate(crisis_id=models.F("event__crisis"), reference_date=models.Max("end_date"))
                .values("crisis_id", "reference_date"),
                name="crisis_figure_reference_date",
            )
            count_base = reference_date_cte.join(
                count_figures, event__crisis=reference_date_cte.col.crisis_id, _join_type=LOUTER
            ).with_cte(reference_date_cte)
            idp_end = reference_date_cte.col.reference_date
        else:
            # explicit scalar reference date (report scope): no reference CTE needed.
            count_base = count_figures
            idp_end = reference_date

        expose_ref = figures is not None and reference_date is None
        count_annotations = {
            "crisis_id": models.F("event__crisis"),
            cls.ND_FIGURES_ANNOTATE: models.Sum("total_figures", filter=models.Q(category=nd, role=rec)),
            cls.IDP_FIGURES_ANNOTATE: models.Sum(
                "total_figures", filter=models.Q(category=idps, role=rec) & models.Q(end_date=idp_end)
            ),
        }
        cte_values = ["crisis_id", cls.ND_FIGURES_ANNOTATE, cls.IDP_FIGURES_ANNOTATE]
        if expose_ref:
            count_annotations[cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE] = models.Max(reference_date_cte.col.reference_date)
            cte_values.append(cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE)

        figure_count_cte = With(
            count_base.values("event__crisis").annotate(**count_annotations).values(*cte_values),
            name="crisis_figure_count",
        )

        outer = {
            cls.ND_FIGURES_ANNOTATE: figure_count_cte.col.total_flow_nd_figures,
            cls.IDP_FIGURES_ANNOTATE: figure_count_cte.col.total_stock_idp_figures,
        }
        if figures is not None:
            outer[cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE] = (
                getattr(figure_count_cte.col, cls.IDP_FIGURES_REFERENCE_DATE_ANNOTATE)
                if reference_date is None
                else models.Value(reference_date, output_field=models.DateField())
            )

        # queryset is a CTEQuerySet (Crisis.objects = CTEManager()), so the join renders the WITH.
        return (
            figure_count_cte.join(queryset, id=figure_count_cte.col.crisis_id, _join_type=LOUTER)
            .with_cte(figure_count_cte)
            .annotate(**outer)
        )

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.crisis.filters import CrisisFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id="ID",
            created_at="Created at",
            created_by__full_name="Created by",
            name="Name",
            start_date="Start date",
            start_date_accuracy="Start date accuracy",
            end_date="End date",
            end_date_accuracy="End date accuracy",
            crisis_type="Cause",
            countries_iso3="ISO3s",
            countries_name="Countries",
            regions_name="Regions",
            events_count="Events count",
            figures_count="Figures count",
            min_event_start="Earliest event start",
            max_event_end="Latest event end",
            **{
                cls.IDP_FIGURES_ANNOTATE: "IDPs figure",
                cls.ND_FIGURES_ANNOTATE: "ND figure",
            },
        )
        crisis_qs = CrisisFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs
        # The filter qs no longer annotates the figure disaggregation by default (it is
        # dataloader-resolved for the list); the excel export reads these columns directly.
        # When the export filter carries aggregate_figures the qs ALREADY annotates them
        # (dated to that aggregate), so only add the default (unfiltered) annotation when it
        # is absent — re-annotating unconditionally would overwrite the filtered values with
        # the whole-history default and silently export wrong figures.
        if cls.IDP_FIGURES_ANNOTATE not in crisis_qs.query.annotations:
            crisis_qs = crisis_qs.annotate(**cls._total_figure_disaggregation_subquery())
        data = crisis_qs.annotate(
            countries_iso3=StringAgg("countries__iso3", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            countries_name=StringAgg("countries__idmc_short_name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            regions_name=StringAgg("countries__region__name", EXTERNAL_ARRAY_SEPARATOR, distinct=True),
            events_count=models.Count("events", distinct=True),
            min_event_start=models.Min("events__start_date"),
            max_event_end=models.Max("events__end_date"),
            figures_count=models.Count("events__figures", distinct=True),
        ).order_by("created_at")

        def transformer(datum):
            return {
                **datum,
                **dict(
                    start_date_accuracy=getattr(DATE_ACCURACY.get(datum["start_date_accuracy"]), "label", ""),
                    end_date_accuracy=getattr(DATE_ACCURACY.get(datum["end_date_accuracy"]), "label", ""),
                    crisis_type=getattr(Crisis.CRISIS_TYPE.get(datum["crisis_type"]), "label", ""),
                ),
            }

        return {
            "headers": headers,
            "data": data.values(*[header for header in headers.keys()]),
            "formulae": None,
            "transformer": transformer,
        }

    # dunders

    def __str__(self):
        return self.name

    @classmethod
    def annotate_review_figures_count(cls):
        from apps.entry.models import Figure

        return {
            "review_not_started_count": models.Count(
                "events__figures",
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                )
                | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_NOT_STARTED,
                    events__include_triangulation_in_qa=True,
                ),
            ),
            "review_in_progress_count": models.Count(
                "events__figures",
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                )
                | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_IN_PROGRESS,
                    events__include_triangulation_in_qa=True,
                ),
            ),
            "review_re_request_count": models.Count(
                "events__figures",
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                )
                | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.REVIEW_RE_REQUESTED,
                    events__include_triangulation_in_qa=True,
                ),
            ),
            "review_approved_count": models.Count(
                "events__figures",
                filter=models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    events__figures__role=Figure.ROLE.RECOMMENDED,
                )
                | models.Q(
                    events__figures__review_status=Figure.FIGURE_REVIEW_STATUS.APPROVED,
                    events__include_triangulation_in_qa=True,
                ),
            ),
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
