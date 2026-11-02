import uuid

from django.utils.dateparse import parse_datetime

from connections.models import ConnectionRequest
from core.testing import APITestCase, make_opportunity, make_user
from safety.models import Block, Report


class BlockListTests(APITestCase):
    url = "/api/blocks/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def test_lists_users_i_blocked(self):
        blocked = make_user(display_name="Annoying")
        block = Block.objects.create(blocker=self.user, blocked=blocked)
        Block.objects.create(blocker=make_user(), blocked=self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["user"], {"id": str(blocked.id), "display_name": "Annoying"})
        self.assertEqual(parse_datetime(body[0]["created_at"]), block.created_at)

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)
