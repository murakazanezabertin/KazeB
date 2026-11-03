from django.conf import settings
from django.db import models

from listings.models import Listing


class Message(models.Model):
    """
    One message in a conversation about a listing. A conversation is
    identified by (listing, buyer) -- the seller is always the other
    side, so all messages a buyer and seller exchange about one
    listing land in the same thread. This is the "first icon: text the
    seller through the website" option from the spec.
    """

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="messages")
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_threads"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} on {self.listing}: {self.body[:30]}"
