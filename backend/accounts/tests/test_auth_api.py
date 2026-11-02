
from core.testing import APITestCase


class CsrfEndpointTests(APITestCase):
    url = "/api/auth/csrf/"

    def test_sets_csrf_cookie_without_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)
        # The returned token is masked, so it differs from the cookie but is equally valid.
        self.assertTrue(response.json()["csrf_token"])
