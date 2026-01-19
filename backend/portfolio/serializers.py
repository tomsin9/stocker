from rest_framework import serializers
from .models import Asset, Transaction, CashFlow, AccountBalance

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'currency', 'current_price']

class PortfolioSummarySerializer(serializers.Serializer):
    symbol = serializers.CharField()
    currency = serializers.CharField(required=False)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4)
    avg_cost = serializers.DecimalField(max_digits=12, decimal_places=4)
    realized_pl = serializers.DecimalField(max_digits=12, decimal_places=2)
    unrealized_pl = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_market_value = serializers.DecimalField(max_digits=12, decimal_places=2)

class TransactionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(write_only=True, help_text="股票代號")
    
    class Meta:
        model = Transaction
        fields = ['symbol', 'action', 'date', 'price', 'quantity', 'fees', 'notes']
    
    def create(self, validated_data):
        symbol = validated_data.pop('symbol')
        asset, created = Asset.objects.get_or_create(symbol=symbol)
        validated_data['asset'] = asset
        return Transaction.objects.create(**validated_data)

class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = ['id', 'amount', 'type', 'date', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

class AccountBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBalance
        fields = ['available_cash', 'last_updated']
        read_only_fields = ['last_updated']

class TransactionListSerializer(serializers.ModelSerializer):
    """序列化交易記錄，包含資產資訊"""
    symbol = serializers.CharField(source='asset.symbol', read_only=True)
    
    class Meta:
        model = Transaction
        fields = ['id', 'symbol', 'action', 'date', 'price', 'quantity', 'fees', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']