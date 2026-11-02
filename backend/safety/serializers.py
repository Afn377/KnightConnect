from rest_framework import serializers

from accounts.models import User
from opportunities.serializers import OwnerSerializer

from .models import Block


class BlockSerializer(serializers.ModelSerializer):
    user = OwnerSerializer(source="blocked", read_only=True)

    class Meta:
        model = Block
        fields = ["user", "created_at"]


class BlockCreateSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    def validate_user(self, user):
        if user == self.context["request"].user:
            raise serializers.ValidationError("You can't block yourself.")
        return user
