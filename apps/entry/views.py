from rest_framework import viewsets
from django.db.models import F, When, Case, Value, CharField, Avg, Q, Func
from django.db.models.functions import Concat, Coalesce, ExtractYear, Lower
from django.contrib.postgres.aggregates.general import StringAgg
from apps.entry.models import Figure, ExternalApiDump
from apps.entry.serializers import FigureReadOnlySerializer
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect

from apps.gidd.views import client_id
from utils.common import track_gidd


def get_idu_data():
    return Figure.objects.annotate(
        displacement_date=Coalesce('end_date', 'start_date'),
    ).filter(
        category__in=[
            Figure.FIGURE_CATEGORY_TYPES.RETURNEES.value,
            Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT.value,
            Figure.FIGURE_CATEGORY_TYPES.CROSS_BORDER_RETURN.value,
            Figure.FIGURE_CATEGORY_TYPES.FAILED_RETURN_RETURNEE_DISPLACEMENT.value,
        ],
        excerpt_idu__isnull=False,
        include_idu=True,
        entry__is_confidential=False
    ).filter(
        ~(Q(entry__document_url__isnull=True) | Q(entry__document_url='')) |
        ~(Q(entry__url__isnull=True) | Q(entry__url=''))
    ).annotate(
        country_name=F('country__idmc_short_name'),
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
        year=Coalesce(ExtractYear('start_date', 'year'), ExtractYear('end_date', 'year')),
        event_name=F('event__name'),
        event_start_date=F('event__start_date'),
        event_end_date=F('event__end_date'),
        disaster_category_name=F('disaster_category__name'),
        disaster_sub_category_name=F('disaster_sub_category__name'),
        disaster_type_name=F('disaster_sub_type__type__name'),
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
        quantifier_label=Case(
            When(quantifier=0, then=Lower(Value(Figure.QUANTIFIER.MORE_THAN.label))),
            When(quantifier=1, then=Lower(Value(Figure.QUANTIFIER.LESS_THAN.label))),
            When(quantifier=2, then=Value('total')),
            When(quantifier=3, then=Lower(Value(Figure.QUANTIFIER.APPROXIMATELY.label))),
            output_field=CharField()
        ),
        total_figures_text=Func(
            F('total_figures'),
            Value('999G999G999G990D'),
            function='to_char',
            output_field=CharField()
        ),
        custom_figure_text=Case(
            When(
                total_figures=1,
                category=Figure.FIGURE_CATEGORY_TYPES.RETURN.value,
                then=Concat(
                    F('country__idmc_short_name'),
                    Value(': '),
                    F('total_figures_text'),
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
                    F('country__idmc_short_name'),
                    Value(': '),
                    F('total_figures_text'),
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
                    F('country__idmc_short_name'),
                    Value(': '),
                    F('total_figures_text'),
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
                    F('country__idmc_short_name'),
                    Value(': '),
                    F('total_figures_text'),
                    Value(' displacements, '),
                    # THIS may be problematic
                    # Concat(Value('('), F('figure_term_label'), Value('),')),
                    # Value(' '),
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
                    F('country__idmc_short_name'),
                    Value(': '),
                    F('total_figures_text'),
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
            Value('target="_blank">'),
            StringAgg('entry__publishers__name', ' ', distinct=True),
            Value(' - '),
            Func(
                F('entry__publish_date'),
                Value('DD Month YYYY'),
                function='to_char',
                output_field=CharField()
            ),
            Value('</a>'),
            output_field=CharField(),
        ),
        standard_popup_text=Concat(
            Value('<b> '),
            F('custom_figure_text'),
            Value(' </b> <br> '),
            F('excerpt_idu'),
            Value(' <br> '),
            F('custom_link_text'),
            output_field=CharField(),
        ),
        standard_info_text=Concat(
            Value('<b> '),
            F('custom_figure_text'),
            Value(' </b>'),
        )
    ).order_by('-start_date', '-end_date')


class FigureViewSet(viewsets.ReadOnlyModelViewSet):
    # TODO Add url for this viewset
    serializer_class = FigureReadOnlySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return get_idu_data()


class ExternalEndpointBaseCachedViewMixin():
    ENDPOINT_TYPE = None

    @client_id
    def get(self, request):
        # Check if request is comming from valid client
        client_id = request.GET.get('client_id', None)
        # Track client
        track_gidd(
            client_id,
            self.ENDPOINT_TYPE,
        )
        api_dump = ExternalApiDump.objects.filter(api_type=self.ENDPOINT_TYPE).first()
        # NOTE: Sending empty array so client don't break.
        _empty_response = []
        if not api_dump:
            return Response(_empty_response, status=status.HTTP_404_NOT_FOUND)
        if api_dump.status == ExternalApiDump.Status.COMPLETED:
            return redirect(
                request.build_absolute_uri(
                    api_dump.dump_file.url,
                )
            )
        if api_dump.status == ExternalApiDump.Status.FAILED:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Finally, for pending. If we have a dump send it
        if api_dump.dump_file.name is not None:
            return redirect(
                request.build_absolute_uri(
                    api_dump.dump_file.url,
                )
            )

        # Else send 202 response
        return Response(_empty_response, status=status.HTTP_202_ACCEPTED)


class IdusFlatCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS


class IdusAllFlatCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL


class IdusAllDisasterCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL_DISASTER
