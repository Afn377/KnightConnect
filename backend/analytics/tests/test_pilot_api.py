import uuid
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import User
from connections.models import ConnectionFeedback, ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from matching.models import MatchResult
from opportunities.models import Opportunity


def show_candidates(opportunity, count):
    """Record one Matches-page run that showed ``count`` qualified candidates."""
    batch = uuid.uuid4()
    for rank in range(1, count + 1):
        MatchResult.objects.create(
            batch_id=batch, direction="candidates", opportunity=opportunity,
            candidate=make_user(), rank=rank, score=Decimal("0.5"),
        )


def accepted_connection(opportunity, *, useful=None):
    request_ = ConnectionRequest.objects.create(
        opportunity=opportunity, kind="join", sender=make_user(), recipient=opportunity.owner, status="accepted"
    )
    if useful is not None:
        ConnectionFeedback.objects.create(connection_request=request_, user=opportunity.owner, was_useful=useful)
    return request_


class PilotMetricsTests(APITestCase):
    url = "/api/analytics/pilot/"

    def setUp(self):
        super().setUp()
        self.login(User.objects.create_user("staff@rutgers.edu", is_staff=True))

    def pilot(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["pilot"]

    def test_empty_pilot_has_no_rates(self):
        pilot = self.pilot()

        self.assertEqual(pilot["opportunities"], 0)
        self.assertIsNone(pilot["qualified_matches"]["rate"])
        self.assertFalse(pilot["qualified_matches"]["met"])
        self.assertIsNone(pilot["useful_connections"]["rate"])

    def test_qualified_match_rate_uses_largest_list_shown_per_post(self):
        posts = [make_opportunity() for _ in range(5)]
        show_candidates(posts[0], 3)
        show_candidates(posts[1], 1)
        show_candidates(posts[1], 4)  # a later run found more: counts as 4
        show_candidates(posts[2], 2)
        show_candidates(posts[3], 5)
        # posts[4]'s owner never opened Matches.

        qualified = self.pilot()["qualified_matches"]

        self.assertEqual(qualified["measured"], 4)
        self.assertEqual(qualified["unmeasured"], 1)
        self.assertEqual(qualified["with_3_or_more"], 3)
        self.assertEqual(qualified["rate"], 0.75)
        self.assertFalse(qualified["met"])

    def test_qualified_match_target_met_at_eighty_percent(self):
        posts = [make_opportunity() for _ in range(5)]
        for post in posts[:4]:
            show_candidates(post, 3)
        show_candidates(posts[4], 2)

        self.assertTrue(self.pilot()["qualified_matches"]["met"])

    def test_recommendation_runs_do_not_count_as_qualified_matches(self):
        post = make_opportunity()
        batch = uuid.uuid4()
        for rank in range(1, 4):
            MatchResult.objects.create(
                batch_id=batch, direction="opportunities", opportunity=post,
                candidate=make_user(), rank=rank, score=Decimal("0.5"),
            )

        self.assertEqual(self.pilot()["qualified_matches"]["measured"], 0)

    def test_useful_connection_rate_counts_posts_not_ratings(self):
        posts = [make_opportunity() for _ in range(4)]
        accepted_connection(posts[0], useful=True)
        accepted_connection(posts[0], useful=True)  # second useful one on the same post
        accepted_connection(posts[1], useful=False)
        accepted_connection(posts[2])  # accepted but never rated

        useful = self.pilot()["useful_connections"]

        self.assertEqual(useful["with_useful_connection"], 1)
        self.assertEqual(useful["rate"], 0.25)
        self.assertTrue(useful["met"])

    def test_drafts_are_not_matching_requests(self):
        make_opportunity(status=Opportunity.Status.DRAFT, expires_at=None)
        make_opportunity()

        self.assertEqual(self.pilot()["opportunities"], 1)

    def test_filters_by_publication_date(self):
        old = make_opportunity()
        Opportunity.objects.filter(pk=old.pk).update(published_at=timezone.now() - timedelta(days=20))
        make_opportunity(published_at=timezone.now())
        today = timezone.localdate().isoformat()

        self.assertEqual(self.pilot(start=today)["opportunities"], 1)

    def test_rejects_bad_dates(self):
        self.assertEqual(self.client.get(self.url, {"start": "11/10/2026"}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {"start": "2026-11-10", "end": "2026-11-01"}).status_code, 400)

    def test_staff_only(self):
        self.login(make_user())
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 401)
