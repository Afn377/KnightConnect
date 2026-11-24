"""Set up the fixed story used to rehearse and present the Dec 3 showcase.

Unlike ``seed_demo`` (random volume), this builds the same named scenario
every time, so every rehearsal starts from an identical state:

- Two presenter accounts you sign in as on stage:
    owner.demo@scarletmail.rutgers.edu   Priya, who posts and reviews
    joiner.demo@scarletmail.rutgers.edu  Jordan, who browses and requests
- One upcoming hackathon, "HackRU Spring 2027".
- Priya's post "Campus Dining Wait Times", where Jordan is the #1 match.
- About 40 background students and 7 other posts so Browse, Matches, and
  Requests look like a real campus, not an empty app.
- Some existing activity: an incoming request and an accepted connection
  for Priya, a sent request for Jordan.

    python manage.py seed_showcase           # first time
    python manage.py seed_showcase --reset   # before every rehearsal
"""

import io
import random
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.test.utils import override_settings
from django.utils import timezone

from accounts.models import ContactMethod, EventInterest, User, UserSkill
from catalog.models import Event, Interest, Role, Skill
from connections.services import accept_request, rate_connection, send_request
from matching.engine import rank_candidates
from matching.services import record_matches
from opportunities.models import Opportunity, OpportunityRole, OpportunitySkill

OWNER_EMAIL = "owner.demo@scarletmail.rutgers.edu"
JOINER_EMAIL = "joiner.demo@scarletmail.rutgers.edu"
BACKGROUND_PREFIX = "showcase-"
DOMAIN = "scarletmail.rutgers.edu"
EVENT_NAME = "HackRU Spring 2027"
STAR_POST = "Campus Dining Wait Times"

WEEKEND = ["weekend_morning", "weekend_afternoon"]

