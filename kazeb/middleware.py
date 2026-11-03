from django.conf import settings

try:
    from django.utils.translation import LANGUAGE_SESSION_KEY
except ImportError:
    # Django has used this exact session key ("_language") for the
    # active language since very old versions, and django.views.i18n
    # itself imports it the same way internally -- but the import can
    # still fail on some environments (mismatched/partial Django
    # installs, an interpreter that isn't the one requirements.txt was
    # installed into, etc). Falling back to the literal value keeps
    # this middleware working either way instead of crashing the whole
    # site on startup.
    LANGUAGE_SESSION_KEY = "_language"


class ForceDefaultLanguageMiddleware:
    """
    Kinyarwanda must be the language every first-time visitor sees,
    no matter what their browser's Accept-Language header prefers.

    Django's LocaleMiddleware picks the active language in this order:
    session -> language cookie -> Accept-Language header -> LANGUAGE_CODE.
    That means a browser configured for English shows the site in
    English on the very first visit, before the visitor has ever
    touched the language dropdown -- LANGUAGE_CODE only wins when
    NONE of the languages in the Accept-Language header match, which
    is rare.

    This middleware runs before LocaleMiddleware. If the visitor
    hasn't explicitly chosen a language yet (no session or cookie
    entry -- i.e. they've never used the dropdown), it strips the
    Accept-Language header for this request so LocaleMiddleware falls
    through to LANGUAGE_CODE (Kinyarwanda). Once someone actually
    picks a language, that choice is saved to their session/cookie by
    the /i18n/setlang/ view and respected on every later visit
    regardless of their browser's language.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        has_session_choice = (
            hasattr(request, "session") and LANGUAGE_SESSION_KEY in request.session
        )
        has_cookie_choice = settings.LANGUAGE_COOKIE_NAME in request.COOKIES
        if not has_session_choice and not has_cookie_choice:
            request.META.pop("HTTP_ACCEPT_LANGUAGE", None)
        return self.get_response(request)
