from rest_framework import serializers
from .models import Asset, Transaction

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'currency', 'current_price']

class PortfolioSummarySerializer(serializers.Serializer):
    symbol = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4)
    avg_cost = serializers.DecimalField(max_digits=12, decimal_places=4)
    realized_pl = serializers.DecimalField(max_digits=12, decimal_places=2)
    unrealized_pl = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_market_value = serializers.DecimalField(max_digits=12, decimal_places=2)