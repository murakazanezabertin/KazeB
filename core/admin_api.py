import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from listings.models import Listing
from trust.audit import record_admin_activity
from trust.models import AdminAuditLog, Report, Review

User = get_user_model()
PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _admin_error(detail, status):
    response = JsonResponse({"detail": detail}, status=status)
    response["Cache-Control"] = "private, no-store"
    return response


def _admin_json(payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "private, no-store"
    return response


def _require_admin(request, *permissions):
    if not request.user.is_authenticated:
        return _admin_error(_("Authentication is required."), 401)
    if not request.user.is_staff or not request.user.has_perms(permissions):
        return _admin_error(_("You do not have permission to access this resource."), 403)
    return None


def _json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _paginate(request, queryset, serialize):
    try:
        page_number = int(request.GET.get("page", "1"))
        page_size = int(request.GET.get("page_size", PAGE_SIZE))
    except (TypeError, ValueError):
        return None
    if page_number < 1 or page_size < 1:
        return None
    paginator = Paginator(queryset, min(page_size, MAX_PAGE_SIZE))
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        return None
    except EmptyPage:
        page = paginator.page(paginator.num_pages or 1)
    return {
        "results": [serialize(item) for item in page.object_list],
        "pagination": {
            "page": page.number,
            "pages": paginator.num_pages,
            "count": paginator.count,
            "has_next": page.has_next(),
            "has_previous": page.has_previous(),
        },
    }


def _search(request, queryset, fields):
    query = request.GET.get("q", "").strip()
    if len(query) > 150:
        return None
    if query:
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(condition)
    return queryset


def _parse_date_filter(request, queryset, field, query_name, lookup):
    value = request.GET.get(query_name, "").strip()
    if not value:
        return queryset, None
    parsed = parse_date(value)
    if parsed is None:
        return None, _admin_error(_("Enter a valid date."), 400)
    return queryset.filter(**{f"{field}__date__{lookup}": parsed}), None


def _user_payload(user):
    return {
        "id": user.pk,
        "username": user.get_username(),
        "email": user.email,
        "phone_number": user.phone_number,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "email_verified": user.email_verified,
        "is_phone_verified": user.is_phone_verified,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
    }


def _listing_payload(listing):
    image = listing.cover_image
    return {
        "id": listing.pk,
        "name": listing.name,
        "description": listing.description,
        "price": listing.display_price,
        "condition": listing.get_condition_display(),
        "category": listing.category.name,
        "district": listing.district,
        "sector": listing.sector,
        "is_active": listing.is_active,
        "moderation_status": listing.moderation_status,
        "moderation_reason": listing.moderation_reason,
        "moderated_at": listing.moderated_at.isoformat() if listing.moderated_at else None,
        "created_at": listing.created_at.isoformat(),
        "image": image.image.url if image else None,
        "seller": {
            "id": listing.seller_id,
            "username": listing.seller.get_username(),
            "email": listing.seller.email,
            "phone_number": listing.seller.phone_number,
        },
    }


def _report_payload(report):
    target = None
    if report.listing_id:
        target = {
            "type": "listing",
            "id": report.listing_id,
            "label": report.listing.name,
        }
    elif report.reported_user_id:
        target = {
            "type": "user",
            "id": report.reported_user_id,
            "label": report.reported_user.get_username(),
        }
    return {
        "id": report.pk,
        "reporter": report.reporter.get_username(),
        "reporter_id": report.reporter_id,
        "target": target,
        "reason": report.get_reason_display(),
        "details": report.details,
        "evidence": [],
        "status": report.status,
        "decision_notes": report.decision_notes or report.resolution_notes,
        "handled_by": report.handled_by.get_username() if report.handled_by else None,
        "handled_at": report.handled_at.isoformat() if report.handled_at else None,
        "created_at": report.created_at.isoformat(),
    }


def _audit_payload(entry):
    return {
        "id": entry.pk,
        "action": entry.get_action_display(),
        "action_code": entry.action,
        "target_type": entry.target_type,
        "target_id": entry.target_id,
        "target_label": entry.target_label,
        "reason": entry.reason,
        "actor": entry.actor.get_username() if entry.actor else None,
        "created_at": entry.created_at.isoformat(),
    }


def _audit(request, action, target, target_type, target_label, reason="", details=None):
    return record_admin_activity(
        actor=request.user,
        action=action,
        target_type=target_type,
        target_id=target.pk,
        target_label=target_label,
        reason=reason,
        details=details,
    )


@require_GET
def admin_overview_api(request):
    denied = _require_admin(
        request,
        "trust.view_admin_dashboard",
        "accounts.view_user",
        "listings.view_listing",
        "trust.view_report",
        "trust.view_review",
        "trust.view_phoneverification",
        "trust.view_adminauditlog",
    )
    if denied:
        return denied

    now = timezone.now()
    start_date = (now - timedelta(days=6)).date()
    registration_trend = (
        User.objects.filter(date_joined__date__gte=start_date)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by("day")
    )
    listing_trend = (
        Listing.objects.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(total=Count("pk"))
        .order_by("day")
    )
    report_totals = Report.objects.aggregate(
        total=Count("pk"),
        pending=Count("pk", filter=Q(status__in=(Report.Status.PENDING, Report.Status.UNDER_REVIEW))),
        under_review=Count("pk", filter=Q(status=Report.Status.UNDER_REVIEW)),
        resolved=Count("pk", filter=Q(status=Report.Status.RESOLVED)),
        rejected=Count("pk", filter=Q(status=Report.Status.REJECTED)),
    )
    listing_totals = Listing.objects.aggregate(
        total=Count("pk"),
        active=Count(
            "pk",
            filter=Q(
                is_active=True,
                moderation_status=Listing.ModerationStatus.VISIBLE,
            ),
        ),
        hidden=Count(
            "pk",
            filter=~Q(moderation_status=Listing.ModerationStatus.VISIBLE),
        ),
        inactive=Count(
            "pk",
            filter=Q(
                is_active=False,
                moderation_status=Listing.ModerationStatus.VISIBLE,
            ),
        ),
        removed=Count("pk", filter=Q(moderation_status=Listing.ModerationStatus.REMOVED)),
    )
    user_totals = User.objects.aggregate(
        total=Count("pk"),
        verified=Count("pk", filter=Q(email_verified=True)),
        unverified=Count("pk", filter=Q(email_verified=False)),
    )
    recent_users = list(
        User.objects.select_related("phone_verification").order_by("-date_joined")[:5]
    )
    recent_listings = list(
        Listing.objects.select_related("seller", "category")
        .prefetch_related("images")
        .order_by("-created_at")[:5]
    )
    recent_reports = list(
        Report.objects.select_related("reporter", "listing", "reported_user")
        .order_by("-created_at")[:5]
    )

    activity = []
    for user in recent_users:
        activity.append(
            {
                "at": user.date_joined,
                "type": "registration",
                "title": _("New registration: %(username)s") % {"username": user.get_username()},
            }
        )
    for listing in recent_listings:
        activity.append(
            {
                "at": listing.created_at,
                "type": "listing",
                "title": _("New listing: %(name)s") % {"name": listing.name},
            }
        )
    for report in recent_reports:
        activity.append(
            {
                "at": report.created_at,
                "type": "report",
                "title": _("New report #%(report_id)s") % {"report_id": report.pk},
            }
        )
    audit_entries = list(
        AdminAuditLog.objects.select_related("actor").order_by("-created_at")[:10]
    )
    for entry in audit_entries:
        activity.append(
            {
                "at": entry.created_at,
                "type": "admin",
                "title": _("%(action)s: %(target)s")
                % {"action": entry.get_action_display(), "target": entry.target_label},
            }
        )
    activity.sort(key=lambda item: item["at"], reverse=True)

    payload = {
        "statistics": {
            "users": user_totals,
            "listings": listing_totals,
            "reports": report_totals,
            "reviews": Review.objects.count(),
            "verified_phones": User.objects.filter(
                phone_verification__is_verified=True
            ).count(),
            "unverified_phones": User.objects.filter(
                Q(phone_verification__isnull=True)
                | Q(phone_verification__is_verified=False)
            ).count(),
        },
        "registration_trend": [
            {"date": item["day"].isoformat(), "total": item["total"]}
            for item in registration_trend
        ],
        "listing_trend": [
            {"date": item["day"].isoformat(), "total": item["total"]}
            for item in listing_trend
        ],
        "recent_registrations": [_user_payload(user) for user in recent_users],
        "recent_listings": [_listing_payload(listing) for listing in recent_listings],
        "recent_activity": [
            {
                "type": item["type"],
                "title": item["title"],
                "created_at": item["at"].isoformat(),
            }
            for item in activity[:12]
        ],
        "permissions": {
            "users": request.user.has_perm("accounts.view_user"),
            "suspend_users": request.user.has_perm("accounts.suspend_user"),
            "listings": request.user.has_perm("listings.view_listing"),
            "moderate_listings": request.user.has_perm("listings.moderate_listing"),
            "remove_listings": request.user.has_perm("listings.remove_listing"),
            "reports": request.user.has_perm("trust.view_report"),
            "manage_reports": request.user.has_perm("trust.manage_report"),
            "reviews": request.user.has_perm("trust.view_review"),
            "remove_reviews": request.user.has_perm("trust.delete_review"),
            "phones": request.user.has_perm("trust.view_phoneverification"),
            "activity": request.user.has_perm("trust.view_adminauditlog"),
        },
    }
    return _admin_json(payload)


@require_GET
def admin_users_api(request):
    denied = _require_admin(request, "accounts.view_user")
    if denied:
        return denied
    users = User.objects.select_related("phone_verification").order_by("-date_joined")
    users = _search(request, users, ("username", "email", "phone_number"))
    if users is None:
        return _admin_error(_("Search text is too long."), 400)
    verified = request.GET.get("verified", "")
    if verified not in ("", "verified", "unverified"):
        return _admin_error(_("Invalid verification filter."), 400)
    if verified:
        users = users.filter(email_verified=(verified == "verified"))
    users, error = _parse_date_filter(
        request, users, "date_joined", "joined_from", "gte"
    )
    if error:
        return error
    users, error = _parse_date_filter(request, users, "date_joined", "joined_to", "lte")
    if error:
        return error
    joined_from = parse_date(request.GET.get("joined_from", ""))
    joined_to = parse_date(request.GET.get("joined_to", ""))
    if joined_from and joined_to and joined_from > joined_to:
        return _admin_error(_("The start date must not be after the end date."), 400)
    page = _paginate(request, users, _user_payload)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)


