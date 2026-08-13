from django.db.models import Exists, OuterRef, Prefetch, prefetch_related_objects
from promise import Promise
from promise.dataloader import DataLoader

from apps.report.models import Report, ReportApproval, ReportGeneration

# M2M filter relations read by QueryAbstractModel.get_filter_kwargs. Prefetching these
# (lean, id-only) lets get_filter_kwargs read ids from the prefetch cache instead of one
# query per relation per report.
_REPORT_FILTER_M2M_FIELDS = [
    "filter_figure_countries",
    "filter_figure_regions",
    "filter_figure_geographical_groups",
    "filter_figure_events",
    "filter_figure_crises",
    "filter_figure_tags",
    "filter_figure_disaster_categories",
    "filter_figure_disaster_sub_categories",
    "filter_figure_disaster_types",
    "filter_figure_disaster_sub_types",
    "filter_figure_violence_types",
    "filter_figure_violence_sub_types",
    "filter_figure_osv_sub_types",
    "filter_figure_context_of_violence",
    "filter_figure_approved_by",
    "filter_figure_created_by",
    "filter_figure_sources",
    "filter_entry_publishers",
]


class ReportLastGenerationLoader(DataLoader):
    """Batch ReportType.last_generation across a report list.

    Report.last_generation is a per-report query (generations annotated with
    is_approved, ordered -created_at, first), so resolving it on a report list was
    an N+1 (see the FIXME on ReportType). This loads the latest generation for all
    batched reports in one query via DISTINCT ON (report_id), preserving the same
    is_approved annotation and "latest" rule (-created_at, pk breaking a tie).
    """

    def batch_load_fn(self, keys):
        qs = (
            ReportGeneration.objects.filter(report_id__in=keys)
            .annotate(is_approved=Exists(ReportApproval.objects.filter(generation=OuterRef("pk"), is_approved=True)))
            .order_by("report_id", "-created_at", "-id")
            .distinct("report_id")
        )
        _map = {generation.report_id: generation for generation in qs}
        return Promise.resolve([_map.get(key) for key in keys])


class ReportTotalDisaggregationLoader(DataLoader):
    """Batch ReportType.total_disaggregation across a report list.

    total_disaggregation per report = get_filter_kwargs + a Sum aggregate over the
    report's filtered figures. The per-report aggregate cannot be merged (each report has
    a distinct figure filter), but the ~18 M2M filter reads CAN: one id-only eager load
    covers the whole batch, so get_filter_kwargs reads ids from a prefetch cache instead
    of a query per relation per report.

    That eager load is for the reports whose kwargs the cache misses: a cached report
    resolves without touching a single filter relation.
    """

    def batch_load_fn(self, keys):
        reports = list(Report.objects.filter(id__in=keys))
        uncached = Report.with_uncached_filter_kwargs(reports)
        if uncached:
            prefetch_related_objects(
                uncached,
                *[
                    Prefetch(
                        field,
                        queryset=Report._meta.get_field(field).related_model._default_manager.only("id"),
                    )
                    for field in _REPORT_FILTER_M2M_FIELDS
                ],
            )
        _map = {report.id: report.total_disaggregation for report in reports}
        return Promise.resolve([_map.get(key) for key in keys])


class ReportGenerationApprovedLoader(DataLoader):
    # ReportGenerationType.is_approved = generation.approvals.filter(is_approved=True).exists().
    # Batch it: one query for all generations on report_generation_list / nested generations.
    def batch_load_fn(self, keys):
        approved = set(
            ReportApproval.objects.filter(generation_id__in=keys, is_approved=True).values_list("generation_id", flat=True)
        )
        return Promise.resolve([key in approved for key in keys])
