from django.db import transaction
from rest_framework import serializers

from catalog.models import Interest, Role, Skill
from catalog.serializers import CatalogSlugField

from .models import ContactMethod, User, UserSkill
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


class UserSkillSerializer(serializers.ModelSerializer):
    skill = CatalogSlugField(queryset=Skill.objects.all())

    class Meta:
        model = UserSkill
        fields = ["skill", "proficiency"]


class MeSerializer(serializers.ModelSerializer):
    """The signed-in user's own profile."""

    preferred_roles = CatalogSlugField(many=True, queryset=Role.objects.all(), required=False)
    interests = CatalogSlugField(many=True, queryset=Interest.objects.all(), required=False)
    skills = UserSkillSerializer(source="user_skills", many=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "bio",
            "open_to_requests",
            "availability",
            "commitment",
            "preferred_roles",
            "interests",
            "skills",
            "is_profile_complete",
            "created_at",
        ]
        read_only_fields = ["id", "email", "is_profile_complete", "created_at"]

    def validate_skills(self, skills):
        slugs = [entry["skill"].slug for entry in skills]
        if len(slugs) != len(set(slugs)):
            raise serializers.ValidationError("Each skill can only be listed once.")
        return skills

    @transaction.atomic
    def update(self, instance, validated_data):
        skills = validated_data.pop("user_skills", None)
        instance = super().update(instance, validated_data)
        if skills is not None:
            instance.user_skills.all().delete()
            UserSkill.objects.bulk_create(UserSkill(user=instance, **entry) for entry in skills)
        return instance


class ContactMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMethod
        fields = ["id", "kind", "value", "is_preferred"]