@require_GET
def admin_user_detail_api(request, user_id):
    denied = _require_admin(
        request,
        "accounts.view_user",
        "listings.view_listing",
        "trust.view_report",
        "trust.view_review",
    )
    if denied:
        return denied
    try:
        user = User.objects.select_related("phone_verification").get(pk=user_id)
    except User.DoesNotExist:
        return _admin_error(_("User not found."), 404)
    listings = (
        Listing.objects.filter(seller=user)
        .select_related("category", "seller")
        .prefetch_related("images")
        .order_by("-created_at")[:10]
    )
    reports = (
        Report.objects.filter(
            Q(reported_user=user) | Q(listing__seller=user)
        )
        .select_related("reporter", "listing", "reported_user", "handled_by")
        .order_by("-created_at")[:10]
    )
    report_count = Report.objects.filter(reported_user=user).count()
    listing_report_count = Report.objects.filter(listing__seller=user).count()
    activity = []
    for listing in Listing.objects.filter(seller=user).order_by("-created_at")[:5]:
        activity.append(
            {
                "at": listing.created_at,
                "type": "listing",
                "title": _("Listed %(name)s") % {"name": listing.name},
            }
        )
    for report in Report.objects.filter(
        Q(reporter=user) | Q(reported_user=user) | Q(listing__seller=user)
    ).order_by("-created_at")[:5]:
        activity.append(
            {
                "at": report.created_at,
                "type": "report",
                "title": _("Report activity #%(report_id)s") % {"report_id": report.pk},
            }
        )
    for review in Review.objects.filter(Q(reviewer=user) | Q(seller=user)).select_related(
        "reviewer", "seller"
    ).order_by("-created_at")[:5]:
        activity.append(
            {
                "at": review.created_at,
                "type": "review",
                "title": _("Review activity with %(username)s")
                % {
                    "username": (
                        review.seller.get_username()
                        if review.reviewer_id == user.pk
                        else review.reviewer.get_username()
                    )
                },
            }
        )
    activity.sort(key=lambda item: item["at"], reverse=True)
    return _admin_json(
        {
            "user": _user_payload(user),
            "statistics": {
                "listings": Listing.objects.filter(seller=user).count(),
                "reviews_received": Review.objects.filter(seller=user).count(),
                "reports_received": report_count + listing_report_count,
            },
            "listings": [_listing_payload(listing) for listing in listings],
            "reports": [_report_payload(report) for report in reports],
            "activity": [
                {
                    "type": item["type"],
                    "title": item["title"],
                    "created_at": item["at"].isoformat(),
                }
                for item in activity[:10]
            ],
        }
    )


@require_POST
def admin_user_status_api(request, user_id):
    denied = _require_admin(request, "accounts.suspend_user")
    if denied:
        return denied
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return _admin_error(_("User not found."), 404)
    if user.pk == request.user.pk or user.is_staff:
        return _admin_error(_("Administrator accounts cannot be suspended here."), 400)
    data = _json_body(request)
    if data is None or type(data.get("is_active")) is not bool:
        return _admin_error(_("Provide a valid account status."), 400)
    reason = str(data.get("reason", "")).strip()
    if not reason or len(reason) > 1000:
        return _admin_error(_("A moderation reason of up to 1000 characters is required."), 400)
    next_active = data["is_active"]
    if user.is_active == next_active:
        return _admin_error(_("The account already has this status."), 400)
    with transaction.atomic():
        user.is_active = next_active
        user.save(update_fields=["is_active"])
        _audit(
            request,
            AdminAuditLog.Action.USER_REACTIVATED if next_active else AdminAuditLog.Action.USER_SUSPENDED,
            user,
            "user",
            user.get_username(),
            reason,
        )
    return _admin_json({"user": _user_payload(user)})


@require_GET
def admin_listings_api(request):
    denied = _require_admin(request, "listings.view_listing")
    if denied:
        return denied
    listings = Listing.objects.select_related("seller", "category").prefetch_related("images")
    listings = _search(
        request,
        listings,
        ("name", "description", "seller__username", "seller__email", "seller__phone_number"),
    )
    if listings is None:
        return _admin_error(_("Search text is too long."), 400)
    status = request.GET.get("status", "")
    if status == "active":
        listings = listings.filter(is_active=True, moderation_status=Listing.ModerationStatus.VISIBLE)
    elif status == "hidden":
        listings = listings.filter(moderation_status=Listing.ModerationStatus.HIDDEN)
    elif status == "removed":
        listings = listings.filter(moderation_status=Listing.ModerationStatus.REMOVED)
    elif status == "inactive":
        listings = listings.filter(
            is_active=False,
            moderation_status=Listing.ModerationStatus.VISIBLE,
        )
    elif status:
        return _admin_error(_("Invalid listing status filter."), 400)
    page = _paginate(request, listings, _listing_payload)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)