# Background students: (name, major, year, skills {slug: proficiency}, roles, interests, availability, commitment)
STUDENTS = [
    ("Aarav M.", "Computer Science", "junior", {"python": "intermediate", "sql": "intermediate"}, ["backend-developer"], ["campus-life"], WEEKEND, "full"),
    ("Maya K.", "Data Science", "sophomore", {"python": "advanced", "data-analysis": "advanced"}, ["data-scientist"], ["ai", "campus-life"], WEEKEND, "partial"),
    ("Ethan R.", "Computer Science", "senior", {"python": "beginner", "flask": "intermediate"}, ["backend-developer"], ["productivity"], ["weekend_afternoon"], "full"),
    ("Sofia G.", "Information Technology", "junior", {"python": "intermediate", "machine-learning": "beginner"}, ["ml-engineer"], ["ai"], WEEKEND, "partial"),
    ("Noah P.", "Electrical Engineering", "junior", {"python": "beginner", "arduino": "advanced"}, ["hardware-engineer"], ["hardwareiot"], ["weekend_morning"], "full"),
    ("Aisha O.", "Computer Science", "freshman", {"react": "intermediate", "typescript": "beginner"}, ["frontend-developer"], ["education"], WEEKEND, "full"),
    ("Liam C.", "Computer Science", "senior", {"react": "advanced", "nextjs": "advanced", "typescript": "advanced"}, ["frontend-developer", "full-stack-developer"], ["developer-tools"], WEEKEND, "full"),
    ("Zara A.", "Design", "sophomore", {"figma": "advanced", "ui-design": "advanced"}, ["designer"], ["accessibility"], WEEKEND, "partial"),
    ("Lucas W.", "Computer Science", "junior", {"java": "advanced", "sql": "intermediate"}, ["backend-developer"], ["fintech"], ["weekday_evening"], "partial"),
    ("Mei L.", "Mathematics", "senior", {"python": "advanced", "pytorch": "intermediate"}, ["ml-engineer", "data-scientist"], ["ai", "research"], ["weekday_evening", "weekend_afternoon"], "partial"),
    ("Omar H.", "Computer Science", "sophomore", {"javascript": "intermediate", "nodejs": "intermediate"}, ["backend-developer", "full-stack-developer"], ["gaming"], WEEKEND, "full"),
    ("Elena I.", "Cognitive Science", "junior", {"ux-research": "advanced", "figma": "intermediate"}, ["designer", "product-manager"], ["health"], WEEKEND, "full"),
    ("Dev S.", "Computer Science", "junior", {"react": "intermediate", "firebase": "intermediate"}, ["mobile-developer", "frontend-developer"], ["campus-life"], ["weekend_evening"], "full"),
    ("Chloe B.", "Business Analytics", "senior", {"data-analysis": "advanced", "sql": "advanced"}, ["data-scientist", "product-manager"], ["fintech"], WEEKEND, "partial"),
    ("Marcus J.", "Computer Science", "freshman", {"python": "beginner", "git": "beginner"}, ["backend-developer"], ["education"], WEEKEND, "full"),
    ("Nina V.", "Information Technology", "sophomore", {"htmlcss": "advanced", "react": "beginner"}, ["frontend-developer"], ["social-good"], WEEKEND, "partial"),
    ("Ravi T.", "Computer Science", "grad", {"tensorflow": "advanced", "python": "advanced", "nlp": "intermediate"}, ["ml-engineer"], ["ai"], ["weekday_evening"], "partial"),
    ("Grace Y.", "Computer Science", "junior", {"swift": "advanced"}, ["mobile-developer"], ["health"], WEEKEND, "full"),
    ("Kai N.", "Electrical Engineering", "senior", {"embedded-systems": "advanced", "c": "advanced"}, ["hardware-engineer"], ["hardwareiot", "climate"], WEEKEND, "full"),
    ("Leila H.", "Computer Science", "sophomore", {"python": "intermediate", "django": "beginner"}, ["backend-developer"], ["social-good"], ["weekday_evening"], "full"),
    ("Sam W.", "Computer Science", "junior", {"go": "intermediate", "docker": "intermediate"}, ["backend-developer"], ["developer-tools"], WEEKEND, "full"),
    ("Hana K.", "Design", "junior", {"figma": "advanced", "ux-research": "intermediate"}, ["designer"], ["education", "accessibility"], ["weekend_afternoon"], "full"),
    ("Ishaan D.", "Computer Science", "sophomore", {"python": "intermediate", "fastapi": "beginner"}, ["backend-developer"], ["ai"], WEEKEND, "partial"),
    ("Priyanka R.", "Data Science", "junior", {"python": "intermediate", "sql": "advanced", "data-analysis": "intermediate"}, ["data-scientist"], ["health"], WEEKEND, "full"),
    ("Tyler F.", "Computer Science", "senior", {"rust": "intermediate", "c": "intermediate"}, ["backend-developer"], ["cybersecurity"], ["weekday_evening"], "partial"),
    ("Ana L.", "Communication", "junior", {"public-speaking": "advanced", "technical-writing": "intermediate"}, ["pitch-and-presentation-lead"], ["social-good"], WEEKEND, "full"),
    ("Ben O.", "Computer Science", "junior", {"kotlin": "intermediate", "react-native": "beginner"}, ["mobile-developer"], ["gaming"], WEEKEND, "full"),
    ("Yuna P.", "Computer Science", "freshman", {"python": "beginner", "htmlcss": "beginner"}, ["frontend-developer"], ["education"], WEEKEND, "full"),
    ("Arjun K.", "Information Technology", "senior", {"aws": "intermediate", "docker": "advanced"}, ["backend-developer"], ["developer-tools"], WEEKEND, "partial"),
    ("Fatima Z.", "Computer Science", "sophomore", {"computer-vision": "intermediate", "python": "intermediate"}, ["ml-engineer"], ["accessibility", "ai"], ["weekend_morning"], "full"),
    ("Jake M.", "Business", "junior", {"project-management": "advanced", "public-speaking": "intermediate"}, ["product-manager"], ["fintech"], WEEKEND, "full"),
    ("Olivia N.", "Computer Science", "senior", {"mongodb": "intermediate", "nodejs": "advanced"}, ["backend-developer", "full-stack-developer"], ["productivity"], WEEKEND, "full"),
    ("Rohan S.", "Mathematics", "sophomore", {"python": "intermediate", "machine-learning": "intermediate"}, ["data-scientist", "ml-engineer"], ["research"], ["weekday_evening"], "partial"),
    ("Emma T.", "Design", "freshman", {"ui-design": "intermediate", "figma": "beginner"}, ["designer"], ["climate"], WEEKEND, "full"),
    ("David C.", "Computer Science", "junior", {"cpp": "advanced", "python": "beginner"}, ["backend-developer"], ["gaming"], ["weekend_evening"], "full"),
    ("Sara Q.", "Information Technology", "junior", {"tailwind-css": "advanced", "react": "intermediate"}, ["frontend-developer"], ["campus-life"], WEEKEND, "partial"),
    ("Victor A.", "Computer Science", "grad", {"postgresql": "advanced", "python": "intermediate"}, ["backend-developer"], ["research"], WEEKEND, "partial"),
    ("Lily H.", "Cognitive Science", "sophomore", {"ux-research": "intermediate"}, ["designer"], ["health"], WEEKEND, "full"),
    ("Kevin Z.", "Computer Science", "junior", {"flutter": "intermediate"}, ["mobile-developer"], ["social-good"], WEEKEND, "full"),
    ("Riya J.", "Data Science", "freshman", {"python": "beginner", "data-analysis": "beginner"}, ["data-scientist"], ["campus-life"], WEEKEND, "full"),
]

