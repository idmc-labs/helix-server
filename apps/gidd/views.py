import csv
from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from django.db.models import Q
from django.http import HttpResponse

from apps.country.models import Country
from .models import Conflict, Disaster
from .serializers import (
    CountrySerializer,
    ConflictSerializer,
    DisasterSerializer,
)
from .rest_filters import (
    RestConflictFilterSet,
    RestDisasterFilterSet,
)
from utils.common import round_and_remove_zero, track_gidd
from apps.entry.models import ExternalApiDump


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CountrySerializer
    queryset = Country.objects.all()
    lookup_field = 'iso3'
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter)
    filterset_fields = ['id']


class ConflictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConflictSerializer
    queryset = Conflict.objects.all().select_related('country')
    filterset_class = RestConflictFilterSet

    @action(
        detail=False,
        methods=["get"],
        url_path="conflict-export",
        permission_classes=[AllowAny],
    )
    def export(self, request, iso3=None):
        """
        Export conflict
        """
        track_gidd(
            request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_CONFLICT_EXPORT_REST
        )
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

        qs = self.filter_queryset(self.get_queryset()).filter(
            (Q(new_displacement__gt=0) | ~Q(total_displacement=None))
        )
        for conflict in qs:
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


class DisasterViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DisasterSerializer
    queryset = Disaster.objects.all().select_related('country')
    filterset_class = RestDisasterFilterSet

    @action(
        detail=False,
        methods=["get"],
        url_path="disaster-export",
        permission_classes=[AllowAny],
    )
    def export(self, request, iso3=None):
        """
        Export disaster
        """
        qs = self.filter_queryset(self.get_queryset())
        track_gidd(
            request.GET.get('client_id'),
            ExternalApiDump.ExternalApiType.GIDD_DISASTER_EXPORT_REST
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="disaster-data.csv"'
        writer = csv.writer(response, delimiter=',')
        writer.writerow([
            'ISO3', 'Country / Territory', 'Year', 'Event Name', 'Date of Event (start)',
            'Disaster Internal Displacements', 'Hazard Category', 'Hazard Type', 'Hazard Sub Type'
        ])
        for disaster in qs:
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
