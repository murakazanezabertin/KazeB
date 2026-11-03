import secrets

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from listings.models import Listing

from .forms import PhoneVerifyForm, ReportForm, ReviewForm
from .models import PhoneVerification, Report, Review, default_expiry
from .sms import send_verification_sms

User = get_user_model()


def _rate_limited(key, limit, window_seconds):
    """
    Very small dependency-free rate limiter built on Django's cache
    framework. Returns True (and does NOT count the attempt) if the
    caller has already hit `limit` attempts within `window_seconds`.
    Uses the default in-memory cache, which is per-process -- fine for
    a single-process deployment; use a shared cache (Redis) in
    production if you run more than one worker, or each worker will
    enforce its own separate limit.
    """
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, window_seconds)
    return False


@login_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if request.method == "POST":
        # Bind the form to an instance that already has `listing` set,
        # not a blank Report(). Report.clean() (which requires a
        # listing or reported_user) runs automatically as part of
        # form.is_valid() -- if `listing` were only set afterwards (as
        # this used to do), that clean() would always fail and every
        # report would silently be rejected.
        form = ReportForm(request.POST, instance=Report(listing=listing))
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.save()
            messages.success(request, _("Murakoze. Twakiriye raporo yanyu."))
            return redirect(listing.get_absolute_url())
    else:
        form = ReportForm()

    return render(request, "trust/report_form.html", {"form": form, "listing": listing})


@login_required
def add_review(request, user_id):
    seller = get_object_or_404(User, pk=user_id)

    if seller == request.user:
        messages.error(request, _("Ntushobora kwisuzuma wenyine."))
        return redirect("core:home")

    existing = Review.objects.filter(reviewer=request.user, seller=seller).first()

    if request.method == "POST":
        # Same fix as report_listing: bind to an instance that already
        # has reviewer/seller set, since Review.clean() (which blocks
        # self-reviews) runs automatically inside form.is_valid() --
        # before this view used to set those fields, so it always
        # raised "You can't review yourself" and silently dropped
        # every submitted rating.
        instance = existing or Review(reviewer=request.user, seller=seller)
        form = ReviewForm(request.POST, instance=instance)
        if form.is_valid():
            review = form.save()
            messages.success(request, _("Ubusuzumire bwawe bwabitswe."))
            return redirect("trust:seller_reviews", user_id=seller.pk)
    else:
        form = ReviewForm(instance=existing)

    return render(
        request,
        "trust/review_form.html",
        {"form": form, "seller": seller, "editing": existing is not None},
    )


def seller_reviews(request, user_id):
    seller = get_object_or_404(User, pk=user_id)
    reviews = Review.objects.filter(seller=seller).select_related("reviewer")
    average = None
    if reviews:
        average = sum(r.rating for r in reviews) / len(reviews)
    return render(
        request,
        "trust/seller_reviews.html",
        {"seller": seller, "reviews": reviews, "average": average},
    )


@login_required
@require_POST
def request_phone_verification(request):
    """Sends (or resends) a 6-digit code to the user's phone number.
    Rate-limited to 3 requests per 10 minutes per account so this
    can't be used to spam a phone number or exhaust SMS credit."""
    user = request.user

    if getattr(user, "is_phone_verified", False):
        messages.info(request, _("Numero yawe yarahamagawe."))
        return redirect("listings:dashboard")

    if _rate_limited(f"otp-request:{user.pk}", limit=3, window_seconds=600):
        messages.error(request, _("Wasabye kode nyinshi. Tegereza gato hanyuma ugerageze."))
        return redirect("trust:verify_phone")

    code = f"{secrets.randbelow(1000000):06d}"
    verification, _created = PhoneVerification.objects.update_or_create(
        user=user,
        defaults={
            "code": code,
            "is_verified": False,
            "attempts": 0,
            "created_at": timezone.now(),
        },
    )
    # update_or_create doesn't re-run the model's default for
    # expires_at on update, so set it explicitly.
    verification.expires_at = default_expiry()
    verification.save(update_fields=["expires_at"])

    send_verification_sms(user, code)
    messages.success(request, _("Kode yoherejwe. Reba ubutumwa bwawe."))
    return redirect("trust:verify_phone")


@login_required
def verify_phone(request):
    user = request.user

    if getattr(user, "is_phone_verified", False):
        messages.info(request, _("Numero yawe yarahamagawe."))
        return redirect("listings:dashboard")

    verification = PhoneVerification.objects.filter(user=user).first()
    code_sent = bool(verification and verification.code and not verification.is_expired())

    if not code_sent:
        return render(request, "trust/verify_phone.html", {"code_sent": False})

    if request.method == "POST":
        form = PhoneVerifyForm(request.POST, verification=verification)
        if form.is_valid():
            verification.is_verified = True
            verification.save(update_fields=["is_verified"])
            messages.success(request, _("Numero yawe yemejwe neza!"))
            return redirect("listings:dashboard")
    else:
        form = PhoneVerifyForm(verification=verification)

    return render(request, "trust/verify_phone.html", {"form": form, "code_sent": True})
