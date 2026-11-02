import re

from django.conf import settings
from django.core import mail
from django.test import override_settings

from accounts.models import LoginCode
from core.testing import APITestCase


def throttle_rates(**rates):
    return override_settings(
        REST_FRAMEWORK={
            **settings.REST_FRAMEWORK,
            "DEFAULT_THROTTLE_RATES": {**settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"], **rates},
        }
    )


def code_from_last_email():
    return re.search(r"\b(\d{6})\b", mail.outbox[-1].body).group(1)


class CsrfEndpointTests(APITestCase):
    url = "/api/auth/csrf/"

    def test_sets_csrf_cookie_without_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        # The returned token is masked, so it differs from the cookie but is equally valid.
        self.assertTrue(response.json()["csrf_token"])


class RequestCodeTests(APITestCase):
    url = "/api/auth/request-code/"

    def test_emails_a_six_digit_code_to_rutgers_address(self):
        response = self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["netid@rutgers.edu"])
        self.assertRegex(mail.outbox[0].body, r"\b\d{6}\b")

    def test_accepts_scarletmail_and_normalizes_case(self):
        response = self.client.post(self.url, {"email": " NetID@ScarletMail.Rutgers.edu "}, format="json")

        self.assertEqual(response.status_code, 202)
        self.assertEqual(mail.outbox[0].to, ["netid@scarletmail.rutgers.edu"])
        self.assertTrue(LoginCode.objects.filter(email="netid@scarletmail.rutgers.edu").exists())

    def test_stores_only_a_hash_of_the_code(self):
        self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json")

        stored = LoginCode.objects.get(email="netid@rutgers.edu")
        self.assertNotEqual(stored.code_hash, code_from_last_email())
        self.assertNotIn(code_from_last_email(), stored.code_hash)

    def test_rejects_non_rutgers_email(self):
        response = self.client.post(self.url, {"email": "someone@gmail.com"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertEqual(mail.outbox, [])

    def test_requires_email(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, 400)

    def test_new_code_replaces_previous_one(self):
        self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json")
        self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json")

        self.assertEqual(LoginCode.objects.filter(email="netid@rutgers.edu").count(), 1)

    def test_response_does_not_reveal_whether_account_exists(self):
        from core.testing import make_user

        make_user("existing@rutgers.edu")
        existing = self.client.post(self.url, {"email": "existing@rutgers.edu"}, format="json")
        new = self.client.post(self.url, {"email": "new@rutgers.edu"}, format="json")

        self.assertEqual(existing.status_code, new.status_code)
        self.assertEqual(existing.json(), new.json())

    @throttle_rates(login_code_email="2/hour")
    def test_rate_limited_per_email(self):
        for _ in range(2):
            self.assertEqual(self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json").status_code, 202)

        response = self.client.post(self.url, {"email": "netid@rutgers.edu"}, format="json")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            self.client.post(self.url, {"email": "other@rutgers.edu"}, format="json").status_code, 202
        )

    @throttle_rates(login_code="2/hour")
    def test_rate_limited_per_client(self):
        self.client.post(self.url, {"email": "a@rutgers.edu"}, format="json")
        self.client.post(self.url, {"email": "b@rutgers.edu"}, format="json")

        response = self.client.post(self.url, {"email": "c@rutgers.edu"}, format="json")

        self.assertEqual(response.status_code, 429)
