
from rest_framework import serializers

from apps.stocks.models import Stock



class StocksSerializer(serializers.ModelSerializer):

    class Meta:
        model = Stock
        fields = '__all__'
        read_only_fields = ('id', 'last_updated_at')


