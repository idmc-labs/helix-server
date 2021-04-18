import django
from django.db.models import Value
from django.db.models.functions import Lower, StrIndex
import django_filters
import graphene
from graphene_django.forms.converter import convert_form_field


def _generate_list_filter_class(inner_type):
    """
    Source: https://github.com/graphql-python/graphene-django/issues/190

    Returns a Filter class that will resolve into a List(`inner_type`) graphene
    type.

    This allows us to do things like use `__in` filters that accept graphene
    lists instead of a comma delimited value string that's interpolated into
    a list by django_filters.BaseCSVFilter (which is used to define
    django_filters.BaseInFilter)
    """

    form_field = type(
        "List{}FormField".format(inner_type.__name__),
        (django.forms.Field,),
        {},
    )
    filter_class = type(
        "{}ListFilter".format(inner_type.__name__),
        (django_filters.Filter,),
        {
            "field_class": form_field,
            "__doc__": (
                "{0}ListFilter is a small extension of a raw django_filters.Filter "
                "that allows us to express graphql List({0}) arguments using FilterSets."
                "Note that the given values are passed directly into queryset filters."
            ).format(inner_type.__name__),
        },
    )
    convert_form_field.register(form_field)(
        lambda x: graphene.List(graphene.NonNull(inner_type))
    )

    return filter_class


StringListFilter = _generate_list_filter_class(graphene.String)
IDListFilter = _generate_list_filter_class(graphene.ID)


class AllowInitialFilterSetMixin:
    # https://django-filter.readthedocs.io/en/stable/guide/tips.html#using-initial-values-as-defaults
    def __init__(self, data=None, *args, **kwargs):
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()

            for name, f in self.base_filters.items():
                initial = f.extra.get('initial')
                if not data.get(name):
                    data[name] = initial

        super().__init__(data, *args, **kwargs)


class NameFilterMixin:
    # NOTE: add a `name` django_filter as follows in the child filters
    # name = django_filters.CharFilter(method='_filter_name')

    def _filter_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.annotate(
            lname=Lower('name')
        ).annotate(
            idx=StrIndex('lname', Value(value.lower()))
        ).filter(idx__gt=0).order_by('idx', 'name')
