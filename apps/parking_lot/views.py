from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

from apps.parking_lot.models import ParkedItem
from apps.parking_lot.serializers import ParkedItemSerializer


class ParkedItemViewSet(viewsets.ModelViewSet):
    queryset = ParkedItem.objects.all()
    serializer_class = ParkedItemSerializer
    permission_classes = [IsAuthenticated]
