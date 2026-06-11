from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from apps.entry.views import (
    IdusAllDisasterCachedView,
    IdusAllFlatCachedView,
    IdusFlatCachedView,
)
from apps.gidd.views import (
    ConflictViewSet,
    CountryViewSet,
    DisaggregationViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
    PublicFigureAnalysisViewSet,
)


class CustomSwaggerView(SpectacularSwaggerView):
    template_name = "drf_spectular/custom_swagger_ui.html"


router = DefaultRouter()
router.register("countries", CountryViewSet, "countries-view")
router.register("conflicts", ConflictViewSet, "conflicts-view")
router.register("disasters", DisasterViewSet, "diasters-view")
router.register("displacements", DisplacementDataViewSet, "displacements-view")
router.register("public-figure-analyses", PublicFigureAnalysisViewSet, "public-figure-analysis-view-set")

urlpatterns = [
    path(
        "idus/last-180-days/",
        IdusFlatCachedView.as_view(
            {
                "get": "export_json",
            }
        ),
        name="idus-180-json-view",
    ),
    path(
        "idus/last-180-days-excel/",
        IdusFlatCachedView.as_view(
            {
                "get": "export_excel",
            }
        ),
        name="idus-180-excel-view",
    ),
    path(
        "idus/last-180-days-geojson/",
        IdusFlatCachedView.as_view(
            {
                "get": "export_geojson",
            }
        ),
        name="idus-180-geojson-view",
    ),
    path(
        "idus/all/",
        IdusAllFlatCachedView.as_view(
            {
                "get": "export_json",
            }
        ),
        name="idus-json-view",
    ),
    path(
        "idus/all-excel/",
        IdusAllFlatCachedView.as_view(
            {
                "get": "export_excel",
            }
        ),
        name="idus-excel-view",
    ),
    path(
        "idus/all-geojson/",
        IdusAllFlatCachedView.as_view(
            {
                "get": "export_geojson",
            }
        ),
        name="idus-geojson-view",
    ),
    path(
        "idus/all/disaster/",
        IdusAllDisasterCachedView.as_view(
            {
                "get": "export_json",
            }
        ),
        name="idus-json-view",
    ),
    path(
        "idus/all/disaster-excel/",
        IdusAllDisasterCachedView.as_view(
            {
                "get": "export_excel",
            }
        ),
        name="idus-excel-view",
    ),
    path(
        "idus/all/disaster-geojson/",
        IdusAllDisasterCachedView.as_view(
            {
                "get": "export_geojson",
            }
        ),
        name="idus-geojson-view",
    ),
    path("gidd/", include(router.urls)),
    # NOTE: If we do not add these manually, the are not visible in GIDD
    path(
        "gidd/disaggregations/disaggregation-geojson/",
        DisaggregationViewSet.as_view(
            {
                "get": "export_disaggregated_geojson",
            }
        ),
        name="disaggregations-geojson-view",
    ),
    path(
        "gidd/disaggregations/disaggregation-export/",
        DisaggregationViewSet.as_view(
            {
                "get": "export_disaggregated",
            }
        ),
        name="disaggregations-export-view",
    ),
    # OpenAPI
    path("api-schema/", SpectacularAPIView.as_view(), name="schema"),
    path("", CustomSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
