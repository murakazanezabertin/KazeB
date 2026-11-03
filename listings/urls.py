from django.urls import path

from . import views

app_name = "listings"

urlpatterns = [
    path("search/", views.search, name="search"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("favorites/", views.favorites, name="favorites"),
    path("add/", views.listing_create, name="listing_create"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("<int:pk>/edit/", views.listing_edit, name="listing_edit"),
    path("<int:pk>/delete/", views.listing_delete, name="listing_delete"),
    path("<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("<int:pk>/", views.listing_detail, name="listing_detail"),
]
