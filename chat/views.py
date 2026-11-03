from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from datetime import timedelta

from listings.models import Listing

from .models import Message

User = get_user_model()


def _get_thread_or_403(request, listing_id, buyer_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    buyer = get_object_or_404(User, pk=buyer_id) if buyer_id else request.user

    if request.user != listing.seller and request.user != buyer:
        raise PermissionDenied("You are not part of this conversation.")
    if buyer == listing.seller:
        raise PermissionDenied("A seller cannot message themselves about their own listing.")

    return listing, buyer


@login_required
def inbox(request):
    """
    Every conversation the current user is part of, whether they're
    the buyer who started it or the seller being messaged.
    """
    threads = (
        Message.objects.filter(Q(buyer=request.user) | Q(listing__seller=request.user))
        .values("listing", "buyer")
        .distinct()
    )

    conversations = []
    for row in threads:
        listing = Listing.objects.select_related("seller").get(pk=row["listing"])
        buyer = User.objects.get(pk=row["buyer"])
        last_message = (
            Message.objects.filter(listing=listing, buyer=buyer).order_by("-created_at").first()
        )
        other_party = buyer if request.user == listing.seller else listing.seller
        conversations.append(
            {
                "listing": listing,
                "buyer": buyer,
                "other_party": other_party,
                "last_message": last_message,
            }
        )

    conversations.sort(key=lambda c: c["last_message"].created_at, reverse=True)
    return render(request, "chat/inbox.html", {"conversations": conversations})


@login_required
def thread(request, listing_id, buyer_id=None):
    """
    A single conversation about one listing. Reached with no buyer_id
    when a buyer opens/starts the thread from the listing page, and
    with buyer_id when the seller opens it from their inbox.
    """
    listing, buyer = _get_thread_or_403(request, listing_id, buyer_id)

    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if body:
            # Guard against duplicate sends -- a slow connection plus a
            # second tap on "Send" (or a refresh of the POST response)
            # used to create two or more identical rows. If the same
            # sender just posted the exact same text in this thread a
            # few seconds ago, treat this as a resubmission and skip
            # creating another row rather than silently duplicating it.
            recent_duplicate = Message.objects.filter(
                listing=listing,
                buyer=buyer,
                sender=request.user,
                body=body,
                created_at__gte=timezone.now() - timedelta(seconds=15),
            ).exists()
            if not recent_duplicate:
                Message.objects.create(
                    listing=listing, buyer=buyer, sender=request.user, body=body
                )
        if request.user == listing.seller:
            return redirect("chat:thread_as_seller", listing_id=listing.pk, buyer_id=buyer.pk)
        return redirect("chat:thread_as_buyer", listing_id=listing.pk)

    thread_messages = Message.objects.filter(listing=listing, buyer=buyer)
    thread_messages.filter(~Q(sender=request.user), is_read=False).update(is_read=True)

    other_party = buyer if request.user == listing.seller else listing.seller

    return render(
        request,
        "chat/thread.html",
        {
            "listing": listing,
            "buyer": buyer,
            "other_party": other_party,
            "thread_messages": thread_messages,
        },
    )


@login_required
def thread_updates(request, listing_id, buyer_id=None):
    """
    JSON polling endpoint: returns messages newer than ?after=<id>,
    marking them read if they weren't sent by the current user. This
    is a deliberately simple stand-in for real-time chat -- true
    real-time (WebSockets via Django Channels + a Redis channel layer)
    is a much bigger infrastructure lift than a static file delivery
    can responsibly set up; polling every few seconds from
    static/js/chat-poll.js gets most of the practical benefit (new
    messages show up without a manual refresh) with zero extra moving
    parts to deploy.
    """
    listing, buyer = _get_thread_or_403(request, listing_id, buyer_id)

    after_id = request.GET.get("after")
    thread_messages = Message.objects.filter(listing=listing, buyer=buyer).order_by("created_at")
    if after_id:
        thread_messages = thread_messages.filter(pk__gt=after_id)

    thread_messages.filter(~Q(sender=request.user), is_read=False).update(is_read=True)

    return JsonResponse({
        "messages": [
            {
                "id": message.pk,
                "body": escape(message.body),
                "mine": message.sender_id == request.user.pk,
                "created_at": message.created_at.strftime("%d %b, %H:%M"),
            }
            for message in thread_messages
        ]
    })
