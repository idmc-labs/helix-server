import typing

from django.core.exceptions import FieldDoesNotExist
from django.db.models import F
from graphene import String
from graphene_django_extras import PageGraphqlPagination
from graphene_django_extras.paginations.pagination import BaseDjangoGraphqlPagination
from graphene_django_extras.paginations.utils import (
    _nonzero_int,
)
from graphene_django_extras.settings import graphql_api_settings

from utils.graphene.ordering import (
    declared_ordering,
    get_ordering_allowlist,
    leads_descending,
    orders_by_pk,
    strip_direction,
)


def _ordering_token_resolvable(qs, token):
    """Can `token` be used as an ORDER BY path on this queryset?

    An annotation alias counts (that is how the denormalised to-many sort keys bind), and so
    does any real model path. Everything else is client-supplied junk.

    A hop that does not resolve refuses the whole token, at any position. Accepting one past
    the first hop let `country__bogus` through to query compilation, where Django's FieldError
    enumerates every ORM field on the joined model — the leak this guard exists to close, on
    exactly the unbounded lists that have no allowlist in front of it.
    """
    if token in qs.query.annotations:
        return True
    model = qs.model
    *hops, last = token.split("__")
    for hop in hops:
        try:
            field = model._meta.get_field(hop)
        except FieldDoesNotExist:
            return False
        # Only a relation can carry the path further; a concrete field mid-token means the
        # rest is a lookup or a transform, neither of which is a sortable path here.
        model = getattr(field, "related_model", None)
        if model is None:
            return False
    try:
        model._meta.get_field(last)
    except FieldDoesNotExist:
        return False
    return True


def _ordering_token_allowed(qs, token):
    """May `token` be used as an ORDER BY path on this queryset?

    A model carrying an `ORDERING_ALLOWLIST` is bounded by what its clients actually sort on,
    so a resolvable but never-requested path (an internal column, or a to-many join the sort
    was never tuned for) is refused. An empty set bounds it to nothing. A model without the
    attribute keeps the looser resolvability check: an unbounded list must degrade to today's
    behaviour, not break.

    Allowed keys are still checked for resolvability — several are annotation aliases that
    only exist when the filterset applied them, and an unapplied one must fail here rather than
    surface as a raw FieldError from query compilation.
    """
    allowed = get_ordering_allowlist(qs.model)
    if allowed is not None and token not in allowed:
        return False
    return _ordering_token_resolvable(qs, token)


def nulls_last_order_queryset(qs, ordering_param, **kwargs):
    """
    https://docs.djangoproject.com/en/3.1/ref/models/expressions/#django.db.models.Expression.desc
    https://docs.djangoproject.com/en/3.1/ref/models/expressions/#using-f-to-sort-null-values
    """
    order = kwargs.pop(ordering_param, None) or ""
    # Empty tokens are not a request: `ordering=","` must read as "nothing asked for", or the
    # fallback below is skipped and the model's declared ordering is dropped.
    order = [token for token in order.strip(",").replace(" ", "").split(",") if token] if order else []

    pk_name = qs.model._meta.pk.name

    if not order:
        # Slicing an unordered queryset follows plan-dependent physical order, so
        # rows can repeat on or vanish between pages. pk ASC (not newest-first)
        # matches the nested-loader fallback and the de-facto insertion order the
        # public GIDD lists rely on.
        #
        # An ordering the queryset already carries is kept and COMPLETED, not returned as
        # found: `Meta.ordering` and a filterset's country-first bucket are both non-unique,
        # so without the tiebreaker the rows tying on them page unstably -- which for a
        # two-valued bucket means the whole list.
        existing = declared_ordering(qs)
        if not existing:
            return qs.order_by(pk_name)
        if orders_by_pk(existing, pk_name):
            return qs.order_by(*existing)
        tiebreaker = F(pk_name).desc() if leads_descending(existing) else F(pk_name).asc()
        return qs.order_by(*existing, tiebreaker)

    # Append a deterministic tiebreaker (the primary key) to `mod_ordering` so
    # paginated results are stable when rows tie on the sort key. Without it, ties
    # come back in plan-dependent physical order, so a row can appear on two pages
    # or be skipped across requests (and count-ordered lists reorder tied/NULL rows
    # vs the pre-optimization order).
    # Reject disallowed sort keys before they reach the ORM. `ordering` is a free-form
    # string, so a junk token otherwise raises Django's FieldError deep in query compilation
    # and the raw exception text — which enumerates every field on the model, including
    # columns absent from the GraphQL schema — is returned to the caller. Name only the token
    # the client sent. Checked per token because `ordering` may be comma-joined.
    for o in order:
        if o and not _ordering_token_allowed(qs, strip_direction(o)):
            raise ValueError(f"Invalid ordering field: {strip_direction(o)}")

    mod_ordering = []
    explicit_fields = set()
    primary_descending = order[0].startswith("-") if order and order[0] else False
    for o in order:
        if not o:
            continue
        if o[0] == "-":
            mod_ordering.append(F(o[1:]).desc(nulls_last=True))
            explicit_fields.add(o[1:])
        else:
            mod_ordering.append(F(o).asc(nulls_last=True))
            explicit_fields.add(o)

    # Append a deterministic pk tiebreaker to EVERY explicit ordering (unless the client
    # already orders by pk): ties on the sort key otherwise come back in plan-dependent order,
    # so a row can appear on two pages or be skipped across requests. It follows the primary
    # key's direction, so a descending sort still reads newest-first within a tie group -- a
    # fixed ASC tiebreak renders a bulk-created batch backwards under `-created_at`.
    # NOTE: on indexed single-column sorts this can defeat the index for the LIMIT.
    #
    # A filterset's own `order_by` leads, the client's keys follow: `orderCountryFirst` buckets
    # the rows a caller cares about to the front, and that bucket outranks the sort within it.
    # Only `query.order_by`, never `Meta.ordering` -- a model default outranking the client's
    # sort key would leave `ordering` with nothing to do.
    existing = list(qs.query.order_by)
    if pk_name not in explicit_fields and "pk" not in explicit_fields and not orders_by_pk(existing, pk_name):
        mod_ordering.append(F(pk_name).desc() if primary_descending else F(pk_name).asc())

    return qs.order_by(*existing, *mod_ordering)


