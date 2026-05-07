from django.db import models


class Video(models.Model):
    """A video uploaded to Videoflix and its conversion metadata."""

    class ConversionStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    class Category(models.TextChoices):
        ACTION = 'action', 'Action'
        ADVENTURE = 'adventure', 'Adventure'
        ANIMATION = 'animation', 'Animation'
        COMEDY = 'comedy', 'Comedy'
        CRIME = 'crime', 'Crime'
        DOCUMENTARY = 'documentary', 'Documentary'
        DRAMA = 'drama', 'Drama'
        FAMILY = 'family', 'Family'
        FANTASY = 'fantasy', 'Fantasy'
        KIDS = 'kids', 'Kids'
        HORROR = 'horror', 'Horror'
        MYSTERY = 'mystery', 'Mystery'
        ROMANCE = 'romance', 'Romance'
        SCI_FI = 'sci-fi', 'Sci-Fi'
        THRILLER = 'thriller', 'Thriller'

    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=Category.choices)
    video_file = models.FileField(upload_to='videos/')
    thumbnail_url = models.FileField(
        upload_to='thumbnails/', null=True, blank=True
    )
    conversion_status = models.CharField(
        max_length=20,
        choices=ConversionStatus.choices,
        default=ConversionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


