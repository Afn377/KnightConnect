from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from catalog.models import Event, Interest, Role, Skill
from catalog.seed_data import INTERESTS, ROLES, SKILLS


class Command(BaseCommand):
    help = (
        "Load the starter skills, roles, and interests, and optionally create or update an "
        "event. Safe to run repeatedly: existing entries (matched case-insensitively) are kept."
    )

    def add_arguments(self, parser):
        parser.add_argument("--event", help="Event name, e.g. 'HackRU Spring 2027'.")
        parser.add_argument("--starts", help="Event start, ISO 8601 with offset.")
        parser.add_argument("--ends", help="Event end, ISO 8601 with offset.")
        parser.add_argument(
            "--recruiting-ends",
            help="When team recruiting closes, ISO 8601. Defaults to the event start.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        created = {
            "skills": self._seed(Skill, SKILLS),
            "roles": self._seed(Role, ROLES),
            "interests": self._seed(Interest, INTERESTS),
        }
        self.stdout.write(
            "Created " + ", ".join(f"{count} {label}" for label, count in created.items()) + "."
        )
        if options["event"]:
            self._seed_event(options)

    def _seed(self, model, names):
        created = 0
        for entry in names:
            name, slug = entry if isinstance(entry, tuple) else (entry, slugify(entry))
            if not model.objects.filter(Q(name__iexact=name) | Q(slug=slug)).exists():
                model.objects.create(name=name, slug=slug)
                created += 1
        return created

    def _parse(self, value, option):
        parsed = parse_datetime(value or "")
        if parsed is None or parsed.tzinfo is None:
            raise CommandError(f"--{option} must be an ISO 8601 datetime with a UTC offset.")
        return parsed

    def _seed_event(self, options):
        starts_at = self._parse(options["starts"], "starts")
        ends_at = self._parse(options["ends"], "ends")
        recruiting_ends_at = (
            self._parse(options["recruiting_ends"], "recruiting-ends")
            if options["recruiting_ends"]
            else starts_at
        )
        event, created = Event.objects.update_or_create(
            slug=slugify(options["event"]),
            defaults={
                "name": options["event"],
                "starts_at": starts_at,
                "ends_at": ends_at,
                "recruiting_ends_at": recruiting_ends_at,
                "is_active": True,
            },
        )
        self.stdout.write(f"{'Created' if created else 'Updated'} event '{event.name}'.")
