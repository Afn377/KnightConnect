from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
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
            "major",
            "year",
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
    """A contact method owned by the signed-in user.

    Marking a method as preferred clears the preference on the user's other
    methods, since only one can be preferred at a time.
    """

    class Meta:
        model = ContactMethod
        fields = ["id", "kind", "value", "is_preferred"]
        # Uniqueness per user is checked in validate(), since the user is not a writable field.
        validators = []

    def validate(self, attrs):
        user = self.context["request"].user
        kind = attrs.get("kind", getattr(self.instance, "kind", None))
        value = attrs.get("value", getattr(self.instance, "value", None))

        if kind == ContactMethod.Kind.EMAIL:
            try:
                validate_email(value)
            except DjangoValidationError:
                raise serializers.ValidationError({"value": ["Enter a valid email address."]})

        duplicates = ContactMethod.objects.filter(user=user, kind=kind)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError(
                {"kind": ["You already have a contact method of this kind."]}
            )
        return attrs

    def _clear_other_preferences(self, user, keep=None):
        others = ContactMethod.objects.filter(user=user, is_preferred=True)
        if keep is not None:
            others = others.exclude(pk=keep.pk)
        others.update(is_preferred=False)

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        if validated_data.get("is_preferred"):
            self._clear_other_preferences(user)
        return ContactMethod.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        if validated_data.get("is_preferred"):
            self._clear_other_preferences(instance.user, keep=instance)
        return super().update(instance, validated_data)


class PublicProfileSerializer(serializers.ModelSerializer):
    """What other students can see. Never includes email or contact methods."""

    preferred_roles = CatalogSlugField(many=True, read_only=True)
    interests = CatalogSlugField(many=True, read_only=True)
    skills = UserSkillSerializer(source="user_skills", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "display_name",
            "major",
            "year",
            "bio",
            "open_to_requests",
            "availability",
            "commitment",
            "preferred_roles",
            "interests",
            "skills",
        ]
        read_only_fields = fields
