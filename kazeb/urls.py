from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from accounts.forms import LoginForm
from accounts import api as account_api
from listings import api as listing_api
from listings import views as listing_views
from .sitemaps import CategorySitemap, ListingSitemap, StaticViewSitemap

sitemaps = {
    "listings": ListingSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}

# Deliberately NOT using i18n_patterns here. i18n_patterns gives every
# non-default language a URL prefix (e.g. /en/..., /fr/...) while the
# default language (Kinyarwanda) has none -- and that prefix silently
# overrides the session language on every request. That combination is
# exactly what broke switching back to Kinyarwanda: once on an /en/...
# page, changing the dropdown back to "rw" updates the session, but
# the redirect target still starts with /en/, so the URL prefix wins
# and the page stays in English. Using plain, unprefixed paths for
# every language means LocaleMiddleware reads the active language
# purely from the session (set by the /i18n/setlang/ view below),
# which switches correctly in both directions.
urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    # Registered ahead of django.contrib.auth.urls below so this one
    # (with our Kinyarwanda-labeled form) wins over the default.
    path("accounts/login/", LoginView.as_view(authentication_form=LoginForm), name="login"),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),  # logout, password reset, etc.
    path("seller/<str:username>/", listing_views.seller_profile, name="seller_profile"),
    path(
        "api/sellers/<str:username>/",
        listing_views.seller_profile_api,
        name="seller_profile_api",
    ),
    path("api/auth/ui/", account_api.auth_ui, name="auth_ui_api"),
    path("api/auth/register/", account_api.register_api, name="auth_register_api"),
    path("api/auth/login/", account_api.login_api, name="auth_login_api"),
    path("api/auth/logout/", account_api.logout_api, name="auth_logout_api"),
    path(
        "api/auth/verify/resend/",
        account_api.resend_verification_api,
        name="auth_resend_verification_api",
    ),
    path(
        "api/auth/password-reset/",
        account_api.password_reset_request_api,
        name="auth_password_reset_api",
    ),
    path(
        "api/auth/password-reset/<str:uidb64>/<str:token>/",
        account_api.password_reset_confirm_api,
        name="auth_password_reset_confirm_api",
    ),
    path("api/account/", account_api.account_api, name="account_api"),
    path("api/account/edit/", account_api.edit_account_api, name="account_edit_api"),
    path("api/account/delete/", account_api.delete_account_api, name="account_delete_api"),
    path("api/favorites/", account_api.favorites_api, name="favorites_api"),
    path(
        "api/favorites/<int:pk>/toggle/",
        account_api.toggle_favorite_api,
        name="favorite_toggle_api",
    ),
    path("api/listings/", listing_api.listing_browse_api, name="listing_browse_api"),
    path(
        "api/listings/<int:pk>/",
        listing_api.listing_detail_api,
        name="listing_detail_api",
    ),
    path("listings/", include("listings.urls")),
    path("messages/", include("chat.urls")),
    path("trust/", include("trust.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots_txt",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
