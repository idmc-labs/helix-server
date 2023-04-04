from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from django.db.models import Q
import csv
from django.http import HttpResponse
from apps.country.models import Country
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
                disaster.event_name,
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
