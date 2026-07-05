import typing

from django.db.models import F
from graphene import String
from graphene_django_extras import PageGraphqlPagination
from graphene_django_extras.paginations.pagination import BaseDjangoGraphqlPagination
from graphene_django_extras.paginations.utils import (
    _nonzero_int,
)
from graphene_django_extras.settings import graphql_api_settings


def nulls_last_order_queryset(qs, ordering_param, **kwargs):
    """
    https://docs.djangoproject.com/en/3.1/ref/models/expressions/#django.db.models.Expression.desc
    https://docs.djangoproject.com/en/3.1/ref/models/expressions/#using-f-to-sort-null-values
    """
    order = kwargs.pop(ordering_param, None) or ""
    if order:
        order = order.strip(",").replace(" ", "").split(",")

    if not order:
        # Slicing an unordered queryset follows plan-dependent physical order, so
        # rows can repeat on or vanish between pages. pk ASC (not newest-first)
        # matches the nested-loader fallback and the de-facto insertion order the
        # public GIDD lists rely on.
        if qs.ordered:
            return qs
        return qs.order_by(qs.model._meta.pk.name)

    # Append a deterministic tiebreaker (the primary key) to `mod_ordering` so
    # paginated results are stable when rows tie on the sort key. Without it, ties
    # come back in plan-dependent physical order, so a row can appear on two pages
    # or be skipped across requests (and count-ordered lists reorder tied/NULL rows
    # vs the pre-optimization order).
    mod_ordering = []
    explicit_fields = set()
    for o in order:
        if not o:
            continue
        if o[0] == "-":
            mod_ordering.append(F(o[1:]).desc(nulls_last=True))
            explicit_fields.add(o[1:])
        else:
            mod_ordering.append(F(o).asc(nulls_last=True))
            explicit_fields.add(o)

    # Append a deterministic pk tiebreaker ONLY when ordering by an annotation (e.g. an
    # aggregate/count field such as total_stock_idp_figures). That is exactly where ties are
    # common (many entities share a 0/NULL count) and where pagination was non-deterministic,
    # and the annotation has no single-column index to defeat — so the tiebreaker is both
    # needed and free there. For ordering by a real indexed column (created_at, idmc_short_name)
    # appending `id` would defeat the index for the LIMIT and measurably regress figure-filtered
    # lists (e.g. country.ff.multi / event.ff.report: +40ms@p10), while ties on those columns are
    # rare — so we leave them as-is (the pre-existing behaviour).
    pk_name = qs.model._meta.pk.name
    annotated_fields = set(getattr(qs.query, "annotations", None) or {})
    if explicit_fields & annotated_fields and pk_name not in explicit_fields and "pk" not in explicit_fields:
        mod_ordering.append(F(pk_name).desc())

    return qs.distinct().order_by(*mod_ordering)


class NoOrderingPageGraphqlPagination(PageGraphqlPagination):
    """
    Custom pagination to support enum ordering from filterset
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_graphql_fields(self):
        fields = super().to_graphql_fields()
        fields.pop(self.ordering_param)
        return fields


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
        order = kwargs.pop(self.ordering_param, None) or self.ordering
        if order:
            if "," in order:
                order = order.strip(",").replace(" ", "").split(",")
                if order.__len__() > 0:
                    qs = qs.order_by(*order)
            else:
                qs = qs.order_by(order)
        return qs


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
