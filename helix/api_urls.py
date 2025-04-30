from django.urls import include, path
from rest_framework import routers

from apps.parking_lot.views import ParkedItemViewSet
from apps.users.views import MeView, UserViewSet

router = routers.DefaultRouter()
router.register(r"parking-lot", ParkedItemViewSet, basename="parking-lot")
router.register(r"users", UserViewSet, basename="users")

urlpatterns = [
    path("me/", MeView.as_view()),
    path("", include(router.urls)),
]
