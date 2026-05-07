"""Tests for ``video_app.signals``."""

import os
from unittest.mock import patch

from django.test import TestCase

from video_app.models import Video
from video_app.tasks import HLS_DIRNAME

from .helpers import MediaRootMixin, make_video, make_video_file


class EnqueueConversionSignalTests(MediaRootMixin, TestCase):
    """``post_save`` should mark the video processing and enqueue the job."""

    _media_prefix = 'videoflix-signal-create-'

    def test_creating_video_enqueues_conversion(self):
        with patch('video_app.signals.django_rq.enqueue') as enqueue, \
                self.captureOnCommitCallbacks(execute=True):
            video = Video.objects.create(
                title='New',
                description='desc',
                category=Video.Category.ACTION,
                video_file=make_video_file(),
            )

        enqueue.assert_called_once()
        args, _ = enqueue.call_args
        # First positional argument is the task callable, second the video id.
        self.assertEqual(args[1], video.pk)

        video.refresh_from_db()
        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.PROCESSING
        )

    def test_updating_video_does_not_enqueue(self):
        video = make_video()

        with patch('video_app.signals.django_rq.enqueue') as enqueue, \
                self.captureOnCommitCallbacks(execute=True):
            video.title = 'changed'
            video.save()

        enqueue.assert_not_called()

    def test_updating_video_does_not_reset_status(self):
        video = make_video()
        video.conversion_status = Video.ConversionStatus.READY
        video.save(update_fields=['conversion_status'])

        with patch('video_app.signals.django_rq.enqueue'), \
                self.captureOnCommitCallbacks(execute=True):
            video.title = 'changed'
            video.save()

        video.refresh_from_db()
        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.READY
        )


class RemoveFilesOnDeleteSignalTests(MediaRootMixin, TestCase):
    """``post_delete`` should clean up source, thumbnail and HLS folder."""

    _media_prefix = 'videoflix-signal-delete-'

    def test_video_file_is_removed(self):
        video = make_video()
        video_path = video.video_file.path
        self.assertTrue(os.path.isfile(video_path))

        video.delete()

        self.assertFalse(os.path.isfile(video_path))

    def test_thumbnail_file_is_removed(self):
        video = make_video()
        thumb_rel = os.path.join('thumbnails', f'thumb_{video.id}.jpg')
        thumb_abs = os.path.join(self._media_root, thumb_rel)
        os.makedirs(os.path.dirname(thumb_abs), exist_ok=True)
        with open(thumb_abs, 'wb') as fh:
            fh.write(b'thumb')
        video.thumbnail_url = thumb_rel
        video.save(update_fields=['thumbnail_url'])

        video.delete()

        self.assertFalse(os.path.isfile(thumb_abs))

    def test_hls_directory_is_removed(self):
        video = make_video()
        hls_dir = os.path.join(
            self._media_root, HLS_DIRNAME, str(video.id), '720p'
        )
        os.makedirs(hls_dir, exist_ok=True)
        with open(os.path.join(hls_dir, 'index.m3u8'), 'wb') as fh:
            fh.write(b'#EXTM3U')

        video.delete()

        self.assertFalse(
            os.path.isdir(
                os.path.join(self._media_root, HLS_DIRNAME, str(video.id))
            )
        )

    def test_delete_without_files_does_not_raise(self):
        video = make_video()
        os.remove(video.video_file.path)

        # Must not raise even though the underlying file is already gone.
        video.delete()