@require_GET
def admin_listing_detail_api(request, listing_id):
    denied = _require_admin(request, "listings.view_listing")
    if denied:
        return denied
    try:
        listing = Listing.objects.select_related("seller", "category").prefetch_related("images").get(pk=listing_id)
    except Listing.DoesNotExist:
        return _admin_error(_("Listing not found."), 404)
    return _admin_json({"listing": _listing_payload(listing)})


@require_POST
def admin_listing_moderation_api(request, listing_id):
    data = _json_body(request)
    if data is None:
        return _admin_error(_("Invalid request data."), 400)
    action = data.get("action")
    permission = "listings.remove_listing" if action == "remove" else "listings.moderate_listing"
    denied = _require_admin(request, permission)
    if denied:
        return denied
    try:
        listing = Listing.objects.select_related("seller", "category").prefetch_related("images").get(pk=listing_id)
    except Listing.DoesNotExist:
        return _admin_error(_("Listing not found."), 404)
    actions = {
        "hide": (Listing.ModerationStatus.HIDDEN, AdminAuditLog.Action.LISTING_HIDDEN),
        "restore": (Listing.ModerationStatus.VISIBLE, AdminAuditLog.Action.LISTING_RESTORED),
        "remove": (Listing.ModerationStatus.REMOVED, AdminAuditLog.Action.LISTING_REMOVED),
    }
    if action not in actions:
        return _admin_error(_("Invalid moderation action."), 400)
    reason = str(data.get("reason", "")).strip()
    if not reason or len(reason) > 1000:
        return _admin_error(_("A moderation reason of up to 1000 characters is required."), 400)
    status, audit_action = actions[action]
    if listing.moderation_status == status:
        return _admin_error(_("The listing already has this moderation status."), 400)
    with transaction.atomic():
        listing.moderation_status = status
        listing.moderation_reason = reason
        listing.moderated_by = request.user
        listing.moderated_at = timezone.now()
        listing.save(
            update_fields=[
                "moderation_status",
                "moderation_reason",
                "moderated_by",
                "moderated_at",
                "updated_at",
            ]
        )
        _audit(request, audit_action, listing, "listing", listing.name, reason)
    return _admin_json({"listing": _listing_payload(listing)})


