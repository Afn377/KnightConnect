from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    """Manager for email-based users.

    Students sign in with one-time codes, so regular users are created
    without a usable password. Superusers keep a password for the admin.
    """

    use_in_migrations = True

    def normalize_email(self, email):
        return (email or "").strip().lower()

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superusers must have is_staff and is_superuser set.")
        return self.create_user(email, password, **extra_fields)
