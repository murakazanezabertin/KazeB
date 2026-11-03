from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("listing/<int:listing_id>/", views.thread, name="thread_as_buyer"),
    path("listing/<int:listing_id>/buyer/<int:buyer_id>/", views.thread, name="thread_as_seller"),
    path("listing/<int:listing_id>/updates/", views.thread_updates, name="thread_updates_as_buyer"),
    path(
        "listing/<int:listing_id>/buyer/<int:buyer_id>/updates/",
        views.thread_updates,
        name="thread_updates_as_seller",
    ),
]
