from django.shortcuts import render
from rest_framework import viewsets, permissions

from apps.stocks.models import Stock
from apps.stocks.serializers import StocksSerializer


# Create your views here.
class StockViewSet(viewsets.ModelViewSet):
    """
    A viewset for viewing and editing stock instances.
    """
    queryset = Stock.objects.all()
    serializer_class = StocksSerializer
    permission_classes = [permissions.AllowAny]
