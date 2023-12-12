import typing
import graphene
import django_filters
from functools import partial
from django import forms
from django.db.models.functions import Lower, StrIndex
from django.db.models import Value
from django.db.models.query import QuerySet
from graphene.types.generic import GenericScalar
from graphene_django.forms.converter import convert_form_field
from graphene_django.filter.utils import get_filtering_args_from_filterset

from utils.mutation import generate_object_field_from_input_type, compare_input_output_type_fields


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    field_class = forms.IntegerField


class DjangoFilterCSVWidget(django_filters.widgets.CSVWidget):
    def value_from_datadict(self, data, files, name):
        value = forms.Widget.value_from_datadict(self, data, files, name)

        if value is not None:
            if value == '':  # parse empty value as an empty list
                return []
            # if value is already list(by POST)
            elif isinstance(value, list) or isinstance(value, QuerySet):
                return value
            elif isinstance(value, str):
                return [x.strip() for x in value.strip().split(',') if x.strip()]
            raise Exception(f'Unknown value type {type(value)}')
        return None


def _generate_filter_class(inner_type, filter_type=None, non_null=False):
    _filter_type = filter_type or django_filters.Filter
    form_field = type(
        "{}FormField".format(inner_type.__name__),
        (_filter_type.field_class,),
        {},
    )
    filter_class = type(
        "{}Filter".format(inner_type.__name__),
        (_filter_type,),
        {
            "field_class": form_field,
            "__doc__": (
                "{0}Filter is a small extension of a raw {1} "
                "that allows us to express graphql ({0}) arguments using FilterSets."
                "Note that the given values are passed directly into queryset filters."
            ).format(inner_type.__name__, _filter_type),
        },
    )
    convert_form_field.register(form_field)(
        lambda _: graphene.NonNull(inner_type) if non_null else inner_type()
    )

    return filter_class


def _generate_list_filter_class(inner_type, filter_type=None, field_class=None):
    """
    Source: https://github.com/graphql-python/graphene-django/issues/190

    Returns a Filter class that will resolve into a List(`inner_type`) graphene
    type.

    This allows us to do things like use `__in` filters that accept graphene
    lists instead of a comma delimited value string that's interpolated into
    a list by django_filters.BaseCSVFilter (which is used to define
    django_filters.BaseInFilter)
    """

    _filter_type = filter_type or django_filters.Filter
    _field_class = field_class or _filter_type.field_class
    form_field = type(
        "List{}FormField".format(inner_type.__name__),
        (_field_class,),
        {},
    )
    filter_class = type(
        "{}ListFilter".format(inner_type.__name__),
        (_filter_type,),
        {
            "field_class": form_field,
            "__doc__": (
                "{0}ListFilter is a small extension of a raw {1} "
                "that allows us to express graphql List({0}) arguments using FilterSets."
                "Note that the given values are passed directly into queryset filters."
            ).format(inner_type.__name__, _filter_type),
        },
    )
    convert_form_field.register(form_field)(
        lambda _: graphene.List(graphene.NonNull(inner_type))
    )

    return filter_class


def _get_simple_input_filter(_type, **kwargs):
    return _generate_filter_class(_type)(**kwargs)


def _get_multiple_input_filter(_type, **kwargs):
    return _generate_list_filter_class(
        _type,
        filter_type=django_filters.MultipleChoiceFilter,
        # TODO: Hack, not sure why django_filters.MultipleChoiceFilter.field_class doesn't work
        field_class=django_filters.Filter.field_class,
    )(**kwargs)


def generate_type_for_filter_set(
    filter_set,
    used_node,
    type_name,
    input_type_name,
    custom_new_fields_map=None,
) -> typing.Tuple[graphene.ObjectType, graphene.InputObjectType]:
    """
    For given filter_set eg: LeadGqlFilterSet
    It returns:
        - LeadGqlFilterSetInputType
        - LeadGqlFilterSetType
    """
    def generate_type_from_input_type(input_type):
        new_fields_map = generate_object_field_from_input_type(input_type)
        if custom_new_fields_map:
            new_fields_map.update(custom_new_fields_map)
        new_type = type(type_name, (graphene.ObjectType,), new_fields_map)
        compare_input_output_type_fields(input_type, new_type)
        return new_type

    input_type = type(
        input_type_name,
        (graphene.InputObjectType,),
        get_filtering_args_from_filterset(filter_set, used_node)
    )
    _type = generate_type_from_input_type(input_type)
    return _type, input_type


SimpleInputFilter = _get_simple_input_filter
MultipleInputFilter = _get_multiple_input_filter

IDFilter = _generate_filter_class(
    graphene.ID,
    filter_type=django_filters.NumberFilter,
)

# Generic Filters
IDListFilter = _generate_list_filter_class(graphene.ID)

StringListFilter: MultipleInputFilter = _generate_list_filter_class(graphene.String)
GenericFilter = _generate_filter_class(GenericScalar)

DateTimeFilter = partial(
    django_filters.DateTimeFilter,
    input_formats=[django_filters.fields.IsoDateTimeField.ISO_8601],
)
DateTimeGteFilter = partial(
    django_filters.DateTimeFilter,
    lookup_expr='gte',
    input_formats=[django_filters.fields.IsoDateTimeField.ISO_8601],
)
DateTimeLteFilter = partial(
    django_filters.DateTimeFilter,
    lookup_expr='lte',
    input_formats=[django_filters.fields.IsoDateTimeField.ISO_8601],
)

DateGteFilter = partial(django_filters.DateFilter, lookup_expr='gte')
DateLteFilter = partial(django_filters.DateFilter, lookup_expr='lte')


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
