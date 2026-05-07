import logging
import os
import subprocess

from django.conf import settings


logger = logging.getLogger(__name__)

HLS_RESOLUTIONS = (480, 720, 1080)
HLS_DIRNAME = 'hls'
THUMBNAIL_DIRNAME = 'thumbnails'
MANIFEST_NAME = 'index.m3u8'


def _run_ffmpeg(args):
    """Run ffmpeg with the given argument list (no shell)."""
    subprocess.run(['ffmpeg', *args], check=True)


def create_thumbnail(video_path, thumbnail_path):
    """Extract a single-frame thumbnail at ~20 seconds (fast seek)."""
    _run_ffmpeg([
        '-y',
        '-ss', '00:00:20',
        '-i', video_path,
        '-vframes', '1',
        thumbnail_path,
    ])


def convert_to_hls(video_path, output_path, resolution):
    """Transcode `video_path` to an HLS playlist at the given resolution."""
    _run_ffmpeg([
        '-y',
        '-i', video_path,
        '-vf', f'scale=-2:{resolution}',
        '-start_number', '0',
        '-hls_time', '10',
        '-hls_list_size', '0',
        '-f', 'hls',
        output_path,
    ])


def _generate_thumbnail(video):
    """Create the thumbnail file for `video` and persist its relative path."""
    rel_path = os.path.join(THUMBNAIL_DIRNAME, f'thumb_{video.id}.jpg')
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    create_thumbnail(video.video_file.path, full_path)
    video.thumbnail_url = rel_path
    video.save(update_fields=['thumbnail_url'])


def _generate_hls_renditions(video):
    """Produce HLS renditions for all configured resolutions."""
    for resolution in HLS_RESOLUTIONS:
        output_dir = os.path.join(
            settings.MEDIA_ROOT, HLS_DIRNAME, str(video.id), f'{resolution}p'
        )
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, MANIFEST_NAME)
        convert_to_hls(video.video_file.path, output_path, resolution)


def convert_and_save(video_id):
    """Create thumbnail and HLS renditions for the given video."""
    from video_app.models import Video

    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        logger.error('Video %s not found for conversion', video_id)
        return

    try:
        _generate_thumbnail(video)
        _generate_hls_renditions(video)
    except (subprocess.CalledProcessError, OSError):
        logger.exception('Conversion failed for video %s', video_id)
        video.conversion_status = Video.ConversionStatus.FAILED
        video.save(update_fields=['conversion_status'])
        return

    video.conversion_status = Video.ConversionStatus.READY
    video.save(update_fields=['conversion_status'])
