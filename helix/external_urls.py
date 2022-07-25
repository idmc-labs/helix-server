from django.urls import path
from apps.entry.views import IdusFlatCachedView
from apps.entry.views import IdusAllFlatCachedView

urlpatterns = [
    path('idus', IdusFlatCachedView.as_view()),
    path('idus-all', IdusAllFlatCachedView.as_view()),
]
