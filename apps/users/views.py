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
    # NOTE: In IDU Map currently none paginated api is used, Set pagination simultaneously
    pagination_class = None
    swagger_schema = None

    def get_queryset(self):
        return User.objects.all()


class MeView(APIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, ]
    swagger_schema = None

    def get(self, request):
        serializer = UserSerializer(request.user)
        return response.Response(serializer.data)
