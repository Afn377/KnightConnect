from rest_framework import serializers

from opportunities.serializers import OwnerSerializer

from .models import Block


class BlockSerializer(serializers.ModelSerializer):
    user = OwnerSerializer(source="blocked", read_only=True)

    class Meta:
        model = Block
        fields = ["user", "created_at"]
