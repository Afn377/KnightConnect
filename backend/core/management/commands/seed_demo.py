"""Fill a local database with realistic fake students, posts, and activity.

For development, frontend work, and demos only. Every account it creates uses
a ``demo-NNN@scarletmail.rutgers.edu`` address so demo data is easy to spot
and remove, and the command refuses to run against a database that already
holds real students unless told otherwise.

    python manage.py seed_demo                  # 100 students, seed 42
    python manage.py seed_demo --students 40 --seed 7
    python manage.py seed_demo --reset          # remove previous demo data first
"""

import io
import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from accounts.models import ContactMethod, EventInterest, User, UserSkill
from analytics.models import FunnelEvent
from catalog.models import Event, Interest, Role, Skill
from connections.models import ConnectionRequest
from connections.services import accept_request, cancel_request, decline_request, rate_connection, send_request
from core.choices import AvailabilitySlot
from core.exceptions import Conflict
from matching.engine import rank_candidates, rank_opportunities
from matching.models import MatchResult
from matching.services import record_matches
from opportunities.models import Opportunity, OpportunityRole, OpportunitySkill
from safety.models import Block, Report

DEMO_DOMAIN = "scarletmail.rutgers.edu"
DEMO_PREFIX = "demo-"
DEMO_EVENT = "Demo Hackathon"

FIRST = [
    "Aarav", "Maya", "Jordan", "Priya", "Ethan", "Sofia", "Noah", "Aisha", "Liam", "Zara", "Lucas", "Mei",
    "Omar", "Elena", "Dev", "Chloe", "Marcus", "Nina", "Ravi", "Grace", "Kai", "Leila", "Sam", "Hana",
]
LAST = [
    "Patel", "Kim", "Nguyen", "Garcia", "Shah", "Chen", "Okafor", "Rossi", "Singh", "Cohen", "Ali", "Park",
    "Lopez", "Mehta", "Brown", "Ivanova", "Haddad", "Wu",
]
MAJORS = [
    ("Computer Science", 40), ("Data Science", 12), ("Information Technology", 10), ("Electrical Engineering", 8),
    ("Mathematics", 6), ("Business Analytics", 6), ("Cognitive Science", 4), ("Design", 4),
]
YEARS = [("freshman", 15), ("sophomore", 25), ("junior", 30), ("senior", 22), ("grad", 8)]

