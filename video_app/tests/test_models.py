"""Tests for the ``Video`` model."""

import os

from django.test import TestCase

from video_app.models import Video

from .helpers import MediaRootMixin, make_video


class VideoModelTests(MediaRootMixin, TestCase):
    """Sanity checks for fields, defaults and ordering."""

    _media_prefix = 'videoflix-model-'

    def test_str_returns_title(self):
        video = make_video(title='My Title')

        self.assertEqual(str(video), 'My Title')

    def test_default_conversion_status_is_processing_after_signal(self):
        video = make_video()
        video.refresh_from_db()

        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.PROCESSING
        )

    def test_thumbnail_url_optional(self):
        video = make_video()

        self.assertFalse(bool(video.thumbnail_url))

    def test_ordering_is_newest_first(self):
        first = make_video(title='First')
        second = make_video(title='Second')

        titles = list(Video.objects.values_list('title', flat=True))

        self.assertEqual(titles, [second.title, first.title])

    def test_video_file_is_stored_under_videos_dir(self):
        video = make_video()

        self.assertTrue(video.video_file.name.startswith('videos/'))
        self.assertTrue(os.path.isfile(video.video_file.path))
