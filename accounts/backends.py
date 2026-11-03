"""
Lets someone log in with either their username or their email address,
typed into the same "username" field Django's built-in login form
already submits -- no new form field or template restructuring
needed, just this backend plus the AUTHENTICATION_BACKENDS setting.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = UserModel._default_manager.get(
                Q(**{UserModel.USERNAME_FIELD: username}) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            # Extremely unlikely (would mean two accounts share an
            # email), but fall back to the first match rather than
            # crash the login attempt.
            user = (
                UserModel._default_manager.filter(
                    Q(**{UserModel.USERNAME_FIELD: username}) | Q(email__iexact=username)
                )
                .order_by("id")
                .first()
            )

        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None