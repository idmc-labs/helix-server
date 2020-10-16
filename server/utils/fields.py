from collections import OrderedDict

from django.db.models import QuerySet
from graphene import Field, Int, Argument, ID
from graphene_django.filter.utils import get_filtering_args_from_filterset
from graphene_django.utils import is_valid_django_model, maybe_queryset, DJANGO_FILTER_INSTALLED
from graphene_django_extras import DjangoListObjectField, DjangoListObjectType, DjangoObjectType, \
    DjangoFilterPaginateListField, DjangoFilterListField
from graphene_django_extras.base_types import DjangoListObjectBase, factory_type
from graphene_django_extras.fields import DjangoListField
from graphene_django_extras.filters.filter import get_filterset_class
from graphene_django_extras.paginations.pagination import BaseDjangoGraphqlPagination
from graphene_django_extras.registry import get_global_registry
from graphene_django_extras.settings import graphql_api_settings
from graphene_django_extras.types import DjangoObjectOptions
from graphene_django_extras.utils import get_extra_filters


class CustomDjangoListObjectBase(DjangoListObjectBase):
    def __init__(self, results, count, page, pageSize, results_field_name="results"):
        self.results = results
        self.count = count
        self.results_field_name = results_field_name
        self.page = page
        self.pageSize = pageSize

    def to_dict(self):
        return {
            self.results_field_name: [e.to_dict() for e in self.results],
            "count": self.count,
            "page": self.page,
            "pageSize": self.pageSize
        }


class CustomDjangoListField(DjangoListField):
    @staticmethod
    def list_resolver(
            django_object_type, resolver, default_queryset, root, info, **args
    ):
        queryset = maybe_queryset(resolver(root, info, **args))
        if queryset is None:
            queryset = default_queryset

        if isinstance(queryset, QuerySet):
            if hasattr(django_object_type, 'get_queryset'):
                # Pass queryset to the DjangoObjectType get_queryset method
                queryset = maybe_queryset(django_object_type.get_queryset(queryset, info))
        return queryset


class CustomDjangoListObjectType(DjangoListObjectType):
    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls,
        model=None,
        registry=None,
        results_field_name=None,
        pagination=None,
        only_fields=(),
        exclude_fields=(),
        filter_fields=None,
        queryset=None,
        filterset_class=None,
        **options,
    ):

        assert is_valid_django_model(model), (
            'You need to pass a valid Django Model in {}.Meta, received "{}".'
        ).format(cls.__name__, model)

        assert pagination is None, (
            'Pagination should be applied on the ListField enclosing {0} rather than its `{0}.Meta`.'
        ).format(cls.__name__)

        if not DJANGO_FILTER_INSTALLED and filter_fields:
            raise Exception("Can only set filter_fields if Django-Filter is installed")

        assert isinstance(queryset, QuerySet) or queryset is None, (
            "The attribute queryset in {} needs to be an instance of "
            'Django model queryset, received "{}".'
        ).format(cls.__name__, queryset)

        results_field_name = results_field_name or "results"

        baseType = get_global_registry().get_type_for_model(model)

        if not baseType:
            factory_kwargs = {
                "model": model,
                "only_fields": only_fields,
                "exclude_fields": exclude_fields,
                "filter_fields": filter_fields,
                "filterset_class": filterset_class,
                "pagination": pagination,
                "queryset": queryset,
                "registry": registry,
                "skip_registry": False,
            }
            baseType = factory_type("output", DjangoObjectType, **factory_kwargs)

        filter_fields = filter_fields or baseType._meta.filter_fields

        """
        if pagination:
            result_container = pagination.get_pagination_field(baseType)
        else:
            global_paginator = graphql_api_settings.DEFAULT_PAGINATION_CLASS
            if global_paginator:
                assert issubclass(global_paginator, BaseDjangoGraphqlPagination), (
                    'You need to pass a valid DjangoGraphqlPagination class in {}.Meta, received "{}".'
                ).format(cls.__name__, global_paginator)

                global_paginator = global_paginator()
                result_container = global_paginator.get_pagination_field(baseType)
            else:
        """
        result_container = CustomDjangoListField(baseType)

        _meta = DjangoObjectOptions(cls)
        _meta.model = model
        _meta.queryset = queryset
        _meta.baseType = baseType
        _meta.results_field_name = results_field_name
        _meta.filter_fields = filter_fields
        _meta.exclude_fields = exclude_fields
        _meta.only_fields = only_fields
        _meta.filterset_class = filterset_class
        _meta.fields = OrderedDict(
            [
                (results_field_name, result_container),
                (
                    "count",
                    Field(
                        Int,
                        name="totalCount",
                        description="Total count of matches elements",
                    ),
                ),
                (
                    "page",
                    Field(
                        Int,
                        name="page",
                        description="Page Number",
                    ),
                ),
                (
                    "pageSize",
                    Field(
                        Int,
                        name="pageSize",
                        description="Page Size",
                    ),
                )
            ]
        )

        super(DjangoListObjectType, cls).__init_subclass_with_meta__(
            _meta=_meta, **options
        )


