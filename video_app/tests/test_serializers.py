"""Tests for ``VideoSerializer``."""

from django.test import RequestFactory, TestCase

from video_app.api.serializers import VideoSerializer

from .helpers import MediaRootMixin, make_video


class VideoSerializerTests(MediaRootMixin, TestCase):
    """Field selection and absolute thumbnail URL handling."""

    _media_prefix = 'videoflix-serializer-'

    def test_serializer_exposes_expected_fields(self):
        video = make_video()

        data = VideoSerializer(video).data

        self.assertEqual(
            set(data.keys()),
            {'id', 'created_at', 'title', 'description',
             'thumbnail_url', 'category'},
        )
        self.assertEqual(data['title'], video.title)
        self.assertEqual(data['category'], video.category)

    def test_thumbnail_url_is_none_when_missing(self):
        video = make_video()

        data = VideoSerializer(video).data

        self.assertIsNone(data['thumbnail_url'])

    def test_thumbnail_url_uses_absolute_uri_when_request_present(self):
        video = make_video()
        video.thumbnail_url = 'thumbnails/thumb.jpg'
        video.save(update_fields=['thumbnail_url'])

        request = RequestFactory().get('/')
        data = VideoSerializer(video, context={'request': request}).data

        self.assertTrue(data['thumbnail_url'].startswith('http'))
        self.assertIn('/media/thumbnails/thumb.jpg', data['thumbnail_url'])

    def test_thumbnail_url_falls_back_to_relative_url_without_request(self):
        video = make_video()
        video.thumbnail_url = 'thumbnails/thumb.jpg'
        video.save(update_fields=['thumbnail_url'])

        data = VideoSerializer(video).data

        self.assertEqual(data['thumbnail_url'], video.thumbnail_url.url)
