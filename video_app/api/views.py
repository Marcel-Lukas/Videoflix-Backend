from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from auth_app.api.authentication import CookieJWTAuthentication
from video_app.models import Video
from video_app.tasks import HLS_DIRNAME, MANIFEST_NAME

from .serializers import VideoSerializer


ALLOWED_RESOLUTIONS = frozenset({'480p', '720p', '1080p'})

MIME_HLS_MANIFEST = 'application/vnd.apple.mpegurl'
MIME_HLS_SEGMENT = 'video/mp2t'


def _resolve_hls_path(*parts):
    """Resolve a path inside ``MEDIA_ROOT/hls`` and guard against traversal."""
    base_dir = (Path(settings.MEDIA_ROOT) / HLS_DIRNAME).resolve()
    candidate = base_dir.joinpath(*parts).resolve()
    if base_dir != candidate and base_dir not in candidate.parents:
        raise Http404('Invalid HLS path')
    if not candidate.is_file():
        raise Http404('HLS file not found')
    return candidate


class VideoListView(ListAPIView):
    """Return the list of available videos for authenticated users."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]
    serializer_class = VideoSerializer
    queryset = Video.objects.all()


class HlsBaseView(APIView):
    """Shared authentication and validation for HLS endpoints."""

    permission_classes = [IsAuthenticated]
    authentication_classes = [CookieJWTAuthentication]

    @staticmethod
    def validate(movie_id, resolution):
        if resolution not in ALLOWED_RESOLUTIONS:
            raise Http404('Unsupported resolution')
        get_object_or_404(Video, pk=movie_id)


class HlsManifestView(HlsBaseView):
    """Serve the HLS manifest (``index.m3u8``) for a video and resolution."""

    def get(self, request, movie_id, resolution):
        self.validate(movie_id, resolution)
        path = _resolve_hls_path(str(movie_id), resolution, MANIFEST_NAME)
        return FileResponse(path.open('rb'), content_type=MIME_HLS_MANIFEST)


class HlsSegmentView(HlsBaseView):
    """Serve a single HLS segment for a video and resolution."""

    def get(self, request, movie_id, resolution, segment):
        self.validate(movie_id, resolution)
        path = _resolve_hls_path(str(movie_id), resolution, segment)
        return FileResponse(path.open('rb'), content_type=MIME_HLS_SEGMENT)
