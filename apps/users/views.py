from rest_framework.views import APIView
from rest_framework.filters import (
    SearchFilter
)

from rest_framework.permissions import IsAuthenticated
from rest_framework import response, viewsets, mixins
from apps.users.models import User
from apps.users.serializers import UserMeSerializer, UsersListSerializer


class UserViewSet(mixins.ListModelMixin,
                  viewsets.GenericViewSet):

    serializer_class = UsersListSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = [SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        return User.objects.all()


class MeView(APIView):
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        users = User.objects.all()
        userProfileObj = users.filter(id=request.user.id)
        serializer = UserMeSerializer(userProfileObj, many=True)
        serializer = UserMeSerializer(request.user)
        return response.Response(serializer.data)