class DjangoPaginatedListObjectField(DjangoFilterPaginateListField):
    def __init__(
        self,
        _type,
        pagination=None,
        fields=None,
        extra_filter_meta=None,
        filterset_class=None,
        *args,
        **kwargs,
    ):

        _fields = _type._meta.filter_fields
        _model = _type._meta.model

        self.fields = fields or _fields
        meta = dict(model=_model, fields=self.fields)
        if extra_filter_meta:
            meta.update(extra_filter_meta)

        filterset_class = filterset_class or _type._meta.filterset_class
        self.filterset_class = get_filterset_class(filterset_class, **meta)
        self.filtering_args = get_filtering_args_from_filterset(
            self.filterset_class, _type
        )
        kwargs.setdefault("args", {})
        kwargs["args"].update(self.filtering_args)

        """
        # filtering by primary key or id seems unnecessary...
        if "id" not in kwargs["args"].keys():
            self.filtering_args.update(
                {
                    "id": Argument(
                        ID, description="Django object unique identification field"
                    )
                }
            )
            kwargs["args"].update(
                {
                    "id": Argument(
                        ID, description="Django object unique identification field"
                    )
                }
            )
        """

        pagination = pagination or graphql_api_settings.DEFAULT_PAGINATION_CLASS()

        if pagination is not None:
            assert isinstance(pagination, BaseDjangoGraphqlPagination), (
                'You need to pass a valid DjangoGraphqlPagination in DjangoFilterPaginateListField, received "{}".'
            ).format(pagination)

            pagination_kwargs = pagination.to_graphql_fields()

            self.pagination = pagination
            kwargs.update(**pagination_kwargs)

        if not kwargs.get("description", None):
            kwargs["description"] = "{} list".format(_type._meta.model.__name__)

        # accessor will be used with m2m or reverse_fk fields
        self.accessor = kwargs.pop('accessor', None)
        super(DjangoFilterPaginateListField, self).__init__(
            _type, *args, **kwargs
        )

    def list_resolver(
            self, manager, filterset_class, filtering_args, root, info, **kwargs
    ):

        filter_kwargs = {k: v for k, v in kwargs.items() if k in filtering_args}
        if self.accessor:
            qs = getattr(root, self.accessor).all()
            qs = filterset_class(data=filter_kwargs, queryset=qs, request=info.context).qs
        else:
            qs = self.get_queryset(manager, info, **kwargs)
            qs = filterset_class(data=filter_kwargs, queryset=qs, request=info.context).qs
            if root and is_valid_django_model(root._meta.model):
                extra_filters = get_extra_filters(root, manager.model)
                qs = qs.filter(**extra_filters)
        count = qs.count()

        if getattr(self, "pagination", None):
            qs = self.pagination.paginate_queryset(qs, **kwargs)

        return CustomDjangoListObjectBase(
            count=count,
            results=maybe_queryset(qs),
            results_field_name=self.type._meta.results_field_name,
            page=kwargs.get('page', 1),
            pageSize=kwargs.get('pageSize', graphql_api_settings.DEFAULT_PAGE_SIZE)
        )
