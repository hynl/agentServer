from django.db import models
from pgvector.django import VectorField
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField

class NewsSource(models.Model):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    url = models.URLField(max_length=2048, unique=True, db_index=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = "News Source"
        verbose_name_plural = "News Sources"
        indexes = [
            models.Index(fields=['name'], name='news_source_name_idx'),
            models.Index(fields=['url'], name='news_source_url_idx'),
        ]

    def __str__(self):
        return self.name

# Create your models here.
class NewsArticle(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    url = models.URLField(max_length=500, unique=True, db_index=True)
    source_name = models.CharField(max_length=100, db_index=True)
    published_at = models.DateTimeField(db_index=True)
    content = models.TextField(null=True, blank=True)
    author = models.CharField(max_length=255, null=True, blank=True)

    summary = models.TextField(null=True, blank=True)
    # Only for openai embedding
    # If you use other embedding models, you can change the dimensions accordingly
    embedding = VectorField(dimensions=768, null=True, blank=True)
    is_processed_for_embedding = models.BooleanField(default=False)
    
    keywords = ArrayField(models.CharField(max_length=100), blank=True, default=list, verbose_name=_("Identified Keywords"))
    categories = ArrayField(models.CharField(max_length=100), blank=True, default=list, verbose_name=_("Identified Categories")) # Added

    #created_at = models.DateTimeField(auto_now_add=True,)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return f"{self.title} - {self.source_name} - {self.published_at}"