# Skewed on purpose: plenty of Python/React, very few designers or hardware people,
# so some posts come up short on qualified matches.
SKILL_WEIGHTS = {
    "python": 30, "javascript": 22, "react": 20, "java": 14, "sql": 12, "git": 12, "html-css": 12,
    "typescript": 9, "node-js": 9, "next-js": 6, "django": 5, "flask": 5, "postgresql": 5, "data-analysis": 7,
    "machine-learning": 6, "pytorch": 3, "aws": 3, "docker": 3, "swift": 2, "figma": 3, "ui-design": 2,
    "ux-research": 1, "arduino": 1, "embedded-systems": 1, "public-speaking": 2, "project-management": 2,
}
ROLE_FOR_SKILL = {
    "python": "backend-developer", "django": "backend-developer", "flask": "backend-developer",
    "sql": "backend-developer", "postgresql": "backend-developer", "node-js": "backend-developer",
    "react": "frontend-developer", "javascript": "frontend-developer", "typescript": "frontend-developer",
    "next-js": "full-stack-developer", "html-css": "frontend-developer", "swift": "mobile-developer",
    "machine-learning": "ml-engineer", "pytorch": "ml-engineer", "data-analysis": "data-scientist",
    "figma": "designer", "ui-design": "designer", "ux-research": "designer",
    "arduino": "hardware-engineer", "embedded-systems": "hardware-engineer",
    "project-management": "product-manager", "public-speaking": "pitch-and-presentation-lead",
}
# Students mostly free on weekends, as hackathon students are.
SLOT_WEIGHTS = {
    AvailabilitySlot.WEEKEND_AFTERNOON: 70, AvailabilitySlot.WEEKEND_MORNING: 45,
    AvailabilitySlot.WEEKEND_EVENING: 50, AvailabilitySlot.WEEKDAY_EVENING: 40,
    AvailabilitySlot.WEEKDAY_AFTERNOON: 15, AvailabilitySlot.WEEKDAY_MORNING: 8,
}
PROJECTS = [
    ("Dining Hall Wait Times", "Estimate line lengths at campus dining halls and post live wait times.", "campus-life"),
    ("Course Swap Board", "Trade section seats when a class is full, with alerts for matching swaps.", "campus-life"),
    ("Bus Arrival Accuracy", "Compare scheduled and actual campus bus arrivals by route.", "research"),
    ("AI Study Buddy", "A tutor that quizzes you on your own lecture notes.", "ai"),
    ("Club Event Finder", "One feed of events from every student org, filterable by major.", "campus-life"),
    ("Textbook Price Tracker", "Track used textbook prices across campus listings.", "fintech"),
    ("Split the Rent", "Shared expense tracking for off-campus roommates.", "fintech"),
    ("Accessible Campus Map", "Routes that avoid stairs and broken elevators.", "accessibility"),
    ("Lab Equipment Booking", "Reserve shared lab equipment without the spreadsheet.", "productivity"),
    ("Mental Health Check-ins", "Anonymous weekly check-ins that point to campus resources.", "health"),
    ("Energy Use Dashboard", "Show dorm energy use and run building-vs-building challenges.", "climate"),
    ("Internship Tracker", "Track applications, deadlines, and referrals in one place.", "productivity"),
    ("Pitch Practice Coach", "Record a pitch and get feedback on pacing and filler words.", "ai"),
    ("Food Pantry Inventory", "Real-time stock for the campus food pantry.", "social-good"),
    ("Hackathon Judge Helper", "Score and rank submissions consistently across judges.", "developer-tools"),
    ("Smart Plant Monitor", "Soil sensors that text you when a plant needs water.", "hardware-iot"),
    ("Phishing Email Detector", "Flag suspicious messages in a student inbox.", "cybersecurity"),
    ("Language Exchange Match", "Pair students learning each other's languages.", "education"),
    ("Gym Crowd Meter", "Predict how busy each rec center will be.", "health"),
    ("Lecture Note Summarizer", "Turn lecture recordings into searchable summaries.", "education"),
    ("Parking Spot Predictor", "Predict open spots in commuter lots by time of day.", "campus-life"),
    ("Retro Game Jam Entry", "A small pixel-art game built in a weekend.", "gaming"),
    ("Volunteer Hours Log", "Log and verify volunteer hours for student orgs.", "social-good"),
    ("Research Paper Finder", "Recommend papers based on a course syllabus.", "research"),
    ("Budget Coach", "Monthly budgeting tips based on student spending.", "fintech"),
    ("Sign Language Translator", "Recognize basic signs from a webcam.", "accessibility"),
    ("Commuter Carpool", "Match commuters driving from the same towns.", "climate"),
    ("Code Review Buddy", "Explain pull request feedback in plain language.", "developer-tools"),
]


