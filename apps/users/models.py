from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from pgvector.django import VectorField

import uuid

# Create your models here.
class User(AbstractUser):

    profile_image = models.ImageField(upload_to='medias/profile', null=True, blank=True, verbose_name='Profile Image')
    bio = models.TextField(null=True, blank=True, verbose_name='Bio')
    professional_area = models.JSONField(null=True, blank=True, default=dict, verbose_name='Professional Area', help_text='{"area": "description"}')
    gender = models.CharField(max_length=1, choices=(('M', 'Male'), ('F', 'Female'), ('U', 'unknown')))
    watched_stocks = models.ManyToManyField('stocks.Stock', related_name='watchers', through='watchlist.Watchlist',through_fields=('user', 'stock'), blank=True, verbose_name='Watched Stocks')


    def __str__(self):
        return super().__str__()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
        

class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='Profile ID', help_text='Unique identifier for the user profile')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    user_self_portrait = models.TextField(null=True, blank=True, verbose_name='Self Portrait', help_text='A brief self-description or portrait of the user')
    preferred_topic = models.JSONField(default=list, blank=True, verbose_name='Preferred Topics', help_text='List of topics the user is interested in')
    excluded_topic = models.JSONField(default=list, blank=True, verbose_name='Excluded Topics', help_text='List of topics the user is not interested in')
    
    interest_embedding = VectorField(dimensions=768, null=True, blank=True, verbose_name='Interest Embedding', help_text='Embedding vector representing the user\'s interests')
    is_processed_for_embedding = models.BooleanField(default=False, db_index=True, verbose_name='Processed for Embedding', help_text='Flag indicating if the user profile has been processed for embedding')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Last Updated', help_text='Timestamp of the last update to the user profile')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At', help_text='Timestamp when the user profile was created')
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user'], name='user_profile_user_idx'),
            models.Index(fields=['is_processed_for_embedding'], name='user_profile_processed_idx'),
        ]
    def __str__(self):
        return f"{self.user.username} Profile"
    

    @property
    def perferred_topic_text(self):
        return ', '.join(self.preferred_topic) if self.preferred_topic else 'No preferred topics'
    