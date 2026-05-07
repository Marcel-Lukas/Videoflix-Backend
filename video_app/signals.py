import os
import shutil

import django_rq
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Video
from .tasks import HLS_DIRNAME, convert_and_save


@receiver(post_save, sender=Video)
def enqueue_conversion_on_create(sender, instance, created, **kwargs):
    """Mark a freshly created video as processing and enqueue conversion."""
    if not created:
        return

    Video.objects.filter(pk=instance.pk).update(
        conversion_status=Video.ConversionStatus.PROCESSING
    )
    transaction.on_commit(
        lambda: django_rq.enqueue(convert_and_save, instance.pk)
    )


@receiver(post_delete, sender=Video)
def remove_video_files_on_delete(sender, instance, **kwargs):
    """Remove the source file, thumbnail and HLS renditions on deletion."""
    if instance.video_file:
        _safe_remove_file(instance.video_file.path)

    if instance.thumbnail_url:
        _safe_remove_file(instance.thumbnail_url.path)

    hls_dir = os.path.join(settings.MEDIA_ROOT, HLS_DIRNAME, str(instance.pk))
    if os.path.isdir(hls_dir):
        shutil.rmtree(hls_dir, ignore_errors=True)


def _safe_remove_file(path):
    if path and os.path.isfile(path):
        os.remove(path)
