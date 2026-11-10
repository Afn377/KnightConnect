import uuid

from analytics.models import FunnelEvent
from core.testing import APITestCase, make_opportunity, make_user, throttle_rates
from matching.models import MatchResult
from opportunities.models import Opportunity


class TrackEventTests(APITestCase):
    url = "/api/analytics/track/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.opportunity = make_opportunity()

    def track(self, **data):
        return self.client.post(self.url, data, format="json")

    def shown_match(self, viewer):
        result = MatchResult.objects.create(
            batch_id=uuid.uuid4(), direction="opportunities", opportunity=self.opportunity,
            candidate=viewer, rank=1, score="0.5",
        )
        FunnelEvent.record(FunnelEvent.Type.RECOMMENDATION_SHOWN, user=viewer, opportunity=self.opportunity, match_result=result)
        return result

    def test_records_opportunity_view(self):
        response = self.track(event_type="opportunity_viewed", opportunity=str(self.opportunity.id))

        self.assertEqual(response.status_code, 204)
        event = FunnelEvent.objects.get()
        self.assertEqual(event.event_type, "opportunity_viewed")
        self.assertEqual(event.user, self.user)
        self.assertEqual(event.opportunity, self.opportunity)

    def test_records_recommendation_view(self):
        result = self.shown_match(self.user)

        response = self.track(event_type="recommendation_viewed", match_result=str(result.id))

        self.assertEqual(response.status_code, 204)
        event = FunnelEvent.objects.get(event_type="recommendation_viewed")
        self.assertEqual(event.match_result, result)
        self.assertEqual(event.opportunity, self.opportunity)
        self.assertEqual(event.metadata, {"rank": 1})

    def test_recommendation_must_have_been_shown_to_viewer(self):
        result = self.shown_match(make_user())

        self.assertEqual(self.track(event_type="recommendation_viewed", match_result=str(result.id)).status_code, 400)

    def test_opportunity_must_be_viewable(self):
        self.opportunity.close(Opportunity.CloseReason.OWNER_CLOSED)

        self.assertEqual(self.track(event_type="opportunity_viewed", opportunity=str(self.opportunity.id)).status_code, 400)

    def test_rejects_server_side_event_types(self):
        response = self.track(event_type="request_accepted", opportunity=str(self.opportunity.id))

        self.assertEqual(response.status_code, 400)
        self.assertFalse(FunnelEvent.objects.exists())

    def test_requires_target(self):
        self.assertEqual(self.track(event_type="opportunity_viewed").status_code, 400)
        self.assertEqual(self.track(event_type="recommendation_viewed").status_code, 400)

    @throttle_rates(analytics="2/hour")
    def test_rate_limited(self):
        for _ in range(2):
            self.track(event_type="opportunity_viewed", opportunity=str(self.opportunity.id))

        self.assertEqual(self.track(event_type="opportunity_viewed", opportunity=str(self.opportunity.id)).status_code, 429)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.track(event_type="opportunity_viewed", opportunity=str(self.opportunity.id)).status_code, 401)
