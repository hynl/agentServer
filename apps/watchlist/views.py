from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core import permissions
from apps.watchlist.models import Watchlist
from apps.watchlist.serializers import WatchlistCreateUpdateSerializer, WatchlistSerializer


# Create your views here.
class WatchlistViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsOwnerOrReadOnly, IsAuthenticated)

    def get_queryset(self):
        return Watchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return WatchlistCreateUpdateSerializer
        return WatchlistSerializer
