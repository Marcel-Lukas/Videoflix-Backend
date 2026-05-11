import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings


logger = logging.getLogger(__name__)

HLS_RESOLUTIONS = (480, 720, 1080)
HLS_DIRNAME = 'hls'
THUMBNAIL_DIRNAME = 'thumbnails'
MANIFEST_NAME = 'index.m3u8'
# One worker per rendition plus the thumbnail job.
_MAX_CONVERSION_WORKERS = len(HLS_RESOLUTIONS) + 1


def _run_ffmpeg(args):
    """Run ffmpeg with the given argument list (no shell)."""
    subprocess.run(['ffmpeg', *args], check=True)


def _get_video_duration(video_path):
    """Return the duration of the video in seconds as a float."""
    result = subprocess.run(
        [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def create_thumbnail(video_path, thumbnail_path):
    """Extract a single-frame thumbnail at one quarter of the video duration."""
    duration = _get_video_duration(video_path)
    seek = duration / 4
    _run_ffmpeg([
        '-y',
        '-ss', str(seek),
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
    rel_path = os.path.join(THUMBNAIL_DIRNAME, f'thumbnail-{video.id}.jpg')
    full_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    create_thumbnail(video.video_file.path, full_path)
    video.thumbnail_url = rel_path
    video.save(update_fields=['thumbnail_url'])


def _generate_hls_rendition(video, resolution):
    """Produce a single HLS rendition for `resolution`."""
    output_dir = os.path.join(
        settings.MEDIA_ROOT, HLS_DIRNAME, str(video.id), f'{resolution}p'
    )
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, MANIFEST_NAME)
    convert_to_hls(video.video_file.path, output_path, resolution)


def _run_conversion_jobs(video):
    """Run thumbnail and all HLS renditions concurrently.

    Each ffmpeg invocation is its own OS process, so threads suffice to
    parallelise the work and use multiple CPU cores at once.
    Raises the first exception encountered after all jobs have been awaited.
    """
    jobs = [('thumbnail', _generate_thumbnail, (video,))]
    jobs.extend(
        (f'hls-{r}p', _generate_hls_rendition, (video, r))
        for r in HLS_RESOLUTIONS
    )

    with ThreadPoolExecutor(max_workers=_MAX_CONVERSION_WORKERS) as pool:
        future_to_name = {
            pool.submit(fn, *args): name for name, fn, args in jobs
        }
        first_error = None
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - re-raised below
                logger.exception(
                    'Conversion job %s failed for video %s', name, video.id
                )
                if first_error is None:
                    first_error = exc

    if first_error is not None:
        raise first_error


def convert_and_save(video_id):
    """Create thumbnail and HLS renditions for the given video."""
    from video_app.models import Video

    try:
        video = Video.objects.get(pk=video_id)
    except Video.DoesNotExist:
        logger.error('Video %s not found for conversion', video_id)
        return

    try:
        _run_conversion_jobs(video)
    except (subprocess.CalledProcessError, OSError):
        logger.exception('Conversion failed for video %s', video_id)
        video.conversion_status = Video.ConversionStatus.FAILED
        video.save(update_fields=['conversion_status'])
        return

    video.conversion_status = Video.ConversionStatus.READY
    video.save(update_fields=['conversion_status'])
