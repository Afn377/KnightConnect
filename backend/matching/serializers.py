from rest_framework import serializers

from accounts.serializers import PublicProfileSerializer
from opportunities.serializers import OpportunitySerializer


class MatchSerializer(serializers.Serializer):
    match_id = serializers.UUIDField(source="id")
    rank = serializers.IntegerField()
    score = serializers.FloatField()
    explanations = serializers.JSONField(source="explanation_factors")


class CandidateMatchSerializer(MatchSerializer):
    candidate = PublicProfileSerializer()


class OpportunityMatchSerializer(MatchSerializer):
    opportunity = OpportunitySerializer()
