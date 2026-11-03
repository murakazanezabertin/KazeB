"""
Django settings for the KazeB project.

KazeB connects buyers and sellers directly: sellers list products,
buyers browse/search by category, location and price, then contact
the seller through in-site chat, WhatsApp, or phone. KazeB does not
handle payment or delivery -- that is arranged directly between the
two parties.

PRODUCTION CHECKLIST -- see README.md "Launch checklist" section for
the full explanation of each of these:
  - Set DJANGO_SECRET_KEY, DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS
  - Set DATABASE_URL to a real Postgres instance
  - Set EMAIL_* variables to a real SMTP provider
  - Set SENTRY_DSN if you want error tracking
  - Use a real cache backend (Redis) instead of the in-memory default
    if you run more than one server process, or rate limiting and the
    "first visit forces Kinyarwanda" logic won't be shared correctly
    across workers.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# SECURITY WARNING: keep the secret key secret in production. This
# fallback is only for local development -- set DJANGO_SECRET_KEY in
# the environment for anything real. Generate one with:
#   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-CHANGE-ME-BEFORE-DEPLOYING"
)

# SECURITY WARNING: don't run with DEBUG turned on in production! This
# defaults to True only so the project runs out of the box for local
# development -- set DJANGO_DEBUG=False (or don't set DJANGO_DEBUG at
# all) in any environment real users can reach.
DEBUG = env_bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]

# Automatically allow the current Vercel deployment hostname
vercel_url = os.environ.get("VERCEL_URL")

if vercel_url:
    ALLOWED_HOSTS.append(vercel_url)

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    # KazeB apps
    "core",
    "accounts",
    "listings",
    "chat",
    "trust",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves static files directly, no separate nginx/CDN needed
    "django.contrib.sessions.middleware.SessionMiddleware",
    "kazeb.middleware.ForceDefaultLanguageMiddleware",  # keeps Kinyarwanda as the true first-visit default
    "django.middleware.locale.LocaleMiddleware",  # enables the language switcher
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kazeb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                # Makes the category list available on every page (for the
                # nav / "find by category" section) without repeating the
                # query in every view.
                "listings.context_processors.categories",
                # Makes the current user's unread-message count available
                # on every page, for the 💬 nav icon's unread badge.
                "chat.context_processors.unread_messages",
            ],
        },
    },
]

WSGI_APPLICATION = "kazeb.wsgi.application"

# Database
# Defaults to SQLite so the project runs with zero extra setup in
# development. Set DATABASE_URL in production to point at a real
# Postgres instance, e.g.:
#   DATABASE_URL=postgres://user:password@host:5432/dbname
# SQLite works for development and small/low-traffic use but isn't
# built for many people writing to it at once -- it will start
# throwing "database is locked" errors under real concurrent traffic.

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:home"
LOGOUT_REDIRECT_URL = "core:home"

# Internationalization
# Rwanda's three official languages, matching the "change language" icon
# in the spec and the District / Sector location fields used on listings.
#
# Kinyarwanda ("rw") isn't one of the ~100 languages Django ships
# built-in support for, so two things are needed beyond the usual
# LANGUAGE_CODE/LANGUAGES settings, or Django refuses to start with
# "OSError: No translation files found for default language rw.":
#
#   1. A real catalog at locale/rw/LC_MESSAGES/django.mo (included in
#      this project -- since the site's source text is already written
#      in Kinyarwanda, it's an identity catalog: msgstr == msgid).
#   2. Registering "rw" in Django's LANG_INFO (below), which is the
#      officially documented way to add a language Django doesn't know
#      about: https://docs.djangoproject.com/en/stable/topics/i18n/translation/#how-to-create-language-files

import django.conf.locale

try:
    from django.conf.locale import LANG_INFO
except ImportError:
    # Extremely stable across Django versions, but fall back to an
    # empty base rather than crash startup if it's ever unavailable --
    # this only means non-Kinyarwanda languages lose Django's built-in
    # display metadata, not that the site stops working.
    LANG_INFO = {}

EXTRA_LANG_INFO = {
    "rw": {
        "bidi": False,
        "code": "rw",
        "name": "Kinyarwanda",
        "name_local": "Kinyarwanda",
    },
}
django.conf.locale.LANG_INFO = {**LANG_INFO, **EXTRA_LANG_INFO}

LANGUAGE_CODE = "rw"

LANGUAGES = [
    ("rw", "Kinyarwanda"),
    ("en", "English"),
    ("fr", "Français"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Africa/Kigali"

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, icons)

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: lets Django serve its own static files (CSS/JS) directly
# in production, compressed and cache-busted, without needing a
# separate nginx/CDN setup. Most small-to-medium hosts (Railway,
# Render, a plain VPS) work fine with this.
#
# The manifest-based storage (CompressedManifestStaticFilesStorage)
# hashes filenames for cache-busting, but that hashing only exists
# after `collectstatic` has run and written staticfiles.json. In
# local development nobody runs collectstatic before `runserver` --
# so with the manifest backend active, EVERY {% static %} tag in
# EVERY template raises "Missing staticfiles manifest entry", which
# replaces the whole site with a Django error page. Production (the
# Docker build) always runs collectstatic before the container ever
# serves traffic, so it's safe to use the manifest version there;
# development uses the plain version, which just resolves paths
# directly with no manifest required.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

# Media files (listing photos, category icons)
#
# Locally this defaults to storing uploads on disk (MEDIA_ROOT), which
# is fine for development but NOT for Fly.io or any host with an
# ephemeral filesystem -- uploaded files would silently disappear on
# every restart/redeploy. Set the SUPABASE_STORAGE_* variables below
# to store uploads in Supabase Storage instead (S3-compatible), which
# survives restarts and works the same way in every environment.
#
#   SUPABASE_STORAGE_ENDPOINT_URL=https://<project-ref>.supabase.co/storage/v1/s3
#   SUPABASE_STORAGE_BUCKET=media
#   SUPABASE_STORAGE_REGION=<your project region, e.g. eu-west-2>
#   SUPABASE_STORAGE_ACCESS_KEY_ID=...   (Storage settings -> S3 Access Keys)
#   SUPABASE_STORAGE_SECRET_ACCESS_KEY=...
#
# See README.md "Media storage (Supabase Storage)" for the full setup
# walkthrough, including creating the bucket and making it public.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET")

if SUPABASE_STORAGE_BUCKET:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": SUPABASE_STORAGE_BUCKET,
            "endpoint_url": os.environ["SUPABASE_STORAGE_ENDPOINT_URL"],
            "access_key": os.environ["SUPABASE_STORAGE_ACCESS_KEY_ID"],
            "secret_key": os.environ["SUPABASE_STORAGE_SECRET_ACCESS_KEY"],
            "region_name": os.environ.get("SUPABASE_STORAGE_REGION", "us-east-1"),
            # Supabase's S3-compatible endpoint requires path-style
            # addressing (bucket in the URL path, not as a subdomain).
            "addressing_style": "path",
            # The bucket itself is set to public in Supabase (see
            # README), so files don't need individually-signed,
            # expiring URLs -- plain permanent public URLs instead.
            "querystring_auth": False,
            "default_acl": None,
            "file_overwrite": False,
        },
    }
    MEDIA_URL = (
        os.environ["SUPABASE_STORAGE_ENDPOINT_URL"].removesuffix("/storage/v1/s3")
        + f"/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/"
    )

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Used to build wa.me deep links; keep as-is unless WhatsApp changes its
# scheme.
WHATSAPP_LINK_BASE = "https://wa.me/"

SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "localhost:8000")
SITE_NAME = "KazeB"

# Email
# Defaults to printing emails to the console so password reset etc.
# are visible during development without any setup. Set these
# environment variables to a real SMTP provider (SendGrid, Mailgun,
# Amazon SES, or even a plain Gmail account with an app password) to
# send real emails in production:
#   EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD,
#   EMAIL_USE_TLS=True, DEFAULT_FROM_EMAIL

if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", default=True)
    DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", f"no-reply@{SITE_DOMAIN}")
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = f"no-reply@{SITE_DOMAIN}"

# SMS (phone verification / OTP)
# There's no free, keyless way to send a real SMS -- it always needs a
# paid gateway account. Set SMS_BACKEND to a dotted path implementing
# trust.sms.SMSBackend (see trust/sms.py) once you have one (Africa's
# Talking and Twilio both have simple HTTP APIs that fit this
# interface). Until then, OTP codes are sent through the email backend
# above (console-printed in development) so the verification flow is
# fully testable without a paid account.
SMS_BACKEND = os.environ.get("SMS_BACKEND", "trust.sms.ConsoleSMSBackend")
SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
SMS_SENDER_ID = os.environ.get("SMS_SENDER_ID", "KazeB")

# Cache (used for basic login/registration/message rate limiting).
# The default here (per-process memory) works for a single-process
# dev server but is NOT shared between multiple worker processes --
# use Redis (django-redis) in any real multi-process deployment or
# each worker will enforce its own separate rate limit.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Error tracking (optional). Set SENTRY_DSN to enable -- sign up for a
# free Sentry account and it'll give you this URL. Left unset, this
# block does nothing.
SENTRY_DSN = os.environ.get("SENTRY_DSN")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,
    )

# Security hardening -- only enforced when DEBUG is off, since these
# (HTTPS redirects, secure-only cookies) actively get in the way of
# local development over plain http://localhost.
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "3600"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    # Fly.io (and most PaaS hosts) terminate HTTPS at their edge proxy
    # and forward plain HTTP to the container, adding this header to
    # say the original request was HTTPS. Without this, Django can't
    # tell and SECURE_SSL_REDIRECT above causes an infinite redirect
    # loop.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Django 4+ requires the exact scheme+host of anywhere that will POST
# forms to this site (logging in, adding a listing, etc.) to be listed
# here, or those POSTs get rejected as a CSRF failure. Comma-separated,
# e.g. "https://kazeb.fly.dev,https://kazeb.rw".
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
