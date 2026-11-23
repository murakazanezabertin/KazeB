
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, DatabaseError, transaction
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import hashlib
import hmac
import secrets


def default_email_expiry():
    return timezone.now() + timezone.timedelta(minutes=10)


class User(AbstractUser):
    """
    Custom user model. Extends Django's built-in user with the contact
    details a seller needs to provide so buyers can reach them: a
    profile picture, a phone number (shown to buyers to call/copy),
    and a WhatsApp number (used to build the "chat on WhatsApp" deep
    link) -- both required at sign-up since every account can list
    products for sale.
    """

    profile_picture = models.ImageField(
        _("Ifoto yawe"),
        upload_to="profiles/",
        blank=True,
        null=True,
    )
    location = models.CharField(
        _("Aho uherereye"),
        max_length=150,
        blank=True,
    )
    bio = models.TextField(
        _("Ibyo wivugaho"),
        max_length=500,
        blank=True,
    )
    phone_number = models.CharField(
        _("Numero ya telefone"),
        max_length=20,
        blank=True,
        help_text=_(
            "Igaragara ku baguzi ku byo ugurisha, urugero: +250788123456"
        ),
    )
    whatsapp_number = models.CharField(
        _("Numero ya WhatsApp"),
        max_length=20,
        blank=True,
        help_text=_(
            "Abaguzi bazabona buto yo 'Kuvugana kuri WhatsApp' "
            "hakoreshejwe iyi numero."
        ),
    )
    agreed_to_terms = models.BooleanField(
        _("Yemeye amabwiriza"),
        default=False,
        help_text=_(
            "Yagaragaje ko yemeye amabwiriza n'amategeko "
            "igihe yiyandikishaga."
        ),
    )
    email_verified = models.BooleanField(
        _("Imeli yemejwe"),
        default=False,
        help_text=_(
            "Yakanze umurongo wo kwemeza wo muri imeli ye. "
            "Ntabwo ashobora kwinjira kugeza iyi imeli yemejwe."
        ),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="unique_user_email_ci",
            )
        ]
        permissions = [
            ("suspend_user", "Can suspend and reactivate user accounts"),
        ]

    def whatsapp_digits(self):
        """Digits only, for building a wa.me/<number> link."""
        return "".join(
            ch for ch in self.whatsapp_number if ch.isdigit()
        )

    @property
    def is_phone_verified(self):
        """Whether this user completed the phone-number OTP check
        (trust.models.PhoneVerification). Uses the reverse relation
        rather than importing the trust app directly, so accounts
        doesn't need to depend on it."""
        try:
            return self.phone_verification.is_verified
        except ObjectDoesNotExist:
            return False

    def __str__(self):
        return self.username


class EmailVerificationCode(models.Model):
    """
    Stores a hashed 6-digit verification code for email verification.
    Each code can only be used once, expires after 10 minutes,
    and has a maximum of 5 verification attempts.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_code",
    )
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_email_expiry)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=("expires_at",)),
        ]

    def is_valid(self):
        """Check if the code is still valid (not expired, not used, attempts not exceeded)."""
        now = timezone.now()
        return (
            self.used_at is None
            and self.expires_at > now
            and self.attempts < self.max_attempts
        )

    def verify_code(self, code: str) -> bool:
        """Verify a plain code against the stored hash. Returns True if valid."""
        if not self.is_valid():
            return False
        self.attempts += 1
        try:
            with transaction.atomic():
                self.save(update_fields=["attempts"])
        except DatabaseError:
            # Object was deleted (e.g., by generate_code)
            return False
        # Verify using constant-time comparison
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if hmac.compare_digest(code_hash, self.code_hash):
            self.used_at = timezone.now()
            try:
                with transaction.atomic():
                    self.save(update_fields=["used_at"])
            except DatabaseError:
                pass
            return True
        return False

    @classmethod
    def generate_code(cls, user: User) -> tuple[str, "EmailVerificationCode"]:
        """Generate a new 6-digit code, invalidate any existing one."""
        # Invalidate existing code if any
        cls.objects.filter(user=user).delete()

        # Generate cryptographically secure 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = hashlib.sha256(code.encode()).hexdigest()

        obj = cls.objects.create(
            user=user,
            code_hash=code_hash,
        )
        return code, obj


class PasswordResetRateLimit(models.Model):
    class Scope(models.TextChoices):
        IP = "ip", "IP address"
        EMAIL = "email", "Email address"

    scope = models.CharField(max_length=8, choices=Scope.choices)
    fingerprint = models.CharField(max_length=64)
    window_started_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("scope", "fingerprint", "window_started_at"),
                name="unique_password_reset_rate_bucket",
            )
        ]
        indexes = [
            models.Index(fields=("window_started_at",)),
        ]
