from collections import defaultdict

from promise import Promise
from promise.dataloader import DataLoader
from django.db.models import (
    Prefetch,
    Subquery,
    OuterRef,
    Count,
    IntegerField,
)


def get_relations(model1, model2):
    relations = []
    for field in model1._meta.get_fields():
        if field.is_relation and field.related_model == model2:
            relations.append(field.name)
    return relations


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
        **kwargs
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

    def get_related_name(self, model1, model2):
        '''
        To be used with models with single relationship in between
        Returns the first relation found

        If multiple relations exists, pass related_name and reverse_related_name explicitly
        '''
        relations = get_relations(model1, model2)
        if relations:
            return relations[0]

    def batch_load_fn(self, keys):
        related_objects_by_parent = defaultdict(list)

        # queryset by related names
        related_name = self.related_name or self.get_related_name(self.parent, self.child)
        reverse_related_name = self.reverse_related_name or self.get_related_name(self.child, self.parent)

        # queryset by custom accessor
        # accessor = self.accessor

        # pre-ready the filtered queryset
        '''
        filtered_qs = self.filterset_class(
            data=self.filter_kwargs,
            request=self.request,
        ).qs.filter(**{
            reverse_related_name: OuterRef(reverse_related_name)
        }).values('id')

        prefetch = Prefetch(
            related_name,
            queryset=self.child.objects.filter(
                id__in=Subquery(
                    filtered_qs
                )
            ).distinct(),
            to_attr='output'
        )

        qs = self.parent.objects.filter(id__in=keys).prefetch_related(
            prefetch
        ).annotate(
            count=Subquery(
                self.child.objects.filter(
                    id__in=Subquery(
                    )
                ),
                output_field=IntegerField()
            )
        )
        '''
        from apps.entry.models import Entry, Figure
        filtered_qs = Figure.objects.filter()
        prefetch = Prefetch(
            'figures',
            queryset=Figure.objects.filter(
                id__in=Subquery(
                    filtered_qs.filter(**{
                        'entry': OuterRef('entry')
                    }).values('id'),
                )
            ).distinct(),
            to_attr='out'
        )

        class SQCount(Subquery):
            template = "(SELECT count(*) FROM (%(subquery)s) _count)"
            output_field = IntegerField()

        qs = Entry.objects.filter(id__in=keys).prefetch_related(
            prefetch
        )

        for each in qs:
            related_objects_by_parent[each.id] = len(each.out)

        return Promise.resolve([
            related_objects_by_parent.get(key, 0) for key in keys
        ])


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
        **kwargs
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

    def get_related_name(self, model1, model2):
        '''
        To be used with models with single relationship in between
        Returns the first relation found

        If multiple relations exists, pass related_name and reverse_related_name explicitly
        '''
        relations = get_relations(model1, model2)
        if relations:
            return relations[0]

    def batch_load_fn(self, keys):
        related_objects_by_parent = defaultdict(list)

        # queryset by related names
        related_name = self.related_name or self.get_related_name(self.parent, self.child)
        reverse_related_name = self.reverse_related_name or self.get_related_name(self.child, self.parent)

        # queryset by custom accessor
        # accessor = self.accessor

        # pre-ready the filtered and paginated queryset
        filtered_qs = self.filterset_class(
            data=self.filter_kwargs,
            request=self.request,
        ).qs.filter(**{
            reverse_related_name: OuterRef(reverse_related_name)
        })
        filtered_paginated_qs = self.pagination.paginate_queryset(
            filtered_qs,
            **self.kwargs
        ).values('id')

        OUT_RELATED_FIELD = 'out_related_field'
        prefetch = Prefetch(
            related_name,
            queryset=self.child.objects.filter(
                id__in=Subquery(
                    filtered_paginated_qs
                )
            ).distinct(),
            to_attr=OUT_RELATED_FIELD,
        )

        qs = self.parent.objects.filter(id__in=keys).prefetch_related(prefetch)

        for each in qs:
            related_objects_by_parent[each.id] = getattr(each, OUT_RELATED_FIELD)

        return Promise.resolve([
            related_objects_by_parent.get(key, []) for key in keys
        ])
