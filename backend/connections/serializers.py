from rest_framework import serializers

from accounts.models import User
from catalog.serializers import CatalogSlugField
from opportunities.models import Opportunity, OpportunityRole
from opportunities.queries import browsable_by
from opportunities.serializers import OwnerSerializer

from .contact import shared_contact_methods
from .models import ConnectionFeedback, ConnectionRequest


class RequestOpportunitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Opportunity
        fields = ["id", "title", "status"]


class ConnectionRequestSerializer(serializers.ModelSerializer):
    """A connection request as seen by one of its two participants.

    The other participant's contact methods are included only once the
    request has been accepted.
    """

    opportunity = serializers.SerializerMethodField()
    role = CatalogSlugField(source="opportunity_role.role", read_only=True, default=None)
    sender = OwnerSerializer(read_only=True)
    recipient = OwnerSerializer(read_only=True)
    direction = serializers.SerializerMethodField()
    contact_methods = serializers.SerializerMethodField()
    my_feedback = serializers.SerializerMethodField()
    fit = serializers.SerializerMethodField()

    class Meta:
        model = ConnectionRequest
        fields = [
            "id",
            "kind",
            "status",
            "direction",
            "opportunity",
            "role",
            "sender",
            "recipient",
            "message",
            "contact_methods",
            "my_feedback",
            "fit",
            "created_at",
            "responded_at",
        ]
        read_only_fields = fields

    def get_opportunity(self, obj):
        if obj.opportunity is None:
            return {"id": None, "title": obj.opportunity_title, "status": "deleted"}
        return RequestOpportunitySerializer(obj.opportunity).data

    def _viewer(self):
        return self.context["request"].user

    def get_direction(self, obj):
        return "outgoing" if obj.sender_id == self._viewer().id else "incoming"

    def get_contact_methods(self, obj):
        if obj.status != ConnectionRequest.Status.ACCEPTED:
            return None
        other = obj.recipient if obj.sender_id == self._viewer().id else obj.sender
        return shared_contact_methods(other)


    def get_fit(self, obj):
        """Why the candidate and the post may suit each other, as matching explanation factors."""
        from matching.engine import profile_for, requirements_for, score

        if obj.opportunity is None:
            return []
        _, factors = score(requirements_for(obj.opportunity), profile_for(obj.candidate))
        return [factor.as_dict() for factor in factors]

    def get_my_feedback(self, obj):
        feedback = next((item for item in obj.feedback.all() if item.user_id == self._viewer().id), None)
        if feedback is None:
            return None
        return {"was_useful": feedback.was_useful, "comment": feedback.comment}


class ConnectionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectionFeedback
        fields = ["was_useful", "comment", "created_at"]
        read_only_fields = ["created_at"]
        extra_kwargs = {"comment": {"required": False}}


class SendRequestSerializer(serializers.Serializer):
    """Validate a new request and work out its direction.

    When the signed-in user owns the opportunity the request is an INVITE
    to ``recipient``; otherwise it is a JOIN request to the owner.
    """

    opportunity = serializers.PrimaryKeyRelatedField(queryset=Opportunity.objects.all())
    recipient = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    role = serializers.SlugField(required=False, allow_null=True)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, attrs):
        user = self.context["request"].user
        opportunity = attrs["opportunity"]

        if not opportunity.is_active:
            raise serializers.ValidationError({"opportunity": ["This opportunity isn't accepting requests."]})
        if opportunity.is_full:
            raise serializers.ValidationError({"opportunity": ["This team is full."]})

        if opportunity.owner_id == user.id:
            recipient = attrs.get("recipient")
            if recipient is None:
                raise serializers.ValidationError({"recipient": ["Choose a student to invite."]})
            if recipient == user:
                raise serializers.ValidationError({"recipient": ["You can't invite yourself."]})
            if not User.objects.visible_to(user).filter(pk=recipient.pk).exists():
                raise serializers.ValidationError({"recipient": ["This student isn't available."]})
            if not recipient.open_to_requests:
                raise serializers.ValidationError({"recipient": ["This student isn't open to requests right now."]})
            kind = ConnectionRequest.Kind.INVITE
        else:
            if not browsable_by(user).filter(pk=opportunity.pk).exists():
                raise serializers.ValidationError({"opportunity": ["This opportunity isn't accepting requests."]})
            recipient = opportunity.owner
            kind = ConnectionRequest.Kind.JOIN

        attrs["opportunity_role"] = self._resolve_role(opportunity, attrs.pop("role", None))
        attrs.update(kind=kind, sender=user, recipient=recipient)
        return attrs

    def _resolve_role(self, opportunity, slug):
        if not slug:
            return None
        role = opportunity.roles.filter(role__slug=slug).first()
        if role is None:
            raise serializers.ValidationError({"role": ["This opportunity has no such open role."]})
        return role
