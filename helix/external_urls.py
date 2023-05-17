from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.entry.views import (
    IdusFlatCachedView,
    IdusAllFlatCachedView,
    IdusAllDisasterCachedView,
)
from apps.gidd.views import (
    CountryViewSet,
    ConflictViewSet,
    DisasterViewSet,
    DisplacementDataViewSet,
    PublicFigureAnalysisViewSet,
)

schema_view = get_schema_view(
    openapi.Info(
        title="GIDD Open API",
        default_version='v1',
        description="Public REST endpoints",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="dev@togglecorp.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

router = DefaultRouter()
router.register("countries", CountryViewSet, "countries-view")
router.register("conflicts", ConflictViewSet, "conflicts-view")
router.register("disasters", DisasterViewSet, "diasters-view")
router.register("displacements", DisplacementDataViewSet, "displacements-view")
router.register("public-figure-analysis", PublicFigureAnalysisViewSet, "public-figure-analysis-view-set")

urlpatterns = [
    path('idus/last-180-days/', IdusFlatCachedView.as_view()),
    path('idus/all/', IdusAllFlatCachedView.as_view()),
    path('idus/all/disaster/', IdusAllDisasterCachedView.as_view()),
    path('gidd/', include(router.urls)),
    path('', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]
