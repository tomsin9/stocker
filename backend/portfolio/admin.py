from posixpath import curdir
from django.contrib import admin
from .models import Asset, Transaction, CashFlow, AccountBalance

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'currency', 'current_price', 'last_price_updated')
    search_fields = ('symbol', 'name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'action', 'asset', 'currency', 'price', 'quantity', 'total_amount')
    list_filter = ('user', 'currency', 'action', 'asset')
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')

@admin.register(CashFlow)
class CashFlowAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'currency', 'amount', 'type')
    list_filter = ('type', 'user', 'currency')
    date_hierarchy = 'date'

@admin.register(AccountBalance)
class AccountBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'cash_usd', 'cash_hkd', 'total_in_base', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'last_updated'
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Cash Balances', {
            'fields': ('cash_usd', 'cash_hkd', 'total_in_base', 'available_cash')
        }),
        ('Metadata', {
            'fields': ('last_updated',)
        }),
    )