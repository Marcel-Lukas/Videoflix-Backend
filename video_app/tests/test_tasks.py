"""Tests for ``video_app.tasks`` (ffmpeg-driven conversion pipeline)."""

import os
import subprocess
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase

from video_app import tasks
from video_app.models import Video

from .helpers import MediaRootMixin, make_video


def _fake_ffmpeg(args):
    """Stand-in for ``_run_ffmpeg`` that creates the expected output file."""
    # Output path is always the last positional argument in our calls.
    output = args[-1]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, 'wb') as fh:
        fh.write(b'fake-ffmpeg-output')


class ConvertAndSaveTests(MediaRootMixin, TransactionTestCase):
    """End-to-end behaviour of the ``convert_and_save`` RQ task."""

    _media_prefix = 'videoflix-tasks-'

    def test_success_marks_video_ready_and_creates_files(self):
        video = make_video()

        with patch('video_app.tasks._run_ffmpeg', side_effect=_fake_ffmpeg), \
                patch('video_app.tasks._get_video_duration', return_value=10.0):
            tasks.convert_and_save(video.pk)

        video.refresh_from_db()
        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.READY
        )
        # Thumbnail recorded and on disk.
        self.assertTrue(bool(video.thumbnail_url))
        self.assertTrue(os.path.isfile(video.thumbnail_url.path))

        # All HLS renditions present.
        for resolution in tasks.HLS_RESOLUTIONS:
            manifest = os.path.join(
                self._media_root,
                tasks.HLS_DIRNAME,
                str(video.pk),
                f'{resolution}p',
                tasks.MANIFEST_NAME,
            )
            self.assertTrue(
                os.path.isfile(manifest),
                f'Missing manifest for {resolution}p',
            )

    def test_ffmpeg_failure_marks_video_failed(self):
        video = make_video()

        error = subprocess.CalledProcessError(returncode=1, cmd=['ffmpeg'])
        with patch('video_app.tasks._run_ffmpeg', side_effect=error):
            tasks.convert_and_save(video.pk)

        video.refresh_from_db()
        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.FAILED
        )

    def test_missing_video_is_logged_and_returns(self):
        with patch('video_app.tasks._run_ffmpeg') as run_ffmpeg, \
                self.assertLogs('video_app.tasks', level='ERROR') as log:
            tasks.convert_and_save(99999)

        run_ffmpeg.assert_not_called()
        self.assertTrue(any('99999' in line for line in log.output))

    def test_partial_failure_marks_video_failed(self):
        """If a later ffmpeg call fails, status flips to FAILED."""
        video = make_video()
        calls = {'count': 0}

        def flaky(args):
            calls['count'] += 1
            # Let thumbnail + first rendition succeed, then fail.
            if calls['count'] >= 3:
                raise subprocess.CalledProcessError(1, ['ffmpeg'])
            _fake_ffmpeg(args)

        with patch('video_app.tasks._run_ffmpeg', side_effect=flaky), \
                self.assertLogs('video_app.tasks', level='ERROR'):
            tasks.convert_and_save(video.pk)

        video.refresh_from_db()
        self.assertEqual(
            video.conversion_status, Video.ConversionStatus.FAILED
        )

    def test_run_ffmpeg_invokes_subprocess_without_shell(self):
        with patch('video_app.tasks.subprocess.run') as run:
            tasks._run_ffmpeg(['-version'])

        run.assert_called_once_with(['ffmpeg', '-version'], check=True)
