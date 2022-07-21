from django.urls import path, include
from rest_framework import routers
from apps.entry.views import FigureViewSet, IdusFlatCachedView


router = routers.DefaultRouter()
router.register(r'idus-figures', FigureViewSet, basename='idu-figures')

urlpatterns = [
    path('idus', IdusFlatCachedView.as_view()),
    path('', include(router.urls)),
]
