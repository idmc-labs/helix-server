from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets


from apps.parking_lot.models import ParkedItem
from apps.parking_lot.serializers import ParkedItemSerializer


class CreateListMixin():
    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True
        return super().get_serializer(*args, **kwargs)


class ParkedItemViewSet(CreateListMixin, viewsets.ModelViewSet):
    queryset = ParkedItem.objects.all()
    serializer_class = ParkedItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    swagger_schema = None
