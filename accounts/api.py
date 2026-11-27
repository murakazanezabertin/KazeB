import hashlib
import hmac
import logging
import smtplib
from datetime import datetime, timedelta, timezone as datetime_timezone

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.forms import (
    PasswordResetForm,
    SetPasswordForm,
)
from django.contrib.auth.tokens import default_token_generator
from django.core.mail.message import BadHeaderError
from django.db.models import F
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from accounts.forms import (
    AccountDeleteForm,
    EditAccountForm,
    LoginForm,
    RegisterForm,
    ResendVerificationForm,
    VerifyCodeForm,
)
from accounts.models import EmailVerificationCode, PasswordResetRateLimit, User
from accounts.views import _send_verification_email
from kazeb.imaging import compress_uploaded_image
from listings.api import _listing_card_payload
from listings.models import Favorite, Listing

User = get_user_model()
logger = logging.getLogger(__name__)

PASSWORD_RESET_WINDOW_SECONDS = 600
PASSWORD_RESET_EMAIL_LIMIT = 3
PASSWORD_RESET_IP_LIMIT = 10


def _form_errors(form):
    return {
        field: [str(error) for error in errors]
        for field, errors in form.errors.items()
    }


def _invalid_form(form):
    return JsonResponse(
        {"detail": _("Habaye ikibazo. Ongera ugerageze."), "errors": _form_errors(form)},
        status=400,
    )


def _private_json(data, status=200):
    response = JsonResponse(data, status=status)
    response["Cache-Control"] = "private, no-store"
    return response


def _password_reset_rate_limited(scope, value, limit, now):
    fingerprint = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"password-reset:{scope}:{value}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    window_epoch = (
        int(now.timestamp()) // PASSWORD_RESET_WINDOW_SECONDS
    ) * PASSWORD_RESET_WINDOW_SECONDS
    window_started_at = datetime.fromtimestamp(
        window_epoch, tz=datetime_timezone.utc
    )
    bucket, created = PasswordResetRateLimit.objects.get_or_create(
        scope=scope,
        fingerprint=fingerprint,
        window_started_at=window_started_at,
        defaults={"attempts": 1},
    )
    if created:
        return False

    updated = PasswordResetRateLimit.objects.filter(
        pk=bucket.pk,
        attempts__lt=limit,
    ).update(attempts=F("attempts") + 1)
    return updated == 0


def _account_payload(request, user):
    return {
        "username": user.get_username(),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "email_verified": user.email_verified,
        "agreed_to_terms": user.agreed_to_terms,
        "profile_picture": (
            request.build_absolute_uri(user.profile_picture.url)
            if user.profile_picture
            else None
        ),
        "location": user.location,
        "bio": user.bio,
        "phone_number": user.phone_number,
        "whatsapp_number": user.whatsapp_number,
        "is_phone_verified": user.is_phone_verified,
        "date_joined": user.date_joined.date().isoformat(),
    }


