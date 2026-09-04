from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds a little user context to the token response and blocks soft-deleted users."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["name"] = user.name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.deleted_at is not None:
            raise serializers.ValidationError("This account has been deactivated.")
        data["user"] = UserSerializer(self.user).data
        return data


class UserSerializer(serializers.ModelSerializer):
    personality_id = serializers.PrimaryKeyRelatedField(source="personality", read_only=True)

    class Meta:
        model = User
        fields = ["id", "name", "email", "personality_id", "is_staff", "created_at"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "name", "email", "password"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class TokenPairResponseSerializer(serializers.Serializer):
    """Documents the login response, which adds ``user`` on top of the token pair."""

    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()
