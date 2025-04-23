
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from apps.stocks.models import Stock
from apps.stocks.serializers import StocksSerializer
from apps.watchlist.models import Watchlist


class WatchlistSerializer(serializers.ModelSerializer):

    stock = StocksSerializer(read_only=True)
    stock_id = serializers.PrimaryKeyRelatedField(queryset=Stock.objects.all(), source= 'stock', write_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Watchlist
        fields = (
            'id',
            'user',
            'stock',
            'stock_id',
            'interest_level',
            'position_shares',
            'average_cost_price',
            'notes',
            'added_at',
            'alert_settings'
        )
        read_only_fields = ('id', 'user', 'added_at')


class WatchlistCreateUpdateSerializer(serializers.ModelSerializer):
    stock = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Watchlist
        fields = (
            'stock',
            'interest_level',
            'position_shares',
            'average_cost_price',
            'notes',
            'alert_settings'
        )


