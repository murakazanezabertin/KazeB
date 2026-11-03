from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext as _

from kazeb.imaging import compress_uploaded_image

from .forms import AccountDeleteForm, EditAccountForm, RegisterForm, ResendVerificationForm
from .models import User
from .tokens import email_verification_token


def _send_verification_email(request, user):
    """Emails a one-time "confirm your account" link. Used both right
    after signup and from the resend-verification page -- kept as one
    function so both call sites always build the link the same way."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    verify_path = request.build_absolute_uri(
        f"/accounts/verify/{uidb64}/{token}/"
    )
    subject = _("Emeza konti yawe kuri KazeB")
    message = render_to_string(
        "registration/verification_email.txt",
        {"user": user, "verify_url": verify_path},
    )
    send_mail(subject, message, None, [user.email])


def register(request):
    """Sign up, send a verification email, but don't log the user in
    yet -- they can't sign in until they click that link (see
    LoginForm.confirm_login_allowed)."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            # agree_to_terms isn't a model field (see RegisterForm), so
            # it doesn't get set by form.save() automatically -- but
            # form.is_valid() being True here already guarantees it was
            # checked, since the field is required.
            user.agreed_to_terms = True
            if "profile_picture" in request.FILES:
                user.profile_picture = compress_uploaded_image(
                    request.FILES["profile_picture"], max_dimension=800
                )
            user.save()
            _send_verification_email(request, user)
            return redirect("accounts:verification_sent")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


def verify_email(request, uidb64, token):
    """Handles the link from the verification email. A valid,
    not-yet-used token flips email_verified on and logs the user
    straight in; anything else (bad/expired/already-used token) shows
    a page offering to send a fresh one."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        login(request, user)
        messages.success(request, _("Imeli yawe yemejwe. Murakaza neza kuri KazeB!"))
        return redirect("core:home")

    return render(request, "registration/verification_invalid.html")


def resend_verification_email(request):
    """Standalone page (linked from login's error and from the
    invalid-link page) to request a fresh verification email.

    Always shows the same "if that account exists..." message whether
    or not the email matches a real, unverified account -- so this
    can't be used to check which emails are registered on KazeB."""
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(
                    email=form.cleaned_data["email"], email_verified=False
                )
                _send_verification_email(request, user)
            except User.DoesNotExist:
                pass
            return redirect("accounts:verification_sent")
    else:
        form = ResendVerificationForm()

    return render(request, "registration/resend_verification.html", {"form": form})


@login_required
def edit_account(request):
    """Let a signed-in user update their own profile: picture, phone,
    WhatsApp, and email."""
    if request.method == "POST":
        form = EditAccountForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            if "profile_picture" in request.FILES:
                user.profile_picture = compress_uploaded_image(
                    request.FILES["profile_picture"], max_dimension=800
                )
            user.save()
            messages.success(request, _("Impinduka ku konti yawe zabitswe."))
            return redirect("listings:dashboard")
    else:
        form = EditAccountForm(instance=request.user)

    return render(request, "registration/edit_account.html", {"form": form})


@login_required
def delete_account(request):
    """Permanently delete the signed-in user's account, after they
    re-enter their password to confirm. Cascades to their products,
    photos, and messages (see the FK on_delete=CASCADE on those
    models)."""
    if request.method == "POST":
        form = AccountDeleteForm(request.POST, user=request.user)
        if form.is_valid():
            user = request.user
            messages.success(request, _("Konti yawe yasibwe burundu."))
            logout(request)
            user.delete()
            return redirect("core:home")
    else:
        form = AccountDeleteForm(user=request.user)

    return render(request, "registration/delete_account.html", {"form": form})
