from django.db import models

# Create your models here.
class NewsArticle(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    url = models.URLField(max_length=500, unique=True, db_index=True)
    source_name = models.CharField(max_length=100, db_index=True)
    published_at = models.DateTimeField(db_index=True)
    content = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)

    try:
        from django.contrib.postgres.fields import JSONField
    except ImportError:
        from django.db.models import JSONField

    #raw_data = JSONField(null=True, blank=True)

    summary = models.TextField(null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    categories = models.TextField(null=True, blank=True)

    #created_at = models.DateTimeField(auto_now_add=True,)


    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return f"{self.title} - {self.source_name} - {self.published_at}"


        