from rest_framework import serializers

from matching.models import MatchResult
from opportunities.models import Opportunity
from opportunities.queries import viewable_by

from .models import FunnelEvent

CLIENT_EVENT_TYPES = [FunnelEvent.Type.OPPORTUNITY_VIEWED, FunnelEvent.Type.RECOMMENDATION_VIEWED]


class TrackEventSerializer(serializers.Serializer):
    """A funnel step only the frontend can observe.

    Everything else (recommendations shown, requests sent and answered,
    ratings) is recorded on the server and can't be submitted here.
    """

    event_type = serializers.ChoiceField(choices=CLIENT_EVENT_TYPES)
    opportunity = serializers.PrimaryKeyRelatedField(queryset=Opportunity.objects.all(), required=False)
    match_result = serializers.PrimaryKeyRelatedField(queryset=MatchResult.objects.all(), required=False)

    def validate(self, attrs):
        user = self.context["request"].user
        if attrs["event_type"] == FunnelEvent.Type.OPPORTUNITY_VIEWED:
            opportunity = attrs.get("opportunity")
            if opportunity is None or not viewable_by(user).filter(pk=opportunity.pk).exists():
                raise serializers.ValidationError({"opportunity": ["Choose an opportunity you can view."]})
            attrs.pop("match_result", None)
        else:
            result = attrs.get("match_result")
            shown = result is not None and FunnelEvent.objects.filter(
                event_type=FunnelEvent.Type.RECOMMENDATION_SHOWN, user=user, match_result=result
            ).exists()
            if not shown:
                raise serializers.ValidationError({"match_result": ["Choose a recommendation you were shown."]})
            attrs["opportunity"] = result.opportunity
        return attrs

    def save(self):
        data = self.validated_data
        result = data.get("match_result")
        metadata = {"rank": result.rank} if result else {}
        return FunnelEvent.record(
            data["event_type"],
            user=self.context["request"].user,
            opportunity=data["opportunity"],
            match_result=result,
            **metadata,
        )
