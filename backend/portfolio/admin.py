from django.contrib import admin
from .models import Asset, Transaction, CashFlow, AccountBalance

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'currency', 'current_price', 'last_price_updated')
    search_fields = ('symbol', 'name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'action', 'asset', 'price', 'quantity', 'total_amount')
    list_filter = ('action', 'asset')
    date_hierarchy = 'date'

@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ('date', 'amount', 'type')
    list_filter = ('type',)
    date_hierarchy = 'date'

@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = ('available_cash', 'last_updated')
    search_fields = ('available_cash',)
    date_hierarchy = 'last_updated'