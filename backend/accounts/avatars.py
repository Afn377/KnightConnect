import io

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

ALLOWED_FORMATS = {"JPEG", "PNG", "GIF"}
AVATAR_SIZE = (256, 256)


def process_avatar(upload):
    """Validate an uploaded image and return a 256x256 JPEG with no metadata.

    Re-encoding from pixels drops EXIF and other embedded data such as GPS
    location, and guarantees the stored file really is an image.
    """
    if upload.size > settings.AVATAR_MAX_UPLOAD_BYTES:
        limit = settings.AVATAR_MAX_UPLOAD_BYTES // (1024 * 1024) or 1
        raise ValidationError(f"Images must be smaller than {limit} MB.")
    try:
        Image.open(upload).verify()
        upload.seek(0)
        image = Image.open(upload)
        image.load()
    except (Image.DecompressionBombError, OSError, SyntaxError, ValueError):
        raise ValidationError("Upload a JPG, GIF, or PNG image.")
    if image.format not in ALLOWED_FORMATS:
        raise ValidationError("Upload a JPG, GIF, or PNG image.")

    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, AVATAR_SIZE, Image.Resampling.LANCZOS)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    return ContentFile(output.getvalue())