class OrderingOnlyArgumentPagination(BaseDjangoGraphqlPagination):
    """
    Pagination just for ordering. Created for DjangoFilterPaginateListField (or its subclasses) in mind, to remove the
    page related arguments.
    """

    __name__ = "OrderingOnlyArgument"

    def __init__(
        self,
        ordering="",
        ordering_param="ordering",
    ):
        # Default ordering value: ""
        self.ordering = ordering

        # A string or comma delimited string values that indicate the default ordering when obtaining lists of objects.
        # Uses Django order_by syntax
        self.ordering_param = ordering_param

    def to_dict(self):
        return {
            "ordering_param": self.ordering_param,
            "ordering": self.ordering,
        }

    def to_graphql_fields(self):
        argument_dict = {
            self.ordering_param: String(
                description="A string or comma delimited string values that indicate the "
                "default ordering when obtaining lists of objects."
            ),
        }

        return argument_dict

    def paginate_queryset(self, qs, **kwargs):
        # One ordering rule for every list: `nulls_last_order_queryset` carries the allowlist
        # refusal, NULLS LAST, the filterset's own ordering, and the pk tiebreaker. A field served
        # here is often the same field a list serves through OneToManyLoader, so anything this
        # route did differently showed up as two orders for one set of arguments.
        kwargs[self.ordering_param] = kwargs.get(self.ordering_param) or self.ordering
        return nulls_last_order_queryset(qs, self.ordering_param, **kwargs)


class GatedPageGraphqlPagination(PageGraphqlPagination):
    """The library's page arithmetic with this project's ordering rule in front of it.

    `PageGraphqlPagination.paginate_queryset` calls `order_by()` on the raw token, so a list wired
    to it reaches SQL through none of the chokepoints: a junk token returns Django's FieldError
    with every column name in it, and a page slices on a sort key with no tiebreaker, which lets a
    tied row come back on two pages. Ordering therefore goes through `nulls_last_order_queryset`
    like every other list, and the library method is left to do only what it does well -- a
    negative page counts from the end, an oversize `pageSize` clamps to the maximum, `pageSize: 0`
    yields no rows.
    """

    def paginate_queryset(self, qs, **kwargs):
        # The library method re-applies `self.ordering` raw over whatever ordering the queryset
        # arrives with, which would drop the completion below.
        assert not self.ordering, "GatedPageGraphqlPagination takes its ordering from the request"
        ordering = kwargs.pop(self.ordering_param, None)
        qs = nulls_last_order_queryset(qs, self.ordering_param, **{self.ordering_param: ordering})
        return super().paginate_queryset(qs, **kwargs)


def get_page_size(page_size: typing.Optional[int]) -> typing.Optional[int]:
    """
    This is separated from PageGraphqlPaginationWithoutCount to support mocking in test cases
    NOTE: This will ignore manually defined limit within the PageGraphqlPaginationWithoutCount instance
    """
    page_size = page_size or graphql_api_settings.DEFAULT_PAGE_SIZE
    max_page_size = graphql_api_settings.MAX_PAGE_SIZE
    if page_size is not None:
        assert page_size <= max_page_size, ValueError(f"Max page size limit {max_page_size} exceeded")
        return page_size


class PageGraphqlPaginationWithoutCount(PageGraphqlPagination):
    """
    Default implementation applies qs.count()
    which is not possible with dataloading
    https://github.com/eamigo86/graphene-django-extras/blob/master/graphene_django_extras/paginations/pagination.py
    """

    def paginate_queryset(self, qs, **kwargs):
        page = kwargs.pop(self.page_query_param, 1) or 1
        assert page > 0, ValueError("Page value for PageGraphqlPagination must be a positive integer")

        if self.page_size_query_param:
            page_size = _nonzero_int(
                kwargs.get(self.page_size_query_param, self.page_size),
                strict=True,
            )
        else:
            page_size = self.page_size
        page_size = get_page_size(page_size)

        if page_size is None:
            """
            raise ValueError('Page_size value for PageGraphqlPagination must be a non-null value, you must set global'
                             ' DEFAULT_PAGE_SIZE on GRAPHENE_DJANGO_EXTRAS dict on your settings.py or specify a '
                             'page_size_query_param value on paginations declaration to specify a custom page size '
                             'value through a query parameters')
            """
            return None

        offset = page_size * (page - 1)

        ordering_param = self.ordering_param
        qs = nulls_last_order_queryset(qs, ordering_param, **kwargs)
        return qs[offset : offset + page_size]
