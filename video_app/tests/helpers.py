"""Shared helpers and constants for the video_app test suite."""

import os
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from rest_framework_simplejwt.tokens import RefreshToken

from video_app.models import Video


User = get_user_model()

TEST_EMAIL = 'video-user@example.com'
TEST_PASSWORD = 'StrongPass!234'

ACCESS_COOKIE = 'access_token'

VIDEO_TITLE = 'Sample Video'
VIDEO_DESCRIPTION = 'A short sample for tests.'
VIDEO_CATEGORY = Video.Category.ACTION

DUMMY_VIDEO_BYTES = b'\x00\x00\x00\x18ftypmp42dummy-bytes'
DUMMY_VIDEO_NAME = 'sample.mp4'


def make_user(email=TEST_EMAIL, password=TEST_PASSWORD, is_active=True):
    """Create a user that can authenticate against the API."""
    return User.objects.create_user(
        username=email,
        email=email,
        password=password,
        is_active=is_active,
    )


def access_token_for(user):
    """Return a signed JWT access token string for ``user``."""
    return str(RefreshToken.for_user(user).access_token)


def authenticate(client, user):
    """Attach the access token cookie expected by ``CookieJWTAuthentication``."""
    client.cookies[ACCESS_COOKIE] = access_token_for(user)
    return client


def make_video_file(name=DUMMY_VIDEO_NAME, content=DUMMY_VIDEO_BYTES):
    """Return an in-memory uploaded video file."""
    return SimpleUploadedFile(name, content, content_type='video/mp4')


def make_video(**overrides):
    """Create a ``Video`` without triggering the real conversion task.

    The ``post_save`` signal enqueues the conversion job via
    ``transaction.on_commit``; we patch ``django_rq.enqueue`` so test runs
    do not depend on Redis or ffmpeg, and we run the queued commit
    callbacks manually because ``TestCase`` wraps each test in an atomic
    block that never commits.

    Pass ``conversion_status=Video.ConversionStatus.READY`` (or any other
    status) to override the status that the signal leaves on the video.
    """
    from django.db import connection

    # Pull out conversion_status before passing to create() so the signal
    # does not stomp on it; we apply it as a final update below.
    final_status = overrides.pop('conversion_status', None)

    defaults = {
        'title': VIDEO_TITLE,
        'description': VIDEO_DESCRIPTION,
        'category': VIDEO_CATEGORY,
        'video_file': make_video_file(),
    }
    defaults.update(overrides)
    with patch('video_app.signals.django_rq.enqueue'):
        start = len(connection.run_on_commit)
        video = Video.objects.create(**defaults)
        pending = connection.run_on_commit[start:]
        del connection.run_on_commit[start:]
        for hook in pending:
            hook[1]()

    if final_status is not None:
        Video.objects.filter(pk=video.pk).update(conversion_status=final_status)

    video.refresh_from_db()
    return video


def temp_media_root():
    """Create an isolated temporary directory to use as ``MEDIA_ROOT``."""
    return tempfile.mkdtemp(prefix='videoflix-test-')


def remove_dir(path):
    """Best-effort recursive removal used for ``tearDown``."""
    if path and os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


class MediaRootMixin:
    """Provide an isolated temporary ``MEDIA_ROOT`` for the whole TestCase."""

    _media_prefix = 'videoflix-test-'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp(prefix=cls._media_prefix)
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        remove_dir(cls._media_root)
        super().tearDownClass()
