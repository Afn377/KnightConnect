import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
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

    def validate_roles(self, roles):
        if not roles:
            raise serializers.ValidationError("List at least one open role.")
        slugs = [entry["role"].slug for entry in roles]
        if len(slugs) != len(set(slugs)):
            raise serializers.ValidationError("Each role can only be listed once.")
        return roles

    def validate_skills(self, skills):
        slugs = [entry["skill"].slug for entry in skills]
        if len(slugs) != len(set(slugs)):
            raise serializers.ValidationError("Each skill can only be listed once.")
        return skills

    def validate_event(self, event):
        unchanged = self.instance is not None and self.instance.event_id == getattr(event, "pk", None)
        if event is not None and not unchanged and not event.is_recruiting:
            raise serializers.ValidationError("This event is no longer recruiting.")
        return event

    def validate(self, attrs):
        """Apply the model's own validation (expiry window, event deadline) to the result."""
        related = {"interests", "roles", "opportunity_skills"}
        candidate = copy.copy(self.instance) if self.instance else Opportunity()
        for field, value in attrs.items():
            if field not in related:
                setattr(candidate, field, value)
        try:
            candidate.clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.message_dict)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        interests = validated_data.pop("interests", [])
        roles = validated_data.pop("roles")
        skills = validated_data.pop("opportunity_skills", [])

        opportunity = Opportunity.objects.create(owner=self.context["request"].user, **validated_data)
        opportunity.interests.set(interests)
        OpportunityRole.objects.bulk_create(
            OpportunityRole(opportunity=opportunity, **entry) for entry in roles
        )
        OpportunitySkill.objects.bulk_create(
            OpportunitySkill(opportunity=opportunity, **entry) for entry in skills
        )
        return opportunity
