from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import response
from apps.users.models import User
from apps.users.serializers import UserMeSerializer


class MeView(APIView):
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        users = User.objects.all()
        userProfileObj = users.filter(id=request.user.id)
        serializer = UserMeSerializer(userProfileObj, many=True)
        serializer = UserMeSerializer(request.user)
        return response.Response(serializer.data)
