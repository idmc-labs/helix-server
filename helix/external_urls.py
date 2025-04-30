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

router = DefaultRouter()
router.register("countries", CountryViewSet, "countries-view")
router.register("conflicts", ConflictViewSet, "conflicts-view")
router.register("disasters", DisasterViewSet, "diasters-view")
router.register("displacements", DisplacementDataViewSet, "displacements-view")
router.register("public-figure-analyses", PublicFigureAnalysisViewSet, "public-figure-analysis-view-set")

urlpatterns = [
    path("idus/last-180-days/", IdusFlatCachedView.as_view()),
    path("idus/all/", IdusAllFlatCachedView.as_view()),
    path("idus/all/disaster/", IdusAllDisasterCachedView.as_view()),
    path("gidd/", include(router.urls)),
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
    path("", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
