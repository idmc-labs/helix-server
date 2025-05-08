from pathlib import Path
from rest_framework import viewsets
from django.db.models import F, When, Case, Value, CharField, Avg, Q, Func
from django.db.models.functions import Concat, Coalesce, ExtractYear, Lower, Cast
from django.contrib.postgres.aggregates.general import StringAgg, ArrayAgg
from django.contrib.postgres.fields import ArrayField
from apps.entry.models import Figure, ExternalApiDump
from apps.entry.serializers import FigureReadOnlySerializer
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import redirect
from apps.common.utils import (
    EXTERNAL_TUPLE_SEPARATOR,
    EXTERNAL_ARRAY_SEPARATOR,
    extract_location_data,
    extract_event_code_data,
)
from apps.gidd.views import client_id
from utils.common import track_gidd
from utils.db import Array
from drf_spectacular.utils import extend_schema, extend_schema_view


def get_idu_data(filters=None):
    base_query = Figure.objects.annotate(
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
        figure_role=F('role'),
        centroid_lat=Avg('geo_locations__lat'),
        centroid_lon=Avg('geo_locations__lon'),
        centroid=Case(
            When(
                centroid_lat__isnull=False,
                then=Concat(
                    Value('['),
                    F('centroid_lat'),
                    Value(EXTERNAL_TUPLE_SEPARATOR),
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
        event_codes=ArrayAgg(
            Array(
                F('event__event_code__event_code'),
                Cast(F('event__event_code__event_code_type'), CharField()),
                output_field=ArrayField(CharField()),
            ),
            distinct=True,
            filter=Q(event__event_code__country__id=F('country__id')),
        ),
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
            When(quantifier=0, then=Lower(Value(Figure.QUANTIFIER.MORE_THAN_OR_EQUAL.label))),
            When(quantifier=1, then=Lower(Value(Figure.QUANTIFIER.LESS_THAN_OR_EQUAL.label))),
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
        sources_name=StringAgg(
            'sources__name', EXTERNAL_ARRAY_SEPARATOR,
            distinct=True, output_field=CharField()
        ),
        entry_url_or_document_url=Case(
            When(entry__document__isnull=False, then=F('entry__document_url')),
            When(entry__document__isnull=True, then=F('entry__url')),
            output_field=CharField()
        ),
        locations=ArrayAgg(
            Array(
                F('geo_locations__display_name'),
                Concat(
                    F('geo_locations__lat'),
                    Value(EXTERNAL_TUPLE_SEPARATOR),
                    F('geo_locations__lon'),
                    output_field=CharField(),
                ),
                Cast('geo_locations__accuracy', CharField()),
                Cast('geo_locations__identifier', CharField()),
                output_field=ArrayField(CharField()),
            ),
            distinct=True,
            filter=~Q(
                Q(geo_locations__display_name__isnull=True) | Q(geo_locations__display_name='')
            ),
        ),
        displacement_occurred_transformed=Case(
            When(displacement_occurred=0, then=Value("Displacement reporting preventive evacuations")),
            When(displacement_occurred__in=[1, 2, 3], then=Value("Displacement without preventive evacuations reported")),
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

    # Apply filters if provided
    if filters:
        base_query = base_query.filter(**filters)

    for figure_data in base_query.values():
        locations_data = figure_data.pop('locations', [])
        location_parse = extract_location_data(locations_data)

        event_codes_data = figure_data.pop('event_codes', [])
        event_code_parse = extract_event_code_data(event_codes_data)

        yield {
            **figure_data,
            'locations_name': location_parse['display_name'],
            'locations_coordinates': location_parse['lat_lon'],
            'locations_accuracy': location_parse['accuracy'],
            'locations_type': location_parse['type_of_points'],
            'event_codes': event_code_parse['code'],
            'event_code_types': event_code_parse['code_type'],
        }


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


@extend_schema_view(
    get=extend_schema(
        description=Path("docs/idus/main-description.md").read_text(),
        responses=FigureReadOnlySerializer,
        tags=['IDU'],
    )
)
class IdusFlatCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS


@extend_schema(
    responses=FigureReadOnlySerializer,
    tags=['IDU'],
)
class IdusAllFlatCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL


@extend_schema(
    responses=FigureReadOnlySerializer,
    tags=['IDU'],
)
class IdusAllDisasterCachedView(ExternalEndpointBaseCachedViewMixin, APIView):
    ENDPOINT_TYPE = ExternalApiDump.ExternalApiType.IDUS_ALL_DISASTER
