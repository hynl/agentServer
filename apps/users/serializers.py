from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import User

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'first_name',
            'last_name',
            'profile_image',
            'bio',
            'professional_area',
            'date_joined',
        )
        read_only_fields = fields

class UserSelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('password', 'user_permissions', 'groups', 'is_superuser', 'is_staff', 'last_login')
        read_only_fields = ('id', 'date_joined', 'last_login')

