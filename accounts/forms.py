from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User


class RegisterForm(UserCreationForm):
    """
    Sign-up form. Collects the profile picture, phone number and
    WhatsApp number up front -- every account can list products for
    sale, and buyers need a reliable way to reach a seller, so all
    three are required. Email is also required, so an account can be
    recovered/contacted even if the phone/WhatsApp numbers change.
    """

    # Not a model field on purpose -- we don't save the checkbox value
    # itself, just require it to be checked before the form can be
    # submitted at all. The view sets user.agreed_to_terms = True once
    # this has passed validation, which is what actually gets stored.
    agree_to_terms = forms.BooleanField(
        required=True,
        label="",  # rendered manually in the template, with links inside it
        error_messages={
            "required": _("Ugomba kwemera amabwiriza n'amategeko mbere yo kwiyandikisha."),
        },
    )

    class Meta:
        model = User
        fields = ("username", "email", "profile_picture", "phone_number", "whatsapp_number")
        labels = {
            "username": _("Izina ukoresha"),
            "email": _("Imeli"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["agree_to_terms"].widget.attrs.update({"class": "form-check-input"})
        self.fields["email"].required = True
        self.fields["email"].widget.attrs.update({"placeholder": "izina@imeli.com"})
        self.fields["phone_number"].required = True
        self.fields["phone_number"].widget.attrs.update(
            {"placeholder": "+250 788 123 456"}
        )
        self.fields["whatsapp_number"].required = True
        self.fields["whatsapp_number"].widget.attrs.update(
            {"placeholder": "+250 788 123 456"}
        )
        self.fields["profile_picture"].widget.attrs.update({"accept": "image/*"})
        self.fields["password1"].label = _("Ijambobanga")
        self.fields["password1"].help_text = _(
            "Ijambobanga rigomba kuba rifite nibura inyuguti 8, ntirigomba kuba "
            "azwi cyane kandi ntirigomba kuba ari imibare gusa."
        )
        self.fields["password2"].label = _("Emeza ijambobanga")
        self.fields["password2"].help_text = _("Andika ijambobanga rimwe ryemeza uko waryanditse haruguru.")
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Hari konti isanzwe ikoresha iyi imeli."))
        return email


class LoginForm(AuthenticationForm):
    """AuthenticationForm with Kinyarwanda labels, since Django's
    built-in labels for this form aren't part of our translation
    catalog. Also blocks sign-in for accounts that haven't verified
    their email yet, using Django's own hook for exactly this kind of
    extra check (confirm_login_allowed runs after the username/
    password themselves have already checked out, so a wrong password
    still gets Django's normal "wrong credentials" error rather than
    leaking whether the account exists and is just unverified)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Izina ukoresha")
        self.fields["password"].label = _("Ijambobanga")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.email_verified:
            raise forms.ValidationError(
                _(
                    "Ugomba kwemeza imeli yawe mbere yo kwinjira. Reba imeli "
                    "twakoherereje, cyangwa usabe indi nk'iyo hepfo."
                ),
                code="email_not_verified",
            )


class ResendVerificationForm(forms.Form):
    """Just an email address -- used both right after signup (if the
    first email got lost) and from the "this link expired" page."""

    email = forms.EmailField(label=_("Imeli"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.setdefault("class", "form-control")


class EditAccountForm(forms.ModelForm):
    """Lets a signed-in user update their own profile details:
    picture, phone, WhatsApp, and email."""

    class Meta:
        model = User
        fields = ("profile_picture", "phone_number", "whatsapp_number", "email")
        labels = {
            "email": _("Imeli"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["phone_number"].required = True
        self.fields["whatsapp_number"].required = True
        self.fields["profile_picture"].widget.attrs.update({"accept": "image/*"})
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(_("Hari konti isanzwe ikoresha iyi imeli."))
        return email


class AccountDeleteForm(forms.Form):
    """Requires the user to re-enter their password before their
    account is permanently deleted, so a stray click (or someone else
    at an unlocked computer) can't destroy an account by accident."""

    password = forms.CharField(
        label=_("Ijambobanga"),
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Ijambobanga ntabwo ari ryo."))
        return password
