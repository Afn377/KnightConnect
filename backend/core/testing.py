"""Shared helpers for building test data and exercising the API."""

import itertools
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase as DRFAPITestCase

from accounts.models import User
from catalog.models import Event
from opportunities.models import Opportunity

_sequence = itertools.count(1)


def make_user(email=None, **fields):
    email = email or f"student{next(_sequence)}@rutgers.edu"
    many_to_many = {name: fields.pop(name) for name in ("preferred_roles", "interests") if name in fields}
    user = User.objects.create_user(email, **fields)
    for name, values in many_to_many.items():
        getattr(user, name).set(values)
    return user


def make_event(**fields):
    now = timezone.now()
    defaults = {
        "name": f"Hackathon {next(_sequence)}",
        "starts_at": now + timedelta(days=10),
        "ends_at": now + timedelta(days=11),
        "recruiting_ends_at": now + timedelta(days=10),
    }
    defaults.update(fields)
    return Event.objects.create(**defaults)


def make_opportunity(owner=None, **fields):
    owner = owner or make_user()
    interests = fields.pop("interests", None)
    defaults = {
        "title": "HackRU Teammates Needed",
        "description": "Looking for teammates for HackRU.",
        "opportunity_type": Opportunity.Type.HACKATHON,
        "commitment": "full_event",
        "availability": ["weekend_morning", "weekend_afternoon"],
        "expires_at": timezone.now() + timedelta(days=3),
    }
    defaults.update(fields)
    opportunity = Opportunity.objects.create(owner=owner, **defaults)
    if interests is not None:
        opportunity.interests.set(interests)
    return opportunity


class APITestCase(DRFAPITestCase):
    """API test case that resets rate-limit counters between tests."""

    def setUp(self):
        super().setUp()
        cache.clear()

    def login(self, user):
        self.client.force_login(user)
        return user
