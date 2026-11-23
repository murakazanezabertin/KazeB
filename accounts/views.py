from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext as _t

from kazeb.imaging import compress_uploaded_image

from .forms import AccountDeleteForm, EditAccountForm, RegisterForm, ResendVerificationForm, VerifyCodeForm
from .models import EmailVerificationCode, User


def _send_verification_email(request, user):
    """Generates a 6-digit verification code and emails it to the user."""
    code, _ = EmailVerificationCode.generate_code(user)
    subject = _t("Emeza konti yawe kuri KazeB")
    message = render_to_string(
        "registration/verification_email.txt",
        {"user": user, "code": code},
    )
    send_mail(subject, message, None, [user.email])


def register(request):
    """Sign up, send a verification code, but don't log the user in
    yet -- they can't sign in until they verify the code."""
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
            return redirect("accounts:verify_code")
    else:
        form = RegisterForm()

    return render(request, "registration/register.html", {"form": form})


def verify_code(request):
    """Handle the 6-digit verification code entry."""
    if request.user.is_authenticated:
        return redirect("core:home")

    if request.method == "POST":
        form = VerifyCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"]
            # Find the user by checking unverified users with a valid code
            # We need to check all unverified users' codes
            users = User.objects.filter(email_verified=False).select_related("email_verification_code")
            verified_user = None
            for user in users:
                try:
                    evc = user.email_verification_code
                    if evc.verify_code(code):
                        verified_user = user
                        break
                except EmailVerificationCode.DoesNotExist:
                    continue

            if verified_user:
                verified_user.email_verified = True
                verified_user.save(update_fields=["email_verified"])
                login(request, verified_user, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, _t("Imeli yawe yemejwe. Murakaza neza kuri KazeB!"))
                return redirect("core:home")

            form.add_error("code", _t("Kode ntabwo ikora, yagize, cyangwa yamaze gukoreshwa."))
    else:
        form = VerifyCodeForm()

    return render(request, "registration/verify_code.html", {"form": form})


def resend_verification_email(request):
    """Standalone page to request a fresh verification code."""
    if request.method == "POST":
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(
                    email__iexact=form.cleaned_data["email"], email_verified=False
                )
                _send_verification_email(request, user)
            except User.DoesNotExist:
                pass
            return redirect("accounts:verify_code")
    else:
        form = ResendVerificationForm()

    return render(request, "registration/resend_verification.html", {"form": form})


@login_required
def edit_account(request):
    """Let a signed-in user update their own profile: picture, phone,
    WhatsApp, and email."""
    original_email = request.user.email
    if request.method == "POST":
        form = EditAccountForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            email_changed = user.email != original_email
            if email_changed:
                user.email_verified = False
            if "profile_picture" in request.FILES:
                user.profile_picture = compress_uploaded_image(
                    request.FILES["profile_picture"], max_dimension=800
                )
            user.save()
            if email_changed:
                _send_verification_email(request, user)
                logout(request)
                return redirect("accounts:verification_sent")
            messages.success(request, _t("Impinduka ku konti yawe zabitswe."))
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
            messages.success(request, _t("Konti yawe yasibwe burundu."))
            logout(request)
            user.delete()
            return redirect("core:home")
    else:
        form = AccountDeleteForm(user=request.user)

    return render(request, "registration/delete_account.html", {"form": form})