class Command(BaseCommand):
    help = "Create fake demo students, posts, requests, feedback, and analytics for local development."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=100)
        parser.add_argument("--seed", type=int, default=42, help="Random seed, so runs are repeatable.")
        parser.add_argument("--reset", action="store_true", help="Delete earlier demo data first.")
        parser.add_argument(
            "--allow-real-data",
            action="store_true",
            help="Run even if the database already has non-demo students. Never use on the pilot database.",
        )

    def handle(self, *args, **options):
        if options["students"] < 10:
            raise CommandError("Use at least 10 students so matching has something to work with.")
        real = User.objects.exclude(email__startswith=DEMO_PREFIX).filter(is_staff=False).count()
        if real and not options["allow_real_data"]:
            raise CommandError(
                f"This database has {real} real student account(s). Demo data would pollute the pilot "
                "metrics. Use a local database, or pass --allow-real-data if you're sure."
            )
        self.random = random.Random(options["seed"])
        # Real services send emails; don't, while seeding.
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"):
            with transaction.atomic():
                if options["reset"]:
                    self.reset()
                elif User.objects.filter(email__startswith=DEMO_PREFIX).exists():
                    raise CommandError("Demo data already exists. Pass --reset to recreate it.")
                call_command("seed_catalog", stdout=io.StringIO())
                self.load_catalog()
                summary = self.seed(options["students"])
        self.stdout.write(self.style.SUCCESS("Demo data created: " + ", ".join(f"{v} {k}" for k, v in summary.items())))

    # ---------------------------------------------------------------- setup

    def reset(self):
        demo_users = User.objects.filter(email__startswith=DEMO_PREFIX)
        demo_posts = Opportunity.objects.filter(owner__in=demo_users)
        FunnelEvent.objects.filter(user__in=demo_users).delete()
        FunnelEvent.objects.filter(opportunity__in=demo_posts).delete()
        ConnectionRequest.objects.filter(opportunity__in=demo_posts).delete()
        demo_posts.delete()
        demo_users.delete()
        Event.objects.filter(name=DEMO_EVENT).delete()

    def load_catalog(self):
        self.skills = {s.slug: s for s in Skill.objects.filter(slug__in=SKILL_WEIGHTS)}
        self.roles = {r.slug: r for r in Role.objects.all()}
        self.interests = {i.slug: i for i in Interest.objects.all()}
        now = timezone.now()
        self.event = Event.objects.create(
            name=DEMO_EVENT,
            description="Fake event for demo data.",
            starts_at=now + timedelta(days=14),
            ends_at=now + timedelta(days=15),
            recruiting_ends_at=now + timedelta(days=14),
        )

    def pick_weighted(self, weights, k):
        """``k`` distinct keys, more likely the heavier their weight."""
        pool = dict(weights)
        chosen = []
        for _ in range(min(k, len(pool))):
            key = self.random.choices(list(pool), weights=list(pool.values()))[0]
            chosen.append(key)
            del pool[key]
        return chosen

    # ---------------------------------------------------------------- data

    def seed(self, count):
        students = [self.make_student(n) for n in range(1, count + 1)]
        posts = self.make_posts(students)
        requests = self.make_activity(posts, students)
        self.make_safety_cases(students)
        return {
            "students": len(students),
            "opportunities": len(posts),
            "requests": requests,
            "accepted": ConnectionRequest.objects.filter(opportunity__in=posts, status="accepted").count(),
            "match runs": MatchResult.objects.filter(opportunity__in=posts).values("batch_id").distinct().count(),
            "funnel events": FunnelEvent.objects.filter(opportunity__in=posts).count(),
        }

    def make_student(self, n):
        r = self.random
        first, last = r.choice(FIRST), r.choice(LAST)
        skills = self.pick_weighted({k: v for k, v in SKILL_WEIGHTS.items() if k in self.skills}, r.randint(2, 6))
        slots = self.pick_weighted(SLOT_WEIGHTS, r.randint(1, 4))
        user = User.objects.create_user(
            f"{DEMO_PREFIX}{n:03d}@{DEMO_DOMAIN}",
            display_name=f"{first} {last[0]}.",
            major=r.choices(*zip(*MAJORS))[0],
            year=r.choices(*zip(*YEARS))[0],
            bio="Demo account. Not a real student.",
            availability=[str(slot) for slot in slots],
            commitment=r.choices(["full", "partial"], weights=[60, 40])[0],
            open_to_requests=r.random() > 0.1,  # ~10% hidden from the candidate pool
        )
        for slug in skills:
            UserSkill.objects.create(
                user=user, skill=self.skills[slug],
                proficiency=r.choices(["beginner", "intermediate", "advanced"], weights=[30, 45, 25])[0],
            )
        roles = {ROLE_FOR_SKILL[s] for s in skills if s in ROLE_FOR_SKILL} & set(self.roles)
        user.preferred_roles.set([self.roles[s] for s in sorted(roles)][:2])
        user.interests.set(r.sample(list(self.interests.values()), r.randint(1, 3)))
        if r.random() < 0.6:
            EventInterest.objects.create(user=user, event=self.event, full_event=True)
        if r.random() < 0.8:  # ~20% have no contact methods, to exercise the email fallback
            ContactMethod.objects.create(user=user, kind="discord", value=f"{first.lower()}.{n:03d}", is_preferred=True)
            if r.random() < 0.3:
                ContactMethod.objects.create(user=user, kind="linkedin", value=f"linkedin.com/in/demo-{n:03d}")
        return user

    def make_posts(self, students):
        r = self.random
        now = timezone.now()
        owners = r.sample(students, min(len(PROJECTS), max(5, len(students) // 4)))
        posts = []
        for index, owner in enumerate(owners):
            title, description, interest = PROJECTS[index]
            on_event = r.random() < 0.7
            post = Opportunity.objects.create(
                owner=owner,
                event=self.event if on_event else None,
                title=title,
                description=description,
                opportunity_type="hackathon" if on_event else r.choice(["class_project", "personal_project", "research"]),
                availability=[str(s) for s in self.pick_weighted(SLOT_WEIGHTS, r.randint(1, 3))],
                commitment=r.choice(["full", "partial"]),
                team_capacity=r.choice([3, 4, 4, 5]),
                expires_at=now + timedelta(days=r.randint(3, 13)),
                published_at=now - timedelta(days=r.randint(0, 6)),
            )
            if interest in self.interests:
                post.interests.set([self.interests[interest]])
            for slug in r.sample(sorted(set(ROLE_FOR_SKILL.values()) & set(self.roles)), r.randint(1, 3)):
                OpportunityRole.objects.create(opportunity=post, role=self.roles[slug])
            skills = self.pick_weighted({k: v for k, v in SKILL_WEIGHTS.items() if k in self.skills}, r.randint(2, 5))
            for i, slug in enumerate(skills):
                OpportunitySkill.objects.create(
                    opportunity=post, skill=self.skills[slug],
                    requirement_type="required" if i < r.choice([0, 1, 1, 2]) else "preferred",
                )
            FunnelEvent.record(FunnelEvent.Type.OPPORTUNITY_CREATED, user=owner, opportunity=post)
            posts.append(post)

        # A few posts in other states: drafts and expired.
        for post in posts[-2:]:
            Opportunity.objects.filter(pk=post.pk).update(status="draft", published_at=None, expires_at=None)
        for post in posts[-4:-2]:
            post.close(Opportunity.CloseReason.EXPIRED)
        return [Opportunity.objects.get(pk=p.pk) for p in posts]

    def make_activity(self, posts, students):
        r = self.random
        sent = 0
        for post in posts:
            if not post.is_active:
                continue
            if r.random() < 0.85:  # most owners open their Matches page at least once
                _, results = record_matches(rank_candidates(post), direction="candidates", viewer=post.owner)
                for result in results[: r.randint(1, 4)]:
                    sent += self.connect(post, result.candidate, kind=r.choice(["join", "join", "invite"]))
        for student in r.sample(students, len(students) // 3):
            _, results = record_matches(rank_opportunities(student), direction="opportunities", viewer=student)
            for result in results[:2]:
                FunnelEvent.record(
                    FunnelEvent.Type.RECOMMENDATION_VIEWED, user=student, opportunity=result.opportunity,
                    match_result=result, rank=result.rank,
                )
        return sent

    def connect(self, post, candidate, *, kind):
        r = self.random
        sender, recipient = (candidate, post.owner) if kind == "join" else (post.owner, candidate)
        role = r.choice(list(post.roles.all()))
        try:
            request_ = send_request(
                opportunity=post, sender=sender, recipient=recipient, kind=kind, opportunity_role=role,
                message="Demo request." if kind == "join" else "",
            )
        except Conflict:
            return 0
        outcome = r.choices(["accept", "decline", "cancel", "pending"], weights=[45, 15, 10, 30])[0]
        try:
            if outcome == "accept":
                request_ = accept_request(request_, actor=recipient)
                for person in (sender, recipient):
                    if r.random() < 0.6:
                        rate_connection(request_, user=person, was_useful=r.random() < 0.7)
            elif outcome == "decline":
                decline_request(request_, actor=recipient)
            elif outcome == "cancel":
                cancel_request(request_, actor=sender)
        except Conflict:
            pass  # team filled up first; leave it pending
        post.refresh_from_db()
        return 1

    def make_safety_cases(self, students):
        a, b, c = self.random.sample(students, 3)
        Block.objects.create(blocker=a, blocked=b)
        Report.objects.create(reporter=c, reported_user=a, reason="spam", details="Demo report.")
