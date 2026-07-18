from typing import Any

from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User


# Create a new user serializer
class UserCreateSerializer(serializers.ModelSerializer[User]):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User  # pyright: ignore[reportAssignmentType, reportIncompatibleVariableOverride]
        fields = ['first_name', 'last_name', 'email', 'password', 'password2']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError("Passwords must match")
        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        validated_data.pop('password2')
        password = validated_data.pop("password")

        return User.objects.create_user(password=password, **validated_data)


# Serializer for retrieving user details
class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User  # pyright: ignore[reportAssignmentType, reportIncompatibleVariableOverride]
        fields = ['id', 'email', 'first_name', 'last_name']


# Serializer for updating user details
class UserUpdateSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User  # pyright: ignore[reportAssignmentType, reportIncompatibleVariableOverride]
        fields = ['first_name', 'last_name', 'email']


# Serializer for changing password
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user

        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError("Old password is incorrect")

        return attrs


# Serializer for logging out and blacklisting the refresh token
class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception:
            self.fail("bad_token")
