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


class ContactMethodUpdateTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())
        self.discord = ContactMethod.objects.create(user=self.user, kind="discord", value="knight")
        self.email = ContactMethod.objects.create(user=self.user, kind="email", value="a@rutgers.edu", is_preferred=True)

    def patch(self, method, data):
        return self.client.patch(f"/api/me/contact-methods/{method.id}/", data, format="json")

    def test_updates_value(self):
        response = self.patch(self.discord, {"value": "scarlet"})

        self.assertEqual(response.status_code, 200)
        self.discord.refresh_from_db()
        self.assertEqual(self.discord.value, "scarlet")

    def test_switching_preference_clears_previous(self):
        response = self.patch(self.discord, {"is_preferred": True})

        self.assertEqual(response.status_code, 200)
        self.email.refresh_from_db()
        self.discord.refresh_from_db()
        self.assertTrue(self.discord.is_preferred)
        self.assertFalse(self.email.is_preferred)

    def test_cannot_change_to_kind_already_used(self):
        self.assertEqual(self.patch(self.discord, {"kind": "email", "value": "b@rutgers.edu"}).status_code, 400)

    def test_cannot_update_someone_elses_method(self):
        other = ContactMethod.objects.create(user=make_user(), kind="discord", value="someone")

        self.assertEqual(self.patch(other, {"value": "hijacked"}).status_code, 404)
        other.refresh_from_db()
        self.assertEqual(other.value, "someone")


class ContactMethodDeleteTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def test_removes_contact_method(self):
        method = ContactMethod.objects.create(user=self.user, kind="discord", value="knight")

        response = self.client.delete(f"/api/me/contact-methods/{method.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(ContactMethod.objects.exists())

    def test_cannot_remove_someone_elses_method(self):
        other = ContactMethod.objects.create(user=make_user(), kind="discord", value="someone")

        response = self.client.delete(f"/api/me/contact-methods/{other.id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(ContactMethod.objects.filter(pk=other.pk).exists())
