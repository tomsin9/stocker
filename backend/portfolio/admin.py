from django.contrib import admin
from .models import Asset, Transaction

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'currency', 'current_price', 'last_price_updated')
    search_fields = ('symbol', 'name')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'action', 'asset', 'price', 'quantity', 'total_amount')
    list_filter = ('action', 'asset')
    date_hierarchy = 'date'