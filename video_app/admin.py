from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'conversion_status', 'created_at')
    list_filter = ('category', 'conversion_status')
    search_fields = ('title', 'description')
    readonly_fields = ('thumbnail_url', 'conversion_status', 'created_at')
    ordering = ('-created_at',)
