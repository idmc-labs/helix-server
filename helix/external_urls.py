from django.urls import path
from apps.entry.views import IdusFlatCachedView

urlpatterns = [
    path('idus', IdusFlatCachedView.as_view()),
]
