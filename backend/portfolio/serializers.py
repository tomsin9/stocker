from rest_framework import serializers
from .models import Asset, Transaction, CashFlow, AccountBalance
from .services import (
    validate_symbol_with_yfinance,
    normalize_symbol,
    add_stock_to_cache,
    detect_asset_currency
)

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['id', 'symbol', 'name', 'currency', 'current_price']

class PortfolioSummarySerializer(serializers.Serializer):
    symbol = serializers.CharField()
    name = serializers.CharField(required=False, allow_blank=True, default='')  # 公司名稱
    currency = serializers.CharField(required=False, default='USD')
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
        read_only_fields = ['user']
    
    def validate_symbol(self, value):
        """
        驗證股票代號
        """
        if not value or not value.strip():
            raise serializers.ValidationError("股票代號不能為空")
        
        symbol = value.strip()
        
        # 驗證股票代號（使用 yfinance）
        try:
            is_valid, symbol_normalized, name, currency, error_msg = validate_symbol_with_yfinance(symbol)
            
            if not is_valid:
                # 提供友好的錯誤訊息
                if error_msg:
                    raise serializers.ValidationError(error_msg)
                else:
                    raise serializers.ValidationError(f"股票代號 '{symbol}' 無效或無法驗證")
            
            # 添加到緩存
            add_stock_to_cache(symbol_normalized, name, currency)
            
            # 將名稱和幣種保存到實例變量，供 create 方法使用
            self._validated_symbol_name = name
            self._validated_symbol_currency = currency
            
            # 返回標準化的股票代號
            return symbol_normalized
        except serializers.ValidationError:
            # 重新拋出驗證錯誤
            raise
        except Exception as e:
            # 處理其他異常
            raise serializers.ValidationError(f"驗證股票代號時發生錯誤: {str(e)}")
    
    def create(self, validated_data):
        symbol = validated_data.pop('symbol')
        
        # 標準化股票代號（雖然 validate_symbol 已經處理，但這裡再確保一次）
        symbol_normalized = normalize_symbol(symbol)
        
        # 從驗證結果中獲取幣種（如果有的話）
        currency = getattr(self, '_validated_symbol_currency', None) or detect_asset_currency(symbol_normalized)
        
        # 獲取當前匯率
        from .services import get_usd_to_hkd_rate
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        
        # 獲取或創建資產（不需要保存公司名稱，從緩存中獲取即可）
        asset, created = Asset.objects.get_or_create(
            symbol=symbol_normalized,
            defaults={'currency': currency}
        )
        
        # 如果資產已存在但幣種不同，更新幣種
        if not created and asset.currency != currency:
            asset.currency = currency
            asset.save()
        
        validated_data['asset'] = asset
        validated_data['currency'] = currency
        validated_data['exchange_rate'] = usd_to_hkd_rate  # 保存交易時的匯率
        # 自動設置當前用戶
        validated_data['user'] = self.context['request'].user
        return Transaction.objects.create(**validated_data)

class CashFlowSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashFlow
        fields = ['id', 'amount', 'type', 'date', 'notes', 'currency', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']
    
    def create(self, validated_data):
        # 如果沒有指定幣種，默認為 USD
        if 'currency' not in validated_data or not validated_data['currency']:
            validated_data['currency'] = 'USD'
        
        # 獲取當前匯率
        from .services import get_usd_to_hkd_rate
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        validated_data['exchange_rate'] = usd_to_hkd_rate
        
        # 自動設置當前用戶
        validated_data['user'] = self.context['request'].user
        return CashFlow.objects.create(**validated_data)

class AccountBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountBalance
        fields = ['available_cash', 'last_updated']
        read_only_fields = ['last_updated']

class TransactionListSerializer(serializers.ModelSerializer):
    """序列化交易記錄，包含資產資訊"""
    symbol = serializers.CharField(source='asset.symbol', read_only=True, allow_null=True)
    currency = serializers.CharField(source='asset.currency', read_only=True, allow_null=True)
    # 如果 transaction 有 currency 字段，優先使用
    transaction_currency = serializers.CharField(source='currency', read_only=True, required=False)
    
    class Meta:
        model = Transaction
        fields = ['id', 'symbol', 'action', 'date', 'price', 'quantity', 'fees', 'notes', 'currency', 'transaction_currency', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """確保返回正確的幣種信息"""
        data = super().to_representation(instance)
        # 優先使用 transaction 的 currency，否則使用 asset 的 currency
        if instance.currency:
            data['currency'] = instance.currency
        elif instance.asset and instance.asset.currency:
            data['currency'] = instance.asset.currency
        else:
            data['currency'] = 'USD'  # 默認值
        # 添加記錄類型標識
        data['record_type'] = 'transaction'
        return data

class UnifiedTransactionSerializer(serializers.Serializer):
    """統一的交易記錄序列化器，處理 Transaction 和 CashFlow"""
    id = serializers.IntegerField()
    record_type = serializers.CharField()  # 'transaction' 或 'cashflow'
    action = serializers.CharField()  # BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW
    date = serializers.DateField()
    currency = serializers.CharField()
    notes = serializers.CharField(allow_null=True, allow_blank=True)
    created_at = serializers.DateTimeField()
    
    # Transaction 專用字段
    symbol = serializers.CharField(allow_null=True, required=False)
    price = serializers.DecimalField(max_digits=12, decimal_places=4, allow_null=True, required=False)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=4, allow_null=True, required=False)
    fees = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True, required=False)
    
    # CashFlow 專用字段
    amount = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True, required=False)
    
    def to_representation(self, instance):
        """根據實例類型返回不同的數據結構"""
        if isinstance(instance, Transaction):
            # 處理 Transaction
            data = {
                'id': instance.id,
                'record_type': 'transaction',
                'action': instance.action,
                'date': instance.date,
                'currency': instance.currency or (instance.asset.currency if instance.asset else 'USD'),
                'notes': instance.notes,
                'created_at': instance.created_at,
                'symbol': instance.asset.symbol if instance.asset else None,
                'price': instance.price,
                'quantity': instance.quantity,
                'fees': instance.fees,
                'amount': None
            }
        elif isinstance(instance, CashFlow):
            # 處理 CashFlow
            data = {
                'id': instance.id,
                'record_type': 'cashflow',
                'action': instance.type,  # DEPOSIT 或 WITHDRAW
                'date': instance.date,
                'currency': instance.currency,
                'notes': instance.notes,
                'created_at': instance.created_at,
                'symbol': None,
                'price': None,
                'quantity': None,
                'fees': None,
                'amount': instance.amount
            }
        else:
            raise ValueError(f"Unknown instance type: {type(instance)}")
        
        return data