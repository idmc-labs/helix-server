import hashlib
from collections import defaultdict

from django.db.models import (
    Count,
    F,
    Window,
)
from django.db.models.functions import RowNumber
from django_cte import CTEQuerySet, With
from graphene_django_extras.paginations.utils import _nonzero_int
from promise import Promise
from promise.dataloader import DataLoader

from utils.graphene.ordering import (
    as_order_expressions,
    declared_ordering,
    leads_descending,
    orders_by_pk,
    strip_direction,
)
from utils.graphene.pagination import (
    _ordering_token_allowed,
    get_page_size,
    nulls_last_order_queryset,
)


def _ordering_expressions(qs, ordering_param, kwargs):
    """Build the order_by expression list (DESC NULLS LAST / ASC NULLS LAST) for the
    given ordering kwargs, mirroring ``nulls_last_order_queryset`` so a window's row
    numbering matches the order the paginated path would have sliced by.

    ``qs`` must be the filtered queryset the Window is annotated onto: the allowlist check
    resolves annotation aliases out of ``qs.query.annotations``, and the ordering-gated ones
    (event/crisis figure counts, user role flags, ...) exist only after the filterset has
    been handed the ordering.
    """
    order = kwargs.get(ordering_param) or ""
    order = order.strip(",").replace(" ", "").split(",") if order else []
    expressions = []
    explicit_fields = set()
    primary_descending = order[0].startswith("-") if order and order[0] else False
    for field in order:
        if not field:
            continue
        # Third and last chokepoint turning a client `ordering` string into SQL. Without it a
        # paginated nested list fed the raw token to the Window and Django's FieldError — which
        # enumerates every ORM field on the model, including columns absent from the GraphQL
        # schema — reached the caller, and tokens the top-level list refuses (to-many paths the
        # sort was never tuned for) were accepted here. Same per-token check and same message as
        # `nulls_last_order_queryset` / `OrderingOnlyArgumentPagination.paginate_queryset`.
        token = strip_direction(field)
        if not _ordering_token_allowed(qs, token):
            raise ValueError(f"Invalid ordering field: {token}")
        if field[0] == "-":
            expressions.append(F(field[1:]).desc(nulls_last=True))
            explicit_fields.add(field[1:])
        else:
            expressions.append(F(field).asc(nulls_last=True))
            explicit_fields.add(field)
    # A filterset's own `order_by` is prepended, mirroring `nulls_last_order_queryset`: a
    # queryset's ordering has no bearing on a window's ROW_NUMBER, so without this a nested
    # list numbers its rows ignoring the bucket its top-level counterpart leads with.
    existing = list(qs.query.order_by)
    if not expressions:
        # RowNumber needs a deterministic order, and with nothing requested that order is the
        # child's own: `Meta.ordering`, else pk, completed with a pk tiebreaker following the
        # leading key's direction -- the same rule as the top-level fallback, so a nested list
        # and its top-level counterpart agree. No model reachable through this window declares
        # `Meta.ordering` today, so the branch is a guarantee rather than a live payload.
        declared = declared_ordering(qs)
        if orders_by_pk(declared, qs.model._meta.pk.name):
            return as_order_expressions(declared)
        tiebreaker = F("pk").desc() if leads_descending(declared) else F("pk").asc()
        return [*as_order_expressions(declared), tiebreaker]
    # Append the pk as a deterministic tiebreaker (mirrors nulls_last_order_queryset) so a
    # paginated nested list with rows tying on the sort key numbers them stably across pages.
    # It follows the primary key's direction, as the top-level path does.
    pk_name = qs.model._meta.pk.name
    if pk_name not in explicit_fields and "pk" not in explicit_fields and not orders_by_pk(existing, pk_name):
        expressions.append(F("pk").desc() if primary_descending else F("pk").asc())
    return [*as_order_expressions(existing), *expressions]


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


def _stable_repr(value):
    """Order-independent, type-aware string for a loader argument.

    Dict and set ordering carries no meaning to a filterset, so it must not change the
    string. Values are tagged with their type so `1`, `"1"` and `True` stay distinct.
    """
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        return "{" + ",".join(f"{_stable_repr(k)}={_stable_repr(v)}" for k, v in items) + "}"
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_stable_repr(item) for item in value) + "]"
    if isinstance(value, (set, frozenset)):
        return "s[" + ",".join(sorted(_stable_repr(item) for item in value)) + "]"
    if isinstance(value, type):
        return f"{value.__module__}.{value.__qualname__}"
    return f"{type(value).__name__}:{value!r}"


