import re
import typing
import unicodedata
from functools import partial

import django_filters
import graphene
from django import forms
from django.db.models import Func, Model, Q
from django.db.models.query import QuerySet
from django_filters import rest_framework as df
from graphene.types.generic import GenericScalar
from graphene_django.filter.utils import get_filtering_args_from_filterset
from graphene_django.forms.converter import convert_form_field

from utils.mutation import compare_input_output_type_fields, generate_object_field_from_input_type


class Unaccent(Func):
    function = "unaccent"
    arity = 1


class MultiWordSearchFilterSet(df.FilterSet):
    """
    Search baseclass to implement multi-word query logic to any FilterSet.
    """

    search = django_filters.CharFilter(method="multi_word_search")

    @property
    def searchable_fields(self) -> typing.List[str]:
        """
        Defines the fields to be included in the multi_word_search logic in Meta.multi_word_search_fields.
        """

        return getattr(self.Meta, "multi_word_search_fields", [])  # type:ignore child class has a Meta

    def traverse_field_path(
        self,
        model: typing.Type[Model],
        field_path: str,
    ):
        """
        Checks a Django model field's relation such as:
        - "model_field", e.g. "name"
        - "related__model_field", e.g. "crisis__name"
        - "related__model_related_field", e.g. "crisis__countries__name"
        """
        parts = field_path.split("__")

        for part in parts:
            field = model._meta.get_field(part)

            yield field

            # Move to the related model if this field is a relation
            if field.is_relation:
                model = typing.cast(typing.Type[Model], field.related_model)

    def search_should_be_distinct(self, field_names: typing.List[str]) -> bool:
        model = self.Meta.model  # type: ignore child has always a Meta

        return any(
            field.is_relation and (field.many_to_many or field.one_to_many)
            for field_name in field_names
            for field in self.traverse_field_path(model, field_name)
        )

    @staticmethod
    def normalize_search_value(value: str) -> str:
        # For uniformity between application and the backend
        # https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize
        value = unicodedata.normalize("NFKC", value)
        # NOTE: Do we need stemming?

        # Removes special characters except underscore
        value = re.sub(r"[^\w\s]", " ", value)
        # Collapse multiple spaces into one
        value = re.sub(r"\s+", " ", value)

        return value.strip().lower()

    def apply_search_filter(self, queryset: QuerySet, query_terms: typing.Set[str], distinct: bool):
        filter_condition = Q()
        for term in query_terms:
            search_term_filter_condition = Q()
            for field in self.searchable_fields:
                lookup = f"{field}__unaccent__icontains"
                # check in every searchable fields
                search_term_filter_condition |= Q(**{lookup: term})
            # check multiple terms in the searchable fields
            filter_condition &= search_term_filter_condition

        queryset = queryset.filter(filter_condition)
        if distinct:
            queryset = queryset.distinct()

        return queryset

    def multi_word_search(self, queryset: QuerySet, name, search_query: str) -> QuerySet:
        if not search_query or not self.searchable_fields:
            return queryset

        normalized_search_query = self.normalize_search_value(search_query)

        search_query_terms = set(normalized_search_query.split())

        results_should_be_distinct = self.search_should_be_distinct(self.searchable_fields)

        queryset = self.apply_search_filter(queryset, search_query_terms, results_should_be_distinct)

        return queryset


class NumberInFilter(django_filters.BaseInFilter, django_filters.NumberFilter):
    field_class = forms.IntegerField


class DjangoFilterCSVWidget(django_filters.widgets.CSVWidget):
    def value_from_datadict(self, data, files, name):
        value = forms.Widget.value_from_datadict(self, data, files, name)

        if value is not None:
            if value == "":  # parse empty value as an empty list
                return []
            # if value is already list(by POST)
            elif isinstance(value, list) or isinstance(value, QuerySet):
                return value
            elif isinstance(value, str):
                return [x.strip() for x in value.strip().split(",") if x.strip()]
            raise Exception(f"Unknown value type {type(value)}")
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
    convert_form_field.register(form_field)(lambda _: graphene.NonNull(inner_type) if non_null else inner_type())

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
    convert_form_field.register(form_field)(lambda _: graphene.List(graphene.NonNull(inner_type)))

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
    if filter_set in generate_type_for_filter_set.cache:
        return generate_type_for_filter_set.cache[filter_set]

    def generate_type_from_input_type(input_type):
        new_fields_map = generate_object_field_from_input_type(input_type)
        if custom_new_fields_map:
            new_fields_map.update(custom_new_fields_map)
        new_type = type(type_name, (graphene.ObjectType,), new_fields_map)
        compare_input_output_type_fields(input_type, new_type)
        return new_type

    input_type = type(input_type_name, (graphene.InputObjectType,), get_filtering_args_from_filterset(filter_set, used_node))
    _type = generate_type_from_input_type(input_type)
    generate_type_for_filter_set.cache[filter_set] = (_type, input_type)
    return _type, input_type


generate_type_for_filter_set.cache = {}

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
    lookup_expr="gte",
    input_formats=[django_filters.fields.IsoDateTimeField.ISO_8601],
)
DateTimeLteFilter = partial(
    django_filters.DateTimeFilter,
    lookup_expr="lte",
    input_formats=[django_filters.fields.IsoDateTimeField.ISO_8601],
)

DateGteFilter = partial(django_filters.DateFilter, lookup_expr="gte")
DateLteFilter = partial(django_filters.DateFilter, lookup_expr="lte")
