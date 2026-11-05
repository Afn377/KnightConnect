import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from core.testing import APITestCase, make_user

MEDIA_ROOT = tempfile.mkdtemp(prefix="kc-test-media-")


def image_file(name="photo.png", size=(800, 400), image_format="PNG", exif=False):
    buffer = io.BytesIO()
    image = Image.new("RGB", size, (200, 30, 30))
    options = {}
    if exif:
        exif_data = Image.Exif()
        exif_data[0x010F] = "SecretCameraMaker"
        options["exif"] = exif_data
    image.save(buffer, format=image_format, **options)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{image_format.lower()}")


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class AvatarUploadTests(APITestCase):
    url = "/api/me/avatar/"

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        super().setUp()
        self.user = self.login(make_user())

    def upload(self, file):
        return self.client.post(self.url, {"image": file}, format="multipart")

    def stored_image(self):
        self.user.refresh_from_db()
        return Image.open(self.user.avatar.open("rb"))

    def test_uploads_a_square_resized_jpeg(self):
        response = self.upload(image_file())

        self.assertEqual(response.status_code, 200, response.json())
        self.assertTrue(response.json()["avatar_url"].startswith("http"))
        image = self.stored_image()
        self.assertEqual(image.size, (256, 256))
        self.assertEqual(image.format, "JPEG")

    def test_strips_photo_metadata(self):
        self.upload(image_file(name="photo.jpg", image_format="JPEG", exif=True))

        self.assertEqual(dict(self.stored_image().getexif()), {})

    def test_accepts_gif(self):
        self.assertEqual(self.upload(image_file(name="photo.gif", image_format="GIF")).status_code, 200)

    def test_replacing_removes_the_old_file(self):
        self.upload(image_file())
        self.user.refresh_from_db()
        old_name = self.user.avatar.name

        self.upload(image_file())

        self.user.refresh_from_db()
        self.assertNotEqual(self.user.avatar.name, old_name)
        self.assertFalse(self.user.avatar.storage.exists(old_name))

    def test_rejects_files_that_are_not_images(self):
        fake = SimpleUploadedFile("photo.png", b"not really an image", content_type="image/png")

        self.assertEqual(self.upload(fake).status_code, 400)

    def test_rejects_unsupported_formats(self):
        self.assertEqual(self.upload(image_file(name="photo.bmp", image_format="BMP")).status_code, 400)

    @override_settings(AVATAR_MAX_UPLOAD_BYTES=100)
    def test_rejects_large_files(self):
        self.assertEqual(self.upload(image_file()).status_code, 400)

    def test_profiles_and_cards_show_the_avatar(self):
        self.upload(image_file())
        url = self.client.get("/api/me/").json()["avatar_url"]

        self.login(make_user())
        self.assertEqual(self.client.get(f"/api/users/{self.user.id}/").json()["avatar_url"], url)
        self.assertIsNone(self.client.get("/api/me/").json()["avatar_url"])

    def test_requires_authentication(self):
        self.client.logout()

        self.assertEqual(self.upload(image_file()).status_code, 401)
