from accounts.models import ContactMethod
from core.testing import APITestCase, make_user


class ContactMethodListTests(APITestCase):
    url = "/api/me/contact-methods/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def test_lists_own_contact_methods_preferred_first(self):
        ContactMethod.objects.create(user=self.user, kind="email", value="netid@rutgers.edu")
        discord = ContactMethod.objects.create(user=self.user, kind="discord", value="knight", is_preferred=True)
        ContactMethod.objects.create(user=make_user(), kind="discord", value="someone-else")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"id": discord.id, "kind": "discord", "value": "knight", "is_preferred": True},
                {"id": discord.id - 1, "kind": "email", "value": "netid@rutgers.edu", "is_preferred": False},
            ],
        )

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.client.get(self.url).status_code, 401)
