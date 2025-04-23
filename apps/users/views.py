from dj_rest_auth.serializers import UserDetailsSerializer
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from apps.users.models import User
from apps.users.serializers import UserPublicSerializer


# Create your views here.
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]


    def get_serializer_class(self):
        if self.action == 'me':
            return UserDetailsSerializer
        return UserPublicSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request, *args, **kwargs):
        user = self.request.user
        serializer = UserDetailsSerializer(user, context={'request': request})
        return Response(serializer.data)