@require_GET
def auth_ui(request):
    register_form = RegisterForm()
    edit_form = EditAccountForm()
    return JsonResponse(
        {
            "labels": {
                "account": _("Umwirondoro wanjye"),
                "account_details": _("Umwirondoro wanjye"),
                "save_changes": _("Bika impinduka"),
                "delete_account": _("Siba Konti"),
                "confirm_delete": _(
                    "Iyi gikorwa gisiba burundu konti yawe, hamwe n'ibicuruzwa byose wagurishaga, amafoto yabyo, n'ubutumwa bwawe bwose. Ntibishobora gusubizwa inyuma."
                ),
                "cancel": _("Reka"),
                "login": _("Injira"),
                "register": _("Iyandikishe"),
                "username": _("Izina ukoresha"),
                "email": _("Imeli"),
                "password": _("Ijambobanga"),
                "password_confirmation": _("Emeza ijambobanga"),
                "forgot_password": _("Wibagiwe ijambobanga?"),
                "reset_password": _("Hindura ijambobanga"),
                "send_reset_link": _("Ohereza umurongo wo guhindura ijambobanga"),
                "new_password": _("Ijambobanga rishya"),
                "verification_sent": _(
                    "Twakoherereje umurongo wo kwemeza konti yawe. Kanda kuri wo kugira ngo winjire kuri KazeB."
                ),
                "resend_verification": _("Ohereza indi email yo kwemeza"),
                "resend": _("Ongera wohereze"),
                "verify_status": _("Imeli yemejwe"),
                "verified": _("Yemejwe"),
                "not_verified": _("Ntiyemejwe"),
                "terms_acceptance": _("Nemeye amabwiriza n'amategeko bya KazeB"),
                "terms": _("Amabwiriza"),
                "privacy": _("Ibanga"),
                "first_name": _("Izina"),
                "last_name": _("Izina ry'umuryango"),
                "profile_picture": _("Ifoto yawe"),
                "location": _("Aho uherereye"),
                "bio": _("Ibyo wivugaho"),
                "phone_number": _("Numero ya telefone"),
                "whatsapp_number": _("Numero ya WhatsApp"),
                "success": _("Impinduka zabitswe."),
                "account_deleted": _("Konti yawe yasibwe burundu."),
                "email_changed": _("Emeza imeli nshya twakoherereje kugira ngo wongere winjire."),
                "password_reset_sent": _(
                    "Niba imeli ijyanye na konti ihari, twohereje umurongo wo guhindura ijambobanga."
                ),
                "password_reset_complete": _("Ijambobanga ryawe ryahinduwe. Ushobora kwinjira ubu."),
                "password_reset_invalid": _(
                    "Uyu murongo wo guhindura ijambobanga ntabwo ukora, wenda kubera ko wamaze gukoreshwa."
                ),
                "verification_generic": _(
                    "Niba konti ihari kandi itaremezwa, twakoherereje imeli."
                ),
                "loading": _("Birimo gutegurwa..."),
                "current_password": _("Andika ijambobanga ryawe kugira ngo wemeze"),
                "listing_saved": _("Ibya kwibuka"),
                "no_favorites": _("Nta kintu urabika ku bya kwibuka."),
                "remove_favorite": _("Vana mu bya kwibuka"),
                "unavailable": _("Iki gicuruzwa ntikiboneka."),
                "terms_required": _("Ugomba kwemera amabwiriza n'amategeko mbere yo kwiyandikisha."),
            },
            "register_fields": {
                name: str(field.label)
                for name, field in register_form.fields.items()
            },
            "account_fields": {
                name: str(field.label)
                for name, field in edit_form.fields.items()
            },
            "terms_url": "/terms/",
            "privacy_url": "/privacy/",
        }
    )


@require_POST
def register_api(request):
    if request.user.is_authenticated:
        return JsonResponse({"detail": _("Konti isanzwe yinjiye.")}, status=400)

    form = RegisterForm(request.POST, request.FILES)
    if not form.is_valid():
        return _invalid_form(form)

    user = form.save(commit=False)
    user.agreed_to_terms = True
    if "profile_picture" in request.FILES:
        user.profile_picture = compress_uploaded_image(
            request.FILES["profile_picture"], max_dimension=800
        )
    user.save()
    _send_verification_email(request, user)
    return JsonResponse(
        {
            "detail": _("Iyandikishe byagenze neza. Reba imeli yawe kugira ngo wemeze konti yawe."),
            "verification_required": True,
        },
        status=201,
    )


@require_POST
def verify_code_api(request):
    form = VerifyCodeForm(request.POST)
    if not form.is_valid():
        return _invalid_form(form)

    code = form.cleaned_data["code"]
    users = User.objects.filter(
        email_verified=False,
        email_verification_code__isnull=False,
    ).select_related("email_verification_code")
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
        return JsonResponse(
            {
                "detail": _("Imeli yawe yemejwe. Murakaza neza kuri KazeB!"),
                "account": _account_payload(request, verified_user),
                "redirect_to": "/",
            }
        )

    return JsonResponse(
        {"detail": _("Kode ntabwo ikora, yagize, cyangwa yamaze gukoreshwa.")},
        status=400,
    )


@require_POST
def login_api(request):
    form = LoginForm(request=request, data=request.POST)
    if not form.is_valid():
        return _invalid_form(form)

    login(request, form.get_user())
    next_url = request.POST.get("next", "")
    redirect_to = (
        next_url
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
        else "/"
    )
    return JsonResponse(
        {
            "detail": _("Winjiye kuri KazeB."),
            "account": _account_payload(request, request.user),
            "redirect_to": redirect_to,
        }
    )


@require_POST
def logout_api(request):
    logout(request)
    return JsonResponse({"detail": _("Wasohotse kuri KazeB.")})


@require_POST
def resend_verification_api(request):
    form = ResendVerificationForm(request.POST)
    if not form.is_valid():
        return _invalid_form(form)

    try:
        user = User.objects.get(
            email__iexact=form.cleaned_data["email"], email_verified=False
        )
        _send_verification_email(request, user)
    except User.DoesNotExist:
        pass

    return JsonResponse(
        {
            "detail": _("Niba konti ihari kandi itaremezwa, twakoherereje kode nshya.")
        }
    )


