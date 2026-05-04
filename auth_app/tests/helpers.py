"""Shared helpers and constants for the auth_app test suite."""

from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


User = get_user_model()

TEST_EMAIL = 'user@example.com'
TEST_PASSWORD = 'StrongPass!234'

TEST_SETTINGS = {
    'FRONTEND_URL': 'http://testserver',
    'DEFAULT_FROM_EMAIL': 'noreply@example.com',
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
}


def make_user(email=TEST_EMAIL, password=TEST_PASSWORD, is_active=True):
    """Create a user with sensible defaults for the test suite."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=is_active,
    )


def encode_uid(user):
    """Return the base64-encoded primary key for ``user``."""
    return urlsafe_base64_encode(force_bytes(user.pk))
