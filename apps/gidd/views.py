import csv
import datetime
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from django.db.models import (
    Q, Sum, Case, When, IntegerField, Value,
    F, Subquery, OuterRef
)
from django.contrib.postgres.aggregates import ArrayAgg
from rest_framework.views import APIView
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.country.models import Country
from apps.entry.models import Figure
from apps.event.models import Event
from apps.event.models import Crisis
from .models import Conflict, Disaster
from .serializers import (
    CountrySerializer,
    ConflictSerializer,
    DisasterSerializer,
)
from utils.common import round_and_remove_zero


def export_disasters(request, iso3=None):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="disaster-data.csv"'
    writer = csv.writer(response, delimiter=',')
    writer.writerow([
        'ISO3', 'Country / Territory', 'Year', 'Event Name', 'Date of Event (start)',
        'Disaster Internal Displacements', 'Hazard Category', 'Hazard Type', 'Hazard Sub Type'
    ])
    countries_iso3 = request.GET.get('countries_iso3', None)
    if not countries_iso3:
        disaster_qs = Disaster.objects.filter(country__iso3=iso3, new_displacement__gt=0)
    else:
        countries_iso3_list = countries_iso3.split(',')
        disaster_qs = Disaster.objects.filter(country__iso3__in=countries_iso3_list, new_displacement__gt=0)

    hazard_type = request.GET.get('hazard_type', None)
    start_year = request.GET.get('start_year', None)
    end_year = request.GET.get('end_year', None)
    if start_year:
        disaster_qs = disaster_qs.filter(year__gte=start_year)
    if end_year:
        disaster_qs = disaster_qs.filter(year__lte=end_year)
    if hazard_type:
        if "-" in hazard_type:
            hazard_type_list = [x.strip() for x in hazard_type.split(',')][:-1]
        else:
            hazard_type_list = [hazard_type]
        disaster_qs = disaster_qs.filter(hazard_type__in=hazard_type_list)
    for disaster in disaster_qs:
        writer.writerow(
            [
                disaster.country.iso3,
                disaster.country.name,
                disaster.year,
                disaster.event__name,
                disaster.start_date,
                round_and_remove_zero(disaster.new_displacement),
                disaster.hazard_category,
                disaster.hazard_type,
                disaster.hazard_sub_type,
            ]
        )
    return response


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()
    lookup_field = 'iso3'
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['id']

    @action(
        detail=True,
        methods=["get"],
        url_path="conflict-export",
        permission_classes=[AllowAny],
    )
    def conflict_export(self, request, iso3=None):
        """
        Export conflict
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="conflict-data.csv"'
        writer = csv.writer(response, delimiter=',')
        writer.writerow([
            'ISO3',
            'Country / Territory',
            'Year',
            'Total number of IDPs',
            'Conflict Internal Displacements',
        ])
        conflict_qs = Conflict.objects.filter(
            Q(country__iso3=iso3) & (Q(new_displacement__gt=0) | ~Q(total_displacement=None))
        )
        start_year = request.GET.get('start_year', None)
        end_year = request.GET.get('end_year', None)
        if start_year:
            conflict_qs = conflict_qs.filter(year__gte=start_year)
        if end_year:
            conflict_qs = conflict_qs.filter(year__lte=end_year)
        for conflict in conflict_qs:
            writer.writerow(
                [
                    conflict.country.iso3,
                    conflict.country.name,
                    conflict.year,
                    round_and_remove_zero(conflict.total_displacement),  # Total number of IDPs
                    round_and_remove_zero(conflict.new_displacement),  # Conflict Internal Displacements
                ]
            )
        return response

    @action(
        detail=True,
        methods=["get"],
        url_path="disaster-export",
        permission_classes=[AllowAny],
    )
    def disaster_export(self, request, iso3=None):
        """
        Export disaster
        """
        return export_disasters(request, iso3)

    @action(
        detail=False,
        methods=["get"],
        url_path="multiple-countries-disaster-export",
        permission_classes=[AllowAny],
    )
    def multiple_countries_disaster_export(self, request):
        """
        Export disaster
        """
        return export_disasters(request)


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConflictSerializer
    queryset = Conflict.objects.all().select_related('country')
    lookup_field = 'id'
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['id']


class DisasterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisasterSerializer
    queryset = Disaster.objects.all().select_related('country')
    lookup_field = 'id'
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['id']


class SyncConflictView(APIView):

    def post(self, request):

        def annotate_conflict(qs, year):
            return qs.annotate(
                year=Value(year, output_field=IntegerField()),
            ).values('year', 'country__idmc_short_name', 'country__iso3').annotate(
                total_displacement=Sum(
                    Case(
                        When(
                            category=Figure.FIGURE_CATEGORY_TYPES.IDPS,
                            then=F('total_figures')
                        ),
                        output_field=IntegerField(),
                        default=0
                    )
                ),
                new_displacement=Sum(
                    Case(
                        When(
                            category=Figure.FIGURE_CATEGORY_TYPES.NEW_DISPLACEMENT,
                            then=F('total_figures')
                        ),
                        output_field=IntegerField(),
                        default=0
                    )
                ),
                country=F('country'),
            ).order_by('year')

        # Delete all the conflicts TODO: Find way to update records
        Conflict.objects.all().delete()

        # Delete disasters
        Disaster.objects.all().delete()

        figure_queryset = Figure.objects.filter(
            role=Figure.ROLE.RECOMMENDED
        )
        start_year = 2016
        end_year = 2023
        for year in range(start_year, end_year):
            nd_figure_qs = Figure.filtered_nd_figures(
                qs=figure_queryset,
                start_date=datetime.datetime(year=year, month=1, day=1),
                end_date=datetime.datetime(year=year, month=12, day=31),
            )
            stock_figure_qs = Figure.filtered_idp_figures(
                qs=figure_queryset,
                start_date=datetime.datetime(year=year, month=1, day=1),
                end_date=datetime.datetime(year=year, month=12, day=31),
            )
            conflict_nd_figure_qs = nd_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
            conflict_stock_figure_qs = stock_figure_qs.filter(event__event_type=Crisis.CRISIS_TYPE.CONFLICT)
            conflict_figure_qs = conflict_nd_figure_qs | conflict_stock_figure_qs
            qs = annotate_conflict(Figure.objects.filter(id__in=conflict_figure_qs.values('id')), year)

            # Create new conflict figures
            Conflict.objects.bulk_create(
                [
                    Conflict(
                        country_id=figure['country'],
                        total_displacement=figure['total_displacement'],
                        new_displacement=figure['new_displacement'],
                        year=figure['year'],
                        iso3=figure['country__iso3'],
                        country_name=figure['country__idmc_short_name'],
                    ) for figure in qs
                ]
            )

            # Sync disaster data
            events = Event.objects.annotate(
                **{
                    'new_displacement': Subquery(
                        Figure.filtered_nd_figures(
                            figure_queryset.filter(
                                event=OuterRef('pk'),
                            ),
                            start_date=datetime.datetime(year=year, month=1, day=1),
                            end_date=datetime.datetime(year=year, month=12, day=31),
                        ).order_by().values('event').annotate(
                            _total=Sum('total_figures')
                        ).values('_total')[:1],
                        output_field=IntegerField()
                    ),
                },
                year=Value(year, output_field=IntegerField()),
                hazard_category=F('disaster_category__name'),
                hazard_sub_category=F('disaster_sub_category__name'),
                hazard_type=F('disaster_type__name'),
                hazard_sub_type=F('disaster_sub_type__name'),
                iso3=ArrayAgg('countries__iso3', distinct=True),
                country_names=ArrayAgg('countries__idmc_short_name', distinct=True),
            ).filter(
                new_displacement__isnull=False,
                disaster_category__isnull=False,
                disaster_type__isnull=False
            ).order_by('year').values(
                'year',
                'countries',
                'id',
                'start_date',
                'start_date_accuracy',
                'end_date',
                'end_date_accuracy',
                'hazard_category',
                'hazard_sub_category',
                'hazard_type',
                'hazard_sub_type',
                'new_displacement',
                'iso3',
                'country_names',
            )
            Disaster.objects.bulk_create(
                [
                    Disaster(
                        event_id=item['id'],
                        year=item['year'],
                        start_date=item['start_date'],
                        start_date_accuracy=item['start_date_accuracy'],
                        end_date=item['end_date'],
                        end_date_accuracy=item['end_date_accuracy'],
                        hazard_category=item['hazard_category'],
                        hazard_sub_category=item['hazard_sub_category'],
                        hazard_type=item['hazard_type'],
                        hazard_sub_type=item['hazard_sub_type'],
                        new_displacement=item['new_displacement'],
                        iso3=item['iso3'],
                        country_names=item['country_names'],
                    ) for item in events
                ]
            )
        return Response("Gidd data synced.", status.HTTP_200_OK)