@require_POST
def password_reset_request_api(request):
    now = timezone.now()
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    client_ip = (
        forwarded_for.split(",", 1)[0].strip()
        or request.META.get("REMOTE_ADDR", "unknown")
    )
    PasswordResetRateLimit.objects.filter(
        window_started_at__lt=now - timedelta(days=1)
    ).delete()

    if _password_reset_rate_limited(
        PasswordResetRateLimit.Scope.IP,
        client_ip,
        PASSWORD_RESET_IP_LIMIT,
        now,
    ):
        return _private_json(
            {
                "detail": _(
                    "Too many password reset requests. Please try again later."
                )
            },
            status=429,
        )

    form = PasswordResetForm(request.POST)
    if not form.is_valid():
        return _private_json(
            {
                "detail": _("Habaye ikibazo. Ongera ugerageze."),
                "errors": _form_errors(form),
            },
            status=400,
        )

    email = form.cleaned_data["email"].strip().casefold()
    if _password_reset_rate_limited(
        PasswordResetRateLimit.Scope.EMAIL,
        email,
        PASSWORD_RESET_EMAIL_LIMIT,
        now,
    ):
        return _private_json(
            {
                "detail": _(
                    "Too many password reset requests. Please try again later."
                )
            },
            status=429,
        )

    eligible_users = list(form.get_users(email))
    if eligible_users:
        try:
            form.save(
                request=request,
                use_https=request.is_secure(),
                subject_template_name="registration/password_reset_subject.txt",
                email_template_name="registration/password_reset_email.html",
                html_email_template_name=None,
            )
        except (BadHeaderError, OSError, smtplib.SMTPException):
            logger.exception("Password reset email delivery failed")
            return _private_json(
                {
                    "detail": _(
                        "Password reset is temporarily unavailable. Please try again later."
                    )
                },
                status=503,
            )

    if eligible_users:
        detail = _(
            "A password reset link has been sent to your email address. Please check your inbox."
        )
    else:
        detail = _(
            "No account exists with this email address. Please check your email or create an account."
        )
    return _private_json({"detail": detail})


@require_POST
def password_reset_confirm_api(request, uidb64, token):
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User._default_manager.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return JsonResponse(
            {
                "detail": _(
                    "Uyu murongo wo guhindura ijambobanga ntabwo ukora, wenda kubera ko wamaze gukoreshwa."
                )
            },
            status=400,
        )

    form = SetPasswordForm(user, request.POST)
    if not form.is_valid():
        return _invalid_form(form)

    form.save()
    return JsonResponse(
        {"detail": _("Ijambobanga ryawe ryahinduwe. Ushobora kwinjira ubu.")}
    )


@require_GET
def account_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": _("Ugomba kwinjira kugira ngo ukomeze.")}, status=401)
    return _private_json({"account": _account_payload(request, request.user)})


@require_POST
def edit_account_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": _("Ugomba kwinjira kugira ngo ukomeze.")}, status=401)

    original_email = request.user.email
    form = EditAccountForm(request.POST, request.FILES, instance=request.user)
    if not form.is_valid():
        return _invalid_form(form)

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
        return _private_json(
            {
                "detail": _("Emeza imeli nshya twakoherereje kugira ngo wongere winjire."),
                "email_verification_required": True,
            }
        )

    return _private_json(
        {"detail": _("Impinduka zabitswe."), "account": _account_payload(request, user)}
    )


@require_POST
def delete_account_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": _("Ugomba kwinjira kugira ngo ukomeze.")}, status=401)

    form = AccountDeleteForm(request.POST, user=request.user)
    if not form.is_valid():
        return _invalid_form(form)

    user = request.user
    logout(request)
    user.delete()
    return JsonResponse({"detail": _("Konti yawe yasibwe burundu.")})


@require_GET
def favorites_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": _("Ugomba kwinjira kugira ngo ukomeze.")}, status=401)

    favorites = (
        Favorite.objects.filter(user=request.user)
        .select_related("listing", "listing__seller")
        .prefetch_related("listing__images")
    )
    page_obj = Paginator(favorites, 12).get_page(request.GET.get("page"))
    return _private_json(
        {
            "results": [
                {
                    "listing": _listing_card_payload(favorite.listing),
                    "is_active": favorite.listing.is_active,
                }
                for favorite in page_obj
            ],
            "pagination": {
                "page": page_obj.number,
                "pages": page_obj.paginator.num_pages,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )


@require_POST
def toggle_favorite_api(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": _("Ugomba kwinjira kugira ngo ukomeze.")}, status=401)

    listing = get_object_or_404(Listing, pk=pk)
    favorite = Favorite.objects.filter(user=request.user, listing=listing).first()
    if favorite:
        favorite.delete()
        return _private_json({"is_favorited": False})
    if (
        not listing.is_active
        or listing.moderation_status != Listing.ModerationStatus.VISIBLE
    ):
        return JsonResponse({"detail": _("Igicuruzwa nticyabonetse.")}, status=404)
    Favorite.objects.create(user=request.user, listing=listing)
    return _private_json({"is_favorited": True})