def call_signature(params):
    """Hash of the arguments one nested-list resolution passes to its loader.

    A loader instance resolves its whole batch with a single set of arguments and caches
    promises by parent id alone, so two resolutions may share an instance only when this
    hash matches. `request` is excluded: it is fixed for the lifetime of a `GQLContext`,
    which is the lifetime of the loader registry.
    """
    signature = {key: value for key, value in params.items() if key != "request"}
    if "pagination" in signature:
        # A pagination instance belongs to a field definition and holds no per-call state; its
        # class is what decides whether the paginated or unpaginated batch path runs.
        signature["pagination"] = type(signature["pagination"])
    return hashlib.sha1(_stable_repr(signature).encode()).hexdigest()


class RelationCallLoader(DataLoader):
    """Holds the arguments of one nested-list resolution for its whole batch."""

    def __init__(
        self,
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
        super().__init__()
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


class CountLoader(RelationCallLoader):
    # The arguments a count batch is resolved with: the relation, the filters and the
    # requesting user. Pagination is not among them - a total counts the unpaged set.
    CALL_PARAMS = (
        "parent",
        "child",
        "related_name",
        "reverse_related_name",
        "filterset_class",
        "filter_kwargs",
        "request",
    )

    def batch_load_fn(self, keys):
        # queryset by related names
        reverse_related_name = self.reverse_related_name or get_related_name(self.child, self.parent)

        filtered_qs = self.filterset_class(data=self.filter_kwargs, request=self.request).qs

        # Single grouped count instead of one correlated COUNT subquery per parent row:
        # group the filtered children by the reverse relation and count once. Parents in
        # ``keys`` with no matching children simply don't appear in the result and fall
        # back to 0 below (same as the old NULL -> 0 coercion). ``.order_by()`` clears any
        # default ordering so it doesn't pollute the GROUP BY.
        counts = (
            filtered_qs.filter(**{f"{reverse_related_name}__in": keys})
            .order_by()
            .values(reverse_related_name)
            .annotate(c=Count("*"))
            .values_list(reverse_related_name, "c")
        )

        related_objects_by_parent = {parent_id: c for parent_id, c in counts}

        return Promise.resolve([related_objects_by_parent.get(key) or 0 for key in keys])


class OneToManyLoader(RelationCallLoader):
    def _filtered_qs(self):
        # Forward ordering to filtersets that opt in, so the (gated) figure-count annotations the
        # ordering references actually get added — mirrors the top-level path in
        # utils/graphene/fields.py (list_resolver). Without this, a nested list ordered by a gated
        # annotation (e.g. crisisList{events(ordering:"-total_stock_idp_figures")}) FieldErrors,
        # because nulls_last_order_queryset / _ordering_expressions reference an un-annotated column.
        fkw = {"data": self.filter_kwargs, "request": self.request}
        if getattr(self.filterset_class, "accepts_ordering", False):
            fkw["ordering"] = self.kwargs.get(self.pagination.ordering_param)
        return self.filterset_class(**fkw).qs

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
                self._filtered_qs()
                .filter(**{f"{reverse_related_name}__in": keys})
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

        filtered_qs = self._filtered_qs()
        base_qs = filtered_qs.filter(**{f"{reverse_related_name}__in": keys}).annotate(
            _dataloader_parent_id=F(reverse_related_name),
            _dataloader_row=Window(
                RowNumber(),
                partition_by=F(reverse_related_name),
                order_by=_ordering_expressions(filtered_qs, self.pagination.ordering_param, self.kwargs),
            ),
        )
        # Select from the CTE. With.queryset() builds the CTE-reading query but wraps it in
        # the child's default queryset (not always CTE-capable, e.g. SoftDelete/plain
        # managers), so rebind it to a CTEQuerySet to attach the WITH clause.
        cte = With(base_qs, name="dataloader_page")
        cte_qs = cte.queryset()
        cte_qs = CTEQuerySet(cte_qs.model, query=cte_qs.query, using=cte_qs.db).with_cte(cte)
        page_rows = cte_qs.filter(
            _dataloader_row__gt=offset,
            _dataloader_row__lte=offset + page_size,
        ).order_by("_dataloader_parent_id", "_dataloader_row")

        for child in page_rows:
            related_objects_by_parent[child._dataloader_parent_id].append(child)

        return Promise.resolve([related_objects_by_parent.get(key, []) for key in keys])
