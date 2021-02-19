from django.urls import path, include
from rest_framework import routers

from apps.users.views import MeView, UserViewSet
from apps.parking_lot.views import ParkedItemViewSet

router = routers.DefaultRouter()
router.register(r'parking-lot', ParkedItemViewSet, basename='parking-lot')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('me/', MeView.as_view()),
    path('', include(router.urls))
]
