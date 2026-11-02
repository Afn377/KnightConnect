from rest_framework import serializers

from catalog.models import Interest, Role, Skill
from catalog.serializers import CatalogSlugField

from .models import User, UserSkill
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
