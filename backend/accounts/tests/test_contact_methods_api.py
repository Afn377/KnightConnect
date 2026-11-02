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


class ContactMethodCreateTests(APITestCase):
    url = "/api/me/contact-methods/"

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def post(self, data):
        return self.client.post(self.url, data, format="json")

    def test_adds_contact_method(self):
        response = self.post({"kind": "discord", "value": "knight"})

        self.assertEqual(response.status_code, 201)
        method = ContactMethod.objects.get()
        self.assertEqual(method.user, self.user)
        self.assertEqual(response.json(), {"id": method.id, "kind": "discord", "value": "knight", "is_preferred": False})

    def test_new_preferred_method_replaces_previous_preference(self):
        old = ContactMethod.objects.create(user=self.user, kind="email", value="a@rutgers.edu", is_preferred=True)

        response = self.post({"kind": "discord", "value": "knight", "is_preferred": True})

        self.assertEqual(response.status_code, 201)
        old.refresh_from_db()
        self.assertFalse(old.is_preferred)

    def test_rejects_second_method_of_same_kind(self):
        ContactMethod.objects.create(user=self.user, kind="discord", value="knight")

        response = self.post({"kind": "discord", "value": "other"})

        self.assertEqual(response.status_code, 400)

    def test_same_kind_allowed_for_different_users(self):
        ContactMethod.objects.create(user=make_user(), kind="discord", value="someone")

        self.assertEqual(self.post({"kind": "discord", "value": "knight"}).status_code, 201)

    def test_rejects_unknown_kind(self):
        self.assertEqual(self.post({"kind": "pager", "value": "123"}).status_code, 400)

    def test_rejects_blank_value(self):
        self.assertEqual(self.post({"kind": "discord", "value": "  "}).status_code, 400)

    def test_email_kind_requires_valid_email(self):
        response = self.post({"kind": "email", "value": "not-an-email"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("value", response.json())
