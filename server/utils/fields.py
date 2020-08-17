from graphene_django.utils import is_valid_django_model, maybe_queryset
from graphene_django_extras import DjangoListObjectField
from graphene_django_extras.base_types import DjangoListObjectBase
from graphene_django_extras.utils import queryset_factory, get_extra_filters


class DjangoPaginatedListObjectField(DjangoListObjectField):
    def list_resolver(
        self, manager, filterset_class, filtering_args, root, info, **kwargs
    ):
        qs = queryset_factory(manager, info.field_asts, info.fragments, **kwargs)

        filter_kwargs = {k: v for k, v in kwargs.items() if k in filtering_args}

        qs = filterset_class(data=filter_kwargs, queryset=qs, request=info.context).qs

        if root and is_valid_django_model(root._meta.model):
            extra_filters = get_extra_filters(root, manager.model)
            qs = qs.filter(**extra_filters)

        count = qs.count()

        return DjangoListObjectBase(
            count=count,
            results=maybe_queryset(qs),
            results_field_name=self.type._meta.results_field_name,
        )
