from rest_framework import serializers

from accounts.models import User
from opportunities.serializers import OwnerSerializer

from .models import Block, Report


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


class ReportSerializer(serializers.ModelSerializer):
    reported_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Report
        fields = ["id", "reported_user", "opportunity", "reason", "details", "status"]
        read_only_fields = ["id", "status"]
        extra_kwargs = {"details": {"required": False}}

    def validate(self, attrs):
        reporter = self.context["request"].user
        reported_user = attrs["reported_user"]
        if reported_user == reporter:
            raise serializers.ValidationError({"reported_user": ["You can't report yourself."]})
        opportunity = attrs.get("opportunity")
        if opportunity is not None and opportunity.owner_id != reported_user.id:
            raise serializers.ValidationError(
                {"opportunity": ["This opportunity doesn't belong to the reported user."]}
            )
        return attrs

    def create(self, validated_data):
        return Report.objects.create(reporter=self.context["request"].user, **validated_data)

    def to_representation(self, instance):
        return {"id": str(instance.id), "status": instance.status}