@require_GET
def admin_reports_api(request):
    denied = _require_admin(request, "trust.view_report")
    if denied:
        return denied
    reports = Report.objects.select_related("reporter", "listing", "reported_user", "handled_by")
    reports = _search(
        request,
        reports,
        ("details", "reporter__username", "listing__name", "reported_user__username"),
    )
    if reports is None:
        return _admin_error(_("Search text is too long."), 400)
    status = request.GET.get("status", "")
    if status and status not in Report.Status.values:
        return _admin_error(_("Invalid report status filter."), 400)
    if status:
        reports = reports.filter(status=status)
    page = _paginate(request, reports, _report_payload)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)


@require_POST
def admin_report_update_api(request, report_id):
    denied = _require_admin(request, "trust.manage_report")
    if denied:
        return denied
    try:
        report = Report.objects.select_related("reporter", "listing", "reported_user", "handled_by").get(pk=report_id)
    except Report.DoesNotExist:
        return _admin_error(_("Report not found."), 404)
    data = _json_body(request)
    if data is None:
        return _admin_error(_("Invalid request data."), 400)
    status = data.get("status")
    if status not in Report.Status.values:
        return _admin_error(_("Invalid report status."), 400)
    notes = str(data.get("decision_notes", "")).strip()
    if len(notes) > 4000 or (status in (Report.Status.RESOLVED, Report.Status.REJECTED) and not notes):
        return _admin_error(_("A decision note is required for resolved or rejected reports."), 400)
    if report.status == status and report.decision_notes == notes:
        return _admin_error(_("The report already has this status and decision."), 400)
    with transaction.atomic():
        report.status = status
        report.decision_notes = notes
        report.handled_by = request.user
        report.handled_at = timezone.now()
        report.is_resolved = status in (Report.Status.RESOLVED, Report.Status.REJECTED)
        report.resolution_notes = notes if report.is_resolved else ""
        report.save(
            update_fields=[
                "status",
                "decision_notes",
                "handled_by",
                "handled_at",
                "is_resolved",
                "resolution_notes",
            ]
        )
        _audit(
            request,
            AdminAuditLog.Action.REPORT_UPDATED,
            report,
            "report",
            f"Report #{report.pk}",
            notes,
            {"status": status},
        )
    return _admin_json({"report": _report_payload(report)})


