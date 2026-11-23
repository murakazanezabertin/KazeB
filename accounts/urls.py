from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("edit/", views.edit_account, name="edit_account"),
    path("delete/", views.delete_account, name="delete_account"),
    path("verify/code/", views.verify_code, name="verify_code"),
    path("verify/sent/", TemplateView.as_view(template_name="registration/verification_sent.html"), name="verification_sent"),
    path("verify/resend/", views.resend_verification_email, name="resend_verification"),
]
