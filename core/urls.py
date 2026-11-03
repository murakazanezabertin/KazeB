from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),
    path("terms/", views.terms, name="terms"),
    path("privacy/", views.privacy, name="privacy"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("faq/", views.faq, name="faq"),
    path("anti-scam/", views.anti_scam, name="anti_scam"),
]
