from rest_framework import serializers

from accounts.models import User
from catalog.models import Event, Interest, Role, Skill
from catalog.serializers import CatalogSlugField

from .models import Opportunity, OpportunityRole, OpportunitySkill


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "display_name"]


class OpportunityRoleSerializer(serializers.ModelSerializer):
    role = CatalogSlugField(queryset=Role.objects.all())
    filled = serializers.SerializerMethodField()

    class Meta:
        model = OpportunityRole
        fields = ["role", "slots", "filled", "notes"]

    def get_filled(self, obj):
        if hasattr(obj, "filled"):
            return obj.filled
        return obj.connection_requests.filter(status="accepted").count() if obj.pk else 0


class OpportunitySkillSerializer(serializers.ModelSerializer):
    skill = CatalogSlugField(queryset=Skill.objects.all())

    class Meta:
        model = OpportunitySkill
        fields = ["skill", "requirement_type"]


class OpportunitySerializer(serializers.ModelSerializer):
    owner = OwnerSerializer(read_only=True)
    event = CatalogSlugField(queryset=Event.objects.all(), allow_null=True, required=False)
    interests = CatalogSlugField(many=True, queryset=Interest.objects.all(), required=False)
    roles = OpportunityRoleSerializer(many=True)
    skills = OpportunitySkillSerializer(source="opportunity_skills", many=True, required=False)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = [
            "id",
            "owner",
            "is_owner",
            "title",
            "description",
            "opportunity_type",
            "event",
            "availability",
            "commitment",
            "interests",
            "roles",
            "skills",
            "status",
            "close_reason",
            "expires_at",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "status", "close_reason", "created_at"]

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and obj.owner_id == request.user.id)
