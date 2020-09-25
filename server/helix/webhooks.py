from django.urls import path

from apps.entry.views import handle_pdf_generation

urlpatterns = [
    path('/generate_pdf', handle_pdf_generation)
]
