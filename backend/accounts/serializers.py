from rest_framework import serializers

from .models import User
from .validators import validate_rutgers_email


class NormalizedEmailField(serializers.EmailField):
    def to_internal_value(self, data):
        return super().to_internal_value(str(data).strip().lower())


class RequestCodeSerializer(serializers.Serializer):
    email = NormalizedEmailField(validators=[validate_rutgers_email])


class VerifyCodeSerializer(serializers.Serializer):
    email = NormalizedEmailField()
    code = serializers.RegexField(r"^\d{6}$", error_messages={"invalid": "Enter the 6-digit code."})


class SessionUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "display_name", "is_profile_complete"]
