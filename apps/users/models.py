from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser

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