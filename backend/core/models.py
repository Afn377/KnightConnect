import uuid

from django.db import models


class UUIDModel(models.Model):
    """Abstract base that uses a random UUID as the primary key.

    UUIDs avoid exposing sequential IDs (and therefore row counts) in API
    URLs, which matters for user and opportunity identifiers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
