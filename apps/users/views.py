from rest_framework.views import APIView
from rest_framework.filters import (
    SearchFilter
)
from rest_framework.permissions import IsAuthenticated
from rest_framework import response, viewsets, mixins

from apps.users.models import User
from apps.users.serializers import UserSerializer


class UserViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        return User.objects.all()


class MeView(APIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return response.Response(serializer.data)
