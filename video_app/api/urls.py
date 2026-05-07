from django.urls import path

from .views import HlsManifestView, HlsSegmentView, VideoListView


urlpatterns = [
    path(
        'video/',
        VideoListView.as_view(),
        name='video-list',
    ),
    path(
        'video/<int:movie_id>/<str:resolution>/index.m3u8',
        HlsManifestView.as_view(),
        name='video-stream',
    ),
    path(
        'video/<int:movie_id>/<str:resolution>/<str:segment>/',
        HlsSegmentView.as_view(),
        name='video-segment',
    ),
]
