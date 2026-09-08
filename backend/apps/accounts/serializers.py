from django.contrib.auth.password_validation import validate_password
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
            "must_change_password",
            "last_login",
            "created_at",
        ]
        read_only_fields = ["id", "last_login", "created_at"]


class POSTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user data to the login response so the frontend doesn't need a second /me/ call."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


# ── Staff management ───────────────────────────────────────────────────────


class CreateUserSerializer(serializers.ModelSerializer):
    """
    Owner creates a staff account and hands over a temporary password.

    The password is set here rather than emailed because this shop has no mail
    server and the owner is standing next to the person. `must_change_password`
    then forces them to pick their own, so the owner does not keep knowing it.
    """

    password = serializers.CharField(write_only=True, min_length=8)
    # Declared without the model's unique validator so the check below runs
    # instead — it is case-insensitive, and says something a person can act on.
    email = serializers.EmailField(validators=[])

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "phone", "password"]

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Someone already uses that email.")
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated):
        password = validated.pop("password")
        email = validated["email"]
        user = User(
            username=email,          # USERNAME_FIELD is email; username must be unique
            must_change_password=True,
            **validated,
        )
        user.set_password(password)
        user.save()
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    """Change who someone is and what they may do — never their password."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "phone", "is_active"]


class SetPasswordSerializer(serializers.Serializer):
    """An owner resetting somebody else's forgotten password."""

    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value


class ChangeOwnPasswordSerializer(serializers.Serializer):
    """A user changing their own — which requires proving they know the old one."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("That is not your current password.")
        return value

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value

    def validate(self, attrs):
        if attrs["current_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "Choose a password you have not used here before."}
            )
        return attrs
