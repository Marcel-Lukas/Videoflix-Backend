"""Tests for ``VideoListView`` (``GET /api/video/``)."""

from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from video_app.models import Video

from .helpers import MediaRootMixin, authenticate, make_user, make_video


class VideoListViewTests(MediaRootMixin, APITestCase):
    """Authentication and payload of the public video listing."""

    _media_prefix = 'videoflix-list-'

    def setUp(self):
        self.url = reverse('video-list')

    def test_requires_authentication(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_returns_videos_for_authenticated_user(self):
        user = make_user()
        authenticate(self.client, user)
        first = make_video(title='Older', conversion_status=Video.ConversionStatus.READY)
        second = make_video(title='Newer', conversion_status=Video.ConversionStatus.READY)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        # Default ordering is "-created_at" → newest first.
        self.assertEqual(response.data[0]['id'], second.id)
        self.assertEqual(response.data[1]['id'], first.id)

    def test_returns_empty_list_when_no_videos(self):
        user = make_user()
        authenticate(self.client, user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_invalid_token_is_rejected(self):
        self.client.cookies['access_token'] = 'not-a-valid-jwt'

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
