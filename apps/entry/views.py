from rest_framework import viewsets
from django.db.models import F, When, Case, Value, CharField, Avg, Q, Func
from django.db.models.functions import Concat, Coalesce, ExtractYear, Lower
from django.contrib.postgres.aggregates.general import StringAgg
from apps.entry.models import Figure
from apps.entry.serializers import FigureReadOnlySerializer
from rest_framework.permissions import AllowAny


class FigureViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FigureReadOnlySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Figure.objects.annotate(
            country_name=F('country__name'),
            iso3=F('country__iso3'),
            centroid_lat=Avg('geo_locations__lat'),
            centroid_lon=Avg('geo_locations__lon'),
            centroid=Case(
                When(
                    centroid_lat__isnull=False,
                    then=Concat(
                        Value('['),
                        F('centroid_lat'),
                        Value(', '),
                        F('centroid_lon'),
                        Value(']'),
                        output_field=CharField()
                    )
                ),
                default=Value('')
            ),
            displacement_start_date=F('start_date'),
            displacement_end_date=F('end_date'),
            displacement_date=Coalesce('end_date', 'start_date'),
            year=Coalesce(ExtractYear('end_date', 'year'), ExtractYear('start_date', 'year')),
            event_name=F('event__name'),
            event_start_date=F('event__start_date'),
            event_end_date=F('event__end_date'),
            disaster_category_name=F('disaster_category__name'),
            disaster_sub_category_name=F('disaster_sub_category__name'),
            disaster_type_name=F('disaster_type__name'),
            disaster_sub_type_name=F('disaster_sub_type__name'),
            figure_term_label=Case(
                When(term=0, then=Lower(Value(Figure.FIGURE_TERMS.EVACUATED.label))),
                When(term=1, then=Lower(Value(Figure.FIGURE_TERMS.DISPLACED.label))),
                When(term=2, then=Lower(Value(Figure.FIGURE_TERMS.FORCED_TO_FLEE.label))),
                When(term=3, then=Lower(Value(Figure.FIGURE_TERMS.RELOCATED.label))),
                When(term=4, then=Lower(Value(Figure.FIGURE_TERMS.SHELTERED.label))),
                When(term=5, then=Lower(Value(Figure.FIGURE_TERMS.IN_RELIEF_CAMP.label))),
                When(term=6, then=Lower(Value(Figure.FIGURE_TERMS.DESTROYED_HOUSING.label))),
                When(term=8, then=Lower(Value(Figure.FIGURE_TERMS.PARTIALLY_DESTROYED_HOUSING.label))),
                When(term=9, then=Lower(Value(Figure.FIGURE_TERMS.UNINHABITABLE_HOUSING.label))),
                When(term=10, then=Lower(Value(Figure.FIGURE_TERMS.HOMELESS.label))),
                When(term=11, then=Lower(Value(Figure.FIGURE_TERMS.RETURNS.label))),
                When(term=12, then=Lower(Value(Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER.label))),
                output_field=CharField()
            ),
            custom_figure_text=Case(
                When(
                    total_figures=1,
                    category=Figure.FIGURE_CATEGORY_TYPES.RETURN.value,
                    then=Concat(
                        F('country__name'),
                        Value(': '),
                        F('total_figures'),
                        Value(' return '),
                        Concat(Value('('), F('figure_term_label'), Value('),')),
                        Value(' '),
                        Func(
                            F('start_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        Value(' - '),
                        Func(
                            F('end_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        output_field=CharField(),
                    )
                ),
                When(
                    (
                        ~Q(total_figures=1) & Q(category=Figure.FIGURE_CATEGORY_TYPES.RETURN.value)
                    ),
                    then=Concat(
                        F('country__name'),
                        Value(': '),
                        F('total_figures'),
                        Value(' returns '),
                        Concat(Value('('), F('figure_term_label'), Value('),')),
                        Value(' '),
                        Func(
                            F('start_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        Value(' - '),
                        Func(
                            F('end_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        output_field=CharField(),
                    )
                ),
                When(
                    (
                        Q(total_figures=1) &
                        ~Q(term=Figure.FIGURE_TERMS.DISPLACED.value)
                    ),
                    then=Concat(
                        F('country__name'),
                        Value(': '),
                        F('total_figures'),
                        Value(' displacement '),
                        Concat(Value('('), F('figure_term_label'), Value('),')),
                        Value(' '),
                        Func(
                            F('start_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        Value(' - '),
                        Func(
                            F('end_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        output_field=CharField(),
                    )
                ),
                When(
                    (
                        ~Q(total_figures=1) &
                        Q(
                            Q(term=Figure.FIGURE_TERMS.DISPLACED.value) |
                            Q(term=Figure.FIGURE_TERMS.MULTIPLE_OR_OTHER.value)
                        )
                    ),
                    then=Concat(
                        F('country__name'),
                        Value(': '),
                        F('total_figures'),
                        Value(' displacements '),
                        Concat(Value('('), F('figure_term_label'), Value('),')),
                        Value(' '),
                        Func(
                            F('start_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        Value(' - '),
                        Func(
                            F('end_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        output_field=CharField(),
                    )
                ),
                When(
                    (
                        ~Q(total_figures=1) &
                        ~Q(term=Figure.FIGURE_TERMS.DISPLACED.value)
                    ),
                    then=Concat(
                        F('country__name'),
                        Value(': '),
                        F('total_figures'),
                        Value(' displacements '),
                        Concat(Value('('), F('figure_term_label'), Value('),')),
                        Value(' '),
                        Func(
                            F('start_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        Value(' - '),
                        Func(
                            F('end_date'),
                            Value('DD Month'),
                            function='to_char',
                            output_field=CharField()
                        ),
                        output_field=CharField(),
                    )
                ),

            ),
            custom_link_text=Concat(
                Value('<a href="'),
                Case(
                    When(entry__url__isnull=False, then=F('entry__url')),
                    When(entry__document_url__isnull=False, then=F('entry__document_url'))
                ),
                Value('"'),
                Value(' target=_blank>'),
                StringAgg('entry__publishers__name', ' ', distinct=True),
                Value(' - '),
                Func(
                    F('entry__created_at'),
                    Value('DD Month YYYY'),
                    function='to_char',
                    output_field=CharField()
                ),
                Value('</a>'),
                output_field=CharField(),
            ),
            standard_popup_text=Concat(
                Value('<b>'),
                F('custom_figure_text'),
                Value('</b> <br>'),
                F('excerpt_idu'),
                Value('<br>'),
                F('custom_link_text'),
                output_field=CharField(),
            ),
            standard_info_text=Concat(
                Value('<b>'),
                F('custom_figure_text'),
                Value('<b>'),
            )
        )
        return queryset
