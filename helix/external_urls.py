from django.urls import path
from apps.entry.views import (
    IdusFlatCachedView,
    IdusAllFlatCachedView,
    IdusAllDisasterCachedView,
)

urlpatterns = [
    path('idus', IdusFlatCachedView.as_view()),
    path('idus-all', IdusAllFlatCachedView.as_view()),
    path('idus-all-disaster', IdusAllDisasterCachedView.as_view()),
]
