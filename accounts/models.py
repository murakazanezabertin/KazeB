from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
    location = models.CharField(_("Aho uherereye"), max_length=150, blank=True)
    bio = models.TextField(_("Ibyo wivugaho"), max_length=500, blank=True)
    phone_number = models.CharField(
        _("Numero ya telefone"),
        max_length=20,
        blank=True,
        help_text=_("Igaragara ku baguzi ku byo ugurisha, urugero: +250788123456"),
    )
    whatsapp_number = models.CharField(
        _("Numero ya WhatsApp"),
        max_length=20,
        blank=True,
        help_text=_("Abaguzi bazabona buto yo 'Kuvugana kuri WhatsApp' hakoreshejwe iyi numero."),
    )
    agreed_to_terms = models.BooleanField(
        _("Yemeye amabwiriza"),
        default=False,
        help_text=_("Yagaragaje ko yemeye amabwiriza n'amategeko igihe yiyandikishaga."),
    )
    email_verified = models.BooleanField(
        _("Imeli yemejwe"),
        default=False,
        help_text=_(
            "Yakanze umurongo wo kwemeza wo muri imeli ye. Ntabwo ashobora "
            "kwinjira kugeza iyi imeli yemejwe."
        ),
    )

    def whatsapp_digits(self):
        """Digits only, for building a wa.me/<number> link."""
        return "".join(ch for ch in self.whatsapp_number if ch.isdigit())

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