# Other open posts: (owner index, title, description, roles, required, preferred, interests, capacity, on_event)
POSTS = [
    (6, "Study Group Finder", "Match students in the same course section into study groups.", ["backend-developer", "designer"], ["react"], ["python", "figma"], ["education"], 4, True),
    (11, "Mental Health Check-ins", "Anonymous weekly check-ins that point students to campus resources.", ["backend-developer", "frontend-developer"], [], ["python", "react"], ["health"], 4, True),
    (18, "Energy Use Dashboard", "Show dorm energy use and run building-vs-building challenges.", ["backend-developer", "data-scientist"], ["python"], ["data-analysis", "django"], ["climate"], 4, True),
    (13, "Textbook Price Tracker", "Track used textbook prices across campus listings.", ["backend-developer", "frontend-developer"], [], ["sql", "react"], ["fintech", "campus-life"], 3, True),
    (9, "Lecture Note Summarizer", "Turn lecture recordings into searchable summaries.", ["ml-engineer", "backend-developer"], ["python"], ["machine-learning", "nlp"], ["ai", "education"], 4, False),
    (21, "Accessible Campus Map", "Routes that avoid stairs and out-of-service elevators.", ["frontend-developer", "backend-developer"], [], ["react", "postgresql"], ["accessibility", "campus-life"], 4, True),
    (30, "Club Event Finder", "One feed of events from every student org, filterable by major.", ["full-stack-developer", "designer"], [], ["nextjs", "figma"], ["campus-life"], 3, False),
]


