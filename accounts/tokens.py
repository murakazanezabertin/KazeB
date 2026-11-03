"""
A token generator for "click this link to verify your email" links,
built the same way Django builds its own password-reset tokens (see
django.contrib.auth.tokens.PasswordResetTokenGenerator) -- reusing
that proven, well-tested approach rather than inventing a new one or
storing tokens in the database ourselves.

Subclassing it (instead of reusing the password-reset generator
directly) matters for one reason: the hash this generator produces is
salted with a value that changes once the token is used -- for
password reset that's the user's password hash; here it's
`email_verified`. That means:

- A verification link naturally stops working the moment it's been
  used once (email_verified flips True -> the old token's hash no
  longer matches).
- A verification link and a password-reset link can never be
  interchanged, even though the URL shapes look similar -- each
  generator salts with a different field, so a token made for one
  purpose fails validation against the other.
"""
from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verified}{timestamp}"


email_verification_token = EmailVerificationTokenGenerator()
