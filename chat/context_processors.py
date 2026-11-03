from django.db.models import Q

from .models import Message


def unread_messages(request):
    """Makes the current user's unread-message count available on
    every page, not just the dashboard, so the 💬 nav icon can show a
    badge -- whether the unread message is one they received as a
    buyer or as a seller."""
    if not request.user.is_authenticated:
        return {}

    count = (
        Message.objects.filter(Q(buyer=request.user) | Q(listing__seller=request.user))
        .exclude(sender=request.user)
        .filter(is_read=False)
        .count()
    )
    return {"unread_message_count": count}
