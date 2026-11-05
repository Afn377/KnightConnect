from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from catalog.models import Interest, Role, Skill
from core.choices import Commitment
from core.models import TimeStampedModel, UUIDModel
from core.validators import validate_availability_slots

from .managers import UserManager
from .validators import validate_rutgers_email


class User(UUIDModel, AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """A verified Rutgers student and their lightweight teammate profile.

    Profile fields live on the user row because every account has exactly
    one profile and matching reads them together.
    """

    email = models.EmailField(
        "Rutgers email",
        max_length=254,
        unique=True,
        validators=[validate_rutgers_email],
    )
    class Year(models.TextChoices):
        FRESHMAN = "freshman", "Freshman"
        SOPHOMORE = "sophomore", "Sophomore"
        JUNIOR = "junior", "Junior"
        SENIOR = "senior", "Senior"
        GRAD = "grad", "Graduate student"

    display_name = models.CharField(max_length=80, blank=True)
    major = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=10, choices=Year.choices, blank=True)
    bio = models.TextField(max_length=1000, blank=True)

    open_to_requests = models.BooleanField(
        default=True,
        help_text="Whether the student is in the active candidate pool for other teams.",
    )
    availability = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_availability_slots],
        help_text="List of AvailabilitySlot codes.",
    )
    commitment = models.CharField(max_length=20, choices=Commitment.choices, blank=True)

    preferred_roles = models.ManyToManyField(Role, blank=True, related_name="users")
    interests = models.ManyToManyField(Interest, blank=True, related_name="users")
    skills = models.ManyToManyField(Skill, through="UserSkill", blank=True, related_name="users")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    deletion_scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When set, the account is hidden and will be permanently deleted at this time "
        "unless the user signs in again first.",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        # Stored lowercase so the unique index is effectively case-insensitive.
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.email

    @property
    def is_profile_complete(self):
        return bool(self.display_name and self.availability and self.commitment)


class UserSkill(models.Model):
    class Proficiency(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_skills")
    proficiency = models.CharField(
        max_length=20, choices=Proficiency.choices, default=Proficiency.INTERMEDIATE
    )

    class Meta:
        ordering = ["skill__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "skill"], name="accounts_userskill_unique"),
        ]

    def __str__(self):
        return f"{self.user} - {self.skill} ({self.proficiency})"


class ContactMethod(TimeStampedModel):
    """A way to reach a student once a connection request is accepted.

    Contact methods are never exposed in browse or match results; they are
    revealed only to users with an accepted connection.
    """

    class Kind(models.TextChoices):
        EMAIL = "email", "Email"
        DISCORD = "discord", "Discord"
        LINKEDIN = "linkedin", "LinkedIn"
        PHONE = "phone", "Phone"
        OTHER = "other", "Other"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contact_methods")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    value = models.CharField(max_length=200)
    is_preferred = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_preferred", "kind"]
        constraints = [
            models.UniqueConstraint(fields=["user", "kind"], name="accounts_contactmethod_one_per_kind"),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_preferred=True),
                name="accounts_contactmethod_one_preferred",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.value}"


class LoginCode(models.Model):
    """A one-time sign-in code emailed to a Rutgers address.

    Only an HMAC of the code is stored. Requesting a new code replaces any
    outstanding one for the same email.
    """

    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Login code for {self.email}"