@require_GET
def admin_reviews_api(request):
    denied = _require_admin(request, "trust.view_review")
    if denied:
        return denied
    reviews = Review.objects.select_related("reviewer", "seller").order_by("-created_at")
    reviews = _search(
        request,
        reviews,
        ("comment", "reviewer__username", "seller__username"),
    )
    if reviews is None:
        return _admin_error(_("Search text is too long."), 400)

    def serialize(review):
        return {
            "id": review.pk,
            "reviewer": review.reviewer.get_username(),
            "seller": review.seller.get_username(),
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at.isoformat(),
        }

    page = _paginate(request, reviews, serialize)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)


@require_POST
def admin_review_remove_api(request, review_id):
    denied = _require_admin(request, "trust.delete_review")
    if denied:
        return denied
    try:
        review = Review.objects.select_related("reviewer", "seller").get(pk=review_id)
    except Review.DoesNotExist:
        return _admin_error(_("Review not found."), 404)
    data = _json_body(request)
    reason = str(data.get("reason", "")).strip() if data is not None else ""
    if not reason or len(reason) > 1000:
        return _admin_error(_("A moderation reason of up to 1000 characters is required."), 400)
    label = f"{review.rating} stars: {review.reviewer.get_username()} to {review.seller.get_username()}"
    with transaction.atomic():
        _audit(
            request,
            AdminAuditLog.Action.REVIEW_REMOVED,
            review,
            "review",
            label,
            reason,
        )
        review.delete()
    return _admin_json({"detail": _("Review removed.")})


@require_GET
def admin_phones_api(request):
    denied = _require_admin(request, "trust.view_phoneverification")
    if denied:
        return denied
    verifications = User.objects.select_related("phone_verification").order_by("-date_joined")
    verified = request.GET.get("verified", "")
    if verified not in ("", "verified", "unverified"):
        return _admin_error(_("Invalid verification filter."), 400)
    if verified == "verified":
        verifications = verifications.filter(phone_verification__is_verified=True)
    elif verified == "unverified":
        verifications = verifications.filter(
            Q(phone_verification__isnull=True)
            | Q(phone_verification__is_verified=False)
        )
    verifications = _search(request, verifications, ("username", "phone_number"))
    if verifications is None:
        return _admin_error(_("Search text is too long."), 400)

    def serialize(user):
        verification = getattr(user, "phone_verification", None)
        return {
            "user": user.get_username(),
            "phone_number": user.phone_number,
            "is_verified": bool(verification and verification.is_verified),
            "attempts": verification.attempts if verification else 0,
            "created_at": (
                verification.created_at.isoformat()
                if verification
                else user.date_joined.isoformat()
            ),
            "expires_at": (
                verification.expires_at.isoformat()
                if verification
                else None
            ),
        }

    page = _paginate(request, verifications, serialize)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)


@require_GET
def admin_activity_api(request):
    denied = _require_admin(request, "trust.view_adminauditlog")
    if denied:
        return denied
    entries = AdminAuditLog.objects.select_related("actor").all()
    action = request.GET.get("action", "")
    if action and action not in AdminAuditLog.Action.values:
        return _admin_error(_("Invalid activity filter."), 400)
    if action:
        entries = entries.filter(action=action)
    page = _paginate(request, entries, _audit_payload)
    return _admin_error(_("Invalid pagination values."), 400) if page is None else _admin_json(page)
