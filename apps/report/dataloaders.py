from django.db.models import Exists, OuterRef
from promise import Promise
from promise.dataloader import DataLoader

from apps.report.models import ReportApproval, ReportGeneration


class ReportLastGenerationLoader(DataLoader):
    """Batch ReportType.last_generation across a report list.

    Report.last_generation is a per-report query (generations annotated with
    is_approved, ordered -created_at, first), so resolving it on a report list was
    an N+1 (see the FIXME on ReportType). This loads the latest generation for all
    batched reports in one query via DISTINCT ON (report_id), preserving the same
    is_approved annotation and -created_at "latest" semantics.
    """

    def batch_load_fn(self, keys):
        qs = (
            ReportGeneration.objects.filter(report_id__in=keys)
            .annotate(is_approved=Exists(ReportApproval.objects.filter(generation=OuterRef("pk"), is_approved=True)))
            .order_by("report_id", "-created_at")
            .distinct("report_id")
        )
        _map = {generation.report_id: generation for generation in qs}
        return Promise.resolve([_map.get(key) for key in keys])
