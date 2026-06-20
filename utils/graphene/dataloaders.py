from collections import defaultdict

from django.db.models import (
    Count,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Window,
)
from django.db.models.functions import RowNumber
from django_cte import CTEQuerySet, With
from graphene_django_extras.paginations.utils import _nonzero_int
from promise import Promise
from promise.dataloader import DataLoader

from utils.graphene.pagination import get_page_size, nulls_last_order_queryset


def _ordering_expressions(ordering_param, kwargs):
    """Build the order_by expression list (DESC NULLS LAST / ASC NULLS LAST) for the
    given ordering kwargs, mirroring ``nulls_last_order_queryset`` so a window's row
    numbering matches the order the paginated path would have sliced by."""
    order = kwargs.get(ordering_param) or ""
    order = order.strip(",").replace(" ", "").split(",") if order else []
    expressions = []
    for field in order:
        if not field:
            continue
        if field[0] == "-":
            expressions.append(F(field[1:]).desc(nulls_last=True))
        else:
            expressions.append(F(field).asc(nulls_last=True))
    # RowNumber needs a deterministic order; fall back to pk (the paginated slice was
    # otherwise on arbitrary physical order, which is not a stable contract).
    return expressions or [F("pk").asc()]


def get_relations(model1, model2):
    relations = []
    for field in model1._meta.get_fields():
        if field.is_relation and field.related_model == model2:
            relations.append(field.name)
    return relations


def get_related_name(model1, model2):
    """
    To be used with models with single relationship in between
    Returns the first relation found

    If multiple relations exists, pass related_name and reverse_related_name explicitly
    """
    relations = get_relations(model1, model2)
    if relations:
        return relations[0]


class DataLoaderException(Exception):
    """
    Unable to batch load
    """


class CountLoader(DataLoader):
    def load(
        self,
        key,
        parent,
        child,
        related_name=None,
        reverse_related_name=None,
        accessor=None,
        pagination=None,
        filterset_class=None,
        filter_kwargs=None,
        request=None,
        **kwargs,
    ):
        self.parent = parent
        self.child = child
        self.related_name = related_name
        self.reverse_related_name = reverse_related_name
        self.accessor = accessor
        self.pagination = pagination
        self.filterset_class = filterset_class
        self.filter_kwargs = filter_kwargs
        self.request = request
        # kwargs carries pagination kwargs
        self.kwargs = kwargs
        return super().load(key)

    def batch_load_fn(self, keys):
        # queryset by related names
        reverse_related_name = self.reverse_related_name or get_related_name(self.child, self.parent)

        filtered_qs = self.filterset_class(data=self.filter_kwargs, request=self.request).qs

        qs = (
            self.parent.objects.filter(id__in=keys)
            .annotate(
                count=Subquery(
                    filtered_qs.filter(**{reverse_related_name: OuterRef("pk")})
                    .order_by()
                    .values(reverse_related_name)
                    .annotate(c=Count("*"))
                    .values("c"),
                    output_field=IntegerField(),
                )
            )
            .values_list("id", "count")
        )

        related_objects_by_parent = {id_: count for id_, count in qs}

        return Promise.resolve([related_objects_by_parent.get(key) or 0 for key in keys])


class OneToManyLoader(DataLoader):
    def load(
        self,
        key,
        parent,
        child,
        related_name=None,
        reverse_related_name=None,
        accessor=None,
        pagination=None,
        filterset_class=None,
        filter_kwargs=None,
        request=None,
        **kwargs,
    ):
        self.parent = parent
        self.child = child
        self.related_name = related_name
        self.reverse_related_name = reverse_related_name
        self.accessor = accessor
        self.pagination = pagination
        self.filterset_class = filterset_class
        self.filter_kwargs = filter_kwargs
        self.request = request
        # kwargs carries pagination kwargs
        self.kwargs = kwargs
        return super().load(key)

    def batch_load_fn(self, keys):
        self.related_name or get_related_name(self.parent, self.child)
        reverse_related_name = self.reverse_related_name or get_related_name(self.child, self.parent)

        related_objects_by_parent = defaultdict(list)

        # The default pagination (OrderingOnlyArgumentPagination) has no page params, so the
        # field returns *every* related child per parent (just ordered). The old code did
        # this with an unsliced correlated subquery `child.filter(reverse=OuterRef(reverse))`
        # which, for M2M relations with high reverse fan-out (e.g. a source organization
        # linked to thousands of figures), produced a huge semi-join + DISTINCT-over-all-
        # columns sort (figureList { sources }: ~244k intermediate rows / 74MB on-disk sort
        # / ~1.7s). Since there is no per-parent limit here, fetch the batch's children once
        # and group in Python — same result set, no cross product (~48ms).
        if not getattr(self.pagination, "page_size_query_param", None):
            related_qs = (
                self.filterset_class(data=self.filter_kwargs, request=self.request)
                .qs.filter(**{f"{reverse_related_name}__in": keys})
                .annotate(_dataloader_parent_id=F(reverse_related_name))
            )
            related_qs = nulls_last_order_queryset(related_qs, self.pagination.ordering_param, **self.kwargs)
            for child in related_qs:
                related_objects_by_parent[child._dataloader_parent_id].append(child)
            return Promise.resolve([related_objects_by_parent.get(key, []) for key in keys])

        # Paginated fields (page params present): return at most one page per parent. The
        # old code did this with a Prefetch over a correlated subquery
        #   child.filter(reverse=OuterRef(reverse)).order_by(...)[offset:offset+size]
        # which, for M2M relations, joined the through table per outer child and produced a
        # large intermediate. Instead, number each parent's children with a ROW_NUMBER()
        # window inside a CTE and keep only the requested page — the DB returns exactly the
        # paged rows, no cross product (countryList { events } ~107ms -> ~5ms at DB level).
        page = self.kwargs.get(self.pagination.page_query_param, 1) or 1
        page_size = get_page_size(
            _nonzero_int(
                self.kwargs.get(self.pagination.page_size_query_param, self.pagination.page_size),
                strict=True,
            )
        )
        offset = page_size * (page - 1)

        base_qs = (
            self.filterset_class(data=self.filter_kwargs, request=self.request)
            .qs.filter(**{f"{reverse_related_name}__in": keys})
            .annotate(
                _dataloader_parent_id=F(reverse_related_name),
                _dataloader_row=Window(
                    RowNumber(),
                    partition_by=F(reverse_related_name),
                    order_by=_ordering_expressions(self.pagination.ordering_param, self.kwargs),
                ),
            )
        )
        # Select from the CTE. With.queryset() builds the CTE-reading query but wraps it in
        # the child's default queryset (not always CTE-capable, e.g. SoftDelete/plain
        # managers), so rebind it to a CTEQuerySet to attach the WITH clause.
        cte = With(base_qs)
        cte_qs = cte.queryset()
        cte_qs = CTEQuerySet(cte_qs.model, query=cte_qs.query, using=cte_qs.db).with_cte(cte)
        page_rows = cte_qs.filter(
            _dataloader_row__gt=offset,
            _dataloader_row__lte=offset + page_size,
        ).order_by("_dataloader_parent_id", "_dataloader_row")

        for child in page_rows:
            related_objects_by_parent[child._dataloader_parent_id].append(child)

        return Promise.resolve([related_objects_by_parent.get(key, []) for key in keys])
