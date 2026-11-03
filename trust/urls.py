from django.urls import path

from . import views

app_name = "trust"

urlpatterns = [
    path("listing/<int:pk>/report/", views.report_listing, name="report_listing"),
    path("seller/<int:user_id>/review/", views.add_review, name="add_review"),
    path("seller/<int:user_id>/reviews/", views.seller_reviews, name="seller_reviews"),
    path("phone/send-code/", views.request_phone_verification, name="request_phone_verification"),
    path("phone/verify/", views.verify_phone, name="verify_phone"),
]
