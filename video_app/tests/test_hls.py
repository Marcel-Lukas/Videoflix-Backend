"""Tests for the HLS manifest and segment endpoints."""

import os

from django.http import Http404
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from video_app.api.views import _resolve_hls_path
from video_app.tasks import HLS_DIRNAME, MANIFEST_NAME

from .helpers import MediaRootMixin, authenticate, make_user, make_video


MANIFEST_BODY = b'#EXTM3U\n#EXT-X-VERSION:3\n'
SEGMENT_NAME = 'index0.ts'
SEGMENT_BODY = b'\x47\x40\x00\x10dummy-segment'


class HlsViewsTests(MediaRootMixin, APITestCase):
    """Manifest and segment delivery + path-traversal protection."""

    _media_prefix = 'videoflix-hls-'

    def setUp(self):
        self.user = make_user()
        authenticate(self.client, self.user)
        self.video = make_video()
        self.resolution = '720p'
        self.hls_dir = os.path.join(
            self._media_root,
            HLS_DIRNAME,
            str(self.video.id),
            self.resolution,
        )
        os.makedirs(self.hls_dir, exist_ok=True)
        with open(os.path.join(self.hls_dir, MANIFEST_NAME), 'wb') as fh:
            fh.write(MANIFEST_BODY)
        with open(os.path.join(self.hls_dir, SEGMENT_NAME), 'wb') as fh:
            fh.write(SEGMENT_BODY)

    # -- manifest ---------------------------------------------------------

    def test_manifest_returns_file_for_authenticated_user(self):
        url = reverse(
            'video-stream',
            kwargs={'movie_id': self.video.id, 'resolution': self.resolution},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'], 'application/vnd.apple.mpegurl'
        )
        self.assertEqual(b''.join(response.streaming_content), MANIFEST_BODY)

    def test_manifest_requires_authentication(self):
        self.client.cookies.clear()
        url = reverse(
            'video-stream',
            kwargs={'movie_id': self.video.id, 'resolution': self.resolution},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manifest_unsupported_resolution(self):
        url = reverse(
            'video-stream',
            kwargs={'movie_id': self.video.id, 'resolution': '144p'},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_manifest_unknown_video(self):
        url = reverse(
            'video-stream',
            kwargs={'movie_id': 9999, 'resolution': self.resolution},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- segment ----------------------------------------------------------

    def test_segment_returns_file(self):
        url = reverse(
            'video-segment',
            kwargs={
                'movie_id': self.video.id,
                'resolution': self.resolution,
                'segment': SEGMENT_NAME,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/mp2t')
        self.assertEqual(b''.join(response.streaming_content), SEGMENT_BODY)

    def test_segment_missing_file_returns_404(self):
        url = reverse(
            'video-segment',
            kwargs={
                'movie_id': self.video.id,
                'resolution': self.resolution,
                'segment': 'does-not-exist.ts',
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_requires_authentication(self):
        self.client.cookies.clear()
        url = reverse(
            'video-segment',
            kwargs={
                'movie_id': self.video.id,
                'resolution': self.resolution,
                'segment': SEGMENT_NAME,
            },
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manifest_missing_file_returns_404(self):
        os.remove(os.path.join(self.hls_dir, MANIFEST_NAME))
        url = reverse(
            'video-stream',
            kwargs={'movie_id': self.video.id, 'resolution': self.resolution},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- path traversal ---------------------------------------------------

    def test_resolve_hls_path_rejects_parent_traversal(self):
        with self.assertRaises(Http404):
            _resolve_hls_path('..', '..', 'etc', 'passwd')

    def test_resolve_hls_path_rejects_absolute_escape(self):
        with self.assertRaises(Http404):
            _resolve_hls_path(str(self.video.id), self.resolution, '/etc/passwd')