class Command(BaseCommand):
    help = "Create the fixed showcase scenario: two presenter accounts, one hackathon, and a realistic campus."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete the previous showcase data first.")
        parser.add_argument(
            "--allow-real-data",
            action="store_true",
            help="Run even if the database has real students. Never use on the pilot database.",
        )

    def handle(self, *args, **options):
        showcase_users = self.showcase_users()
        real = User.objects.filter(is_staff=False).exclude(pk__in=showcase_users).exclude(email__startswith="demo-")
        if real.exists() and not options["allow_real_data"]:
            raise CommandError(
                f"This database has {real.count()} real student account(s). Run the showcase on a local "
                "database, or pass --allow-real-data if you're sure."
            )
        self.random = random.Random(2026)
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"):
            with transaction.atomic():
                if options["reset"]:
                    self.reset()
                elif showcase_users.exists():
                    raise CommandError("Showcase data already exists. Pass --reset to start fresh.")
                call_command("seed_catalog", stdout=io.StringIO())
                self.build()

        star = Opportunity.objects.get(title=STAR_POST, owner__email=OWNER_EMAIL)
        top = [m.candidate.display_name for m in rank_candidates(star)[:3]]
        self.stdout.write(self.style.SUCCESS("Showcase ready."))
        self.stdout.write(f"  Presenter (posts, reviews):  {OWNER_EMAIL}")
        self.stdout.write(f"  Presenter (browses, joins):  {JOINER_EMAIL}")
        self.stdout.write(f"  Event: {EVENT_NAME}    Star post: {STAR_POST}")
        self.stdout.write(f"  Top matches for the star post: {', '.join(top)}")
        self.stdout.write("  Sign-in codes print in the runserver terminal.")

    # ------------------------------------------------------------------ helpers

    def showcase_users(self):
        return User.objects.filter(Q(email__in=[OWNER_EMAIL, JOINER_EMAIL]) | Q(email__startswith=BACKGROUND_PREFIX))

    def reset(self):
        users = self.showcase_users()
        Opportunity.objects.filter(owner__in=users).delete()
        users.delete()
        Event.objects.filter(name=EVENT_NAME).delete()

    def make_student(self, email, name, major, year, skills, roles, interests, availability, commitment, *, discord=None, event=True):
        user = User.objects.create_user(
            email, display_name=name, major=major, year=year, availability=list(availability), commitment=commitment,
            bio="Showcase account. Not a real student.",
        )
        for slug, level in skills.items():
            UserSkill.objects.create(user=user, skill=self.skills[slug], proficiency=level)
        user.preferred_roles.set([self.roles[r] for r in roles])
        user.interests.set([self.interests[i] for i in interests])
        if event:
            EventInterest.objects.create(user=user, event=self.event, full_event=True)
        if discord:
            ContactMethod.objects.create(user=user, kind="discord", value=discord, is_preferred=True)
        return user

    def make_post(self, owner, title, description, roles, required, preferred, interests, capacity, *, on_event=True, days_left=6):
        now = timezone.now()
        post = Opportunity.objects.create(
            owner=owner, event=self.event if on_event else None, title=title, description=description,
            opportunity_type="hackathon" if on_event else "personal_project",
            availability=WEEKEND, commitment="full", team_capacity=capacity,
            expires_at=min(now + timedelta(days=days_left), self.event.recruiting_ends_at),
            published_at=now - timedelta(days=self.random.randint(0, 3)),
        )
        for slug in roles:
            OpportunityRole.objects.create(opportunity=post, role=self.roles[slug])
        for slug in required:
            OpportunitySkill.objects.create(opportunity=post, skill=self.skills[slug], requirement_type="required")
        for slug in preferred:
            OpportunitySkill.objects.create(opportunity=post, skill=self.skills[slug], requirement_type="preferred")
        post.interests.set([self.interests[i] for i in interests])
        return post

    # ------------------------------------------------------------------ the story

    def build(self):
        self.skills = {s.slug: s for s in Skill.objects.all()}
        self.roles = {r.slug: r for r in Role.objects.all()}
        self.interests = {i.slug: i for i in Interest.objects.all()}
        now = timezone.now()
        self.event = Event.objects.create(
            name=EVENT_NAME, description="Rutgers' student hackathon (showcase data).", venue="College Avenue Student Center",
            starts_at=now + timedelta(days=10), ends_at=now + timedelta(days=11), recruiting_ends_at=now + timedelta(days=9),
        )

        owner = self.make_student(
            OWNER_EMAIL, "Priya S.", "Computer Science", "junior",
            {"figma": "advanced", "ui-design": "advanced", "react": "intermediate"},
            ["designer", "frontend-developer"], ["campus-life", "ai"], WEEKEND, "full", discord="priya.designs",
        )
        joiner = self.make_student(
            JOINER_EMAIL, "Jordan T.", "Computer Science", "sophomore",
            {"python": "advanced", "django": "advanced", "postgresql": "intermediate", "machine-learning": "intermediate"},
            ["backend-developer", "ml-engineer"], ["campus-life", "ai"], WEEKEND, "full", discord="jordan.builds",
        )
        background = [
            self.make_student(
                f"{BACKGROUND_PREFIX}{n:02d}@{DOMAIN}", name, major, year, skills, roles, interests, avail, commit,
                discord=f"{name.split()[0].lower()}.{n:02d}" if n % 5 else None,  # every 5th has no contact method
                event=n % 3 != 0,
            )
            for n, (name, major, year, skills, roles, interests, avail, commit) in enumerate(STUDENTS, start=1)
        ]

        star = self.make_post(
            owner, STAR_POST,
            "Estimate line lengths at Busch, Livingston and Neilson dining halls from swipe data and post live "
            "wait times. I've got the UI designed; looking for people to build the backend and the prediction model.",
            ["backend-developer", "ml-engineer"], ["python"], ["django", "postgresql", "machine-learning"],
            ["campus-life", "ai"], 4,
        )
        others = [
            self.make_post(background[i], title, desc, roles, req, pref, ints, cap, on_event=on_event)
            for i, title, desc, roles, req, pref, ints, cap, on_event in POSTS
        ]

        # Existing activity so Requests isn't empty on stage.
        # Priya: one connection already accepted (shows revealed contact info) and one waiting for review.
        accepted = send_request(
            opportunity=star, sender=background[1], recipient=owner, kind="join",
            opportunity_role=star.roles.get(role__slug="ml-engineer"),
            message="I've done data analysis on campus datasets before and would love to work on the model.",
        )
        accepted = accept_request(accepted, actor=owner)
        rate_connection(accepted, user=owner, was_useful=True)
        send_request(
            opportunity=star, sender=background[0], recipient=owner, kind="join",
            opportunity_role=star.roles.get(role__slug="backend-developer"),
            message="Comfortable with Python and SQL, free all weekend.",
        )
        # Jordan: has already asked to join a different team, still pending.
        send_request(
            opportunity=others[2], sender=joiner, recipient=others[2].owner, kind="join",
            opportunity_role=others[2].roles.get(role__slug="backend-developer"),
            message="Happy to own the Django API.",
        )

        # The owners of other posts have looked at their matches, for the pilot metrics.
        for post in others:
            record_matches(rank_candidates(post), direction="candidates", viewer=post.owner)
