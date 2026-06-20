from collections import defaultdict

from django.db.models import (
    Count,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Subquery,
)
from promise import Promise
from promise.dataloader import DataLoader

from utils.graphene.pagination import nulls_last_order_queryset


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
        related_name = self.related_name or get_related_name(self.parent, self.child)
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

        # Paginated fields (page params present) keep the per-parent windowed subquery so the
        # DB returns at most one page per parent — important when a parent can have a large
        # related set (e.g. a country's events).
        filtered_qs = self.filterset_class(
            data=self.filter_kwargs,
            request=self.request,
        ).qs.filter(**{reverse_related_name: OuterRef(reverse_related_name)})
        filtered_paginated_qs = self.pagination.paginate_queryset(filtered_qs, **self.kwargs).values("id")

        OUT_RELATED_FIELD = "out_related_field"

        prefetch = Prefetch(
            related_name,
            queryset=self.child.objects.filter(id__in=Subquery(filtered_paginated_qs)).distinct(),
            to_attr=OUT_RELATED_FIELD,
        )
        qs = self.parent.objects.filter(id__in=keys).prefetch_related(prefetch)
        for each in qs:
            related_objects_by_parent[each.id] = getattr(each, OUT_RELATED_FIELD)

        return Promise.resolve([related_objects_by_parent.get(key, []) for key in keys])
