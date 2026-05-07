from rest_framework import serializers

from video_app.models import Video


class VideoSerializer(serializers.ModelSerializer):
    """Serializer for the public video listing endpoint."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = [
            'id',
            'created_at',
            'title',
            'description',
            'thumbnail_url',
            'category',
        ]
        read_only_fields = ['id', 'created_at', 'thumbnail_url']

    def get_thumbnail_url(self, obj):
        request = self.context.get('request')
        if not obj.thumbnail_url:
            return None
        if request is None:
            return obj.thumbnail_url.url
        return request.build_absolute_uri(obj.thumbnail_url.url)
