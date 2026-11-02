import re
from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import LoginCode, User
from core.testing import APITestCase, make_user


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


class VerifyCodeTests(APITestCase):
    url = "/api/auth/verify-code/"

    def request_code(self, email="netid@rutgers.edu"):
        self.client.post("/api/auth/request-code/", {"email": email}, format="json")
        return code_from_last_email()

    def verify(self, code, email="netid@rutgers.edu"):
        return self.client.post(self.url, {"email": email, "code": code}, format="json")

    def wrong(self, code):
        return "000000" if code != "000000" else "111111"

    def test_correct_code_creates_account_and_signs_in(self):
        code = self.request_code()

        response = self.verify(code)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["created"])
        self.assertEqual(body["user"]["email"], "netid@rutgers.edu")
        user = User.objects.get(email="netid@rutgers.edu")
        self.assertEqual(body["user"]["id"], str(user.id))
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_existing_user_signs_in_without_creating_account(self):
        user = make_user("netid@rutgers.edu")
        code = self.request_code()

        response = self.verify(code)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(self.client.session["_auth_user_id"], str(user.pk))

    def test_email_is_matched_case_insensitively(self):
        code = self.request_code("netid@rutgers.edu")

        self.assertEqual(self.verify(code, email="NetID@Rutgers.edu").status_code, 200)

    def test_wrong_code_is_rejected_and_counted(self):
        code = self.request_code()

        response = self.verify(self.wrong(code))

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(LoginCode.objects.get().attempts, 1)
        self.assertEqual(self.verify(code).status_code, 200)

    def test_code_cannot_be_reused(self):
        code = self.request_code()
        self.verify(code)
        self.client.logout()

        self.assertEqual(self.verify(code).status_code, 400)

    def test_expired_code_is_rejected(self):
        code = self.request_code()
        LoginCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        self.assertEqual(self.verify(code).status_code, 400)

    @override_settings(LOGIN_CODE_MAX_ATTEMPTS=3)
    def test_code_is_locked_after_too_many_attempts(self):
        code = self.request_code()
        for _ in range(3):
            self.verify(self.wrong(code))

        self.assertEqual(self.verify(code).status_code, 400)

    def test_code_for_another_email_is_rejected(self):
        first_code = self.request_code("first@rutgers.edu")
        second_code = self.request_code("second@rutgers.edu")
        if first_code == second_code:
            self.skipTest("Randomly generated codes collided.")

        self.assertEqual(self.verify(first_code, email="second@rutgers.edu").status_code, 400)

    def test_rejects_when_no_code_was_requested(self):
        self.assertEqual(self.verify("123456").status_code, 400)

    def test_requires_email_and_code(self):
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 400)

    def test_disabled_account_cannot_sign_in(self):
        make_user("netid@rutgers.edu", is_active=False)
        code = self.request_code()

        response = self.verify(code)

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)

    @throttle_rates(login_verify="2/hour")
    def test_rate_limited(self):
        self.verify("111111")
        self.verify("111111")

        self.assertEqual(self.verify("111111").status_code, 429)


class LogoutTests(APITestCase):
    url = "/api/auth/logout/"

    def test_ends_the_session(self):
        self.login(make_user())

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 204)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_requires_authentication(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)

    def test_requires_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(make_user())

        self.assertEqual(client.post(self.url).status_code, 403)

        token = client.get("/api/auth/csrf/").json()["csrf_token"]
        self.assertEqual(client.post(self.url, HTTP_X_CSRFTOKEN=token).status_code, 204)
