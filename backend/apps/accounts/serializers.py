from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "phone",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class POSTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user data to the login response so the frontend doesn't need a second /me/ call."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
