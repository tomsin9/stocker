from django.urls import path
from .views import (
    PortfolioDashboardView, 
    AddTransactionView, 
    CSVImportView, 
    UpdatePricesView,
    CashFlowListCreateView,
    CashFlowDetailView,
    AccountBalanceView,
    TransactionListView
)

urlpatterns = [
    path('dashboard/', PortfolioDashboardView.as_view(), name='dashboard'),
    path('add-transaction/', AddTransactionView.as_view(), name='add-transaction'),
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('import-csv/', CSVImportView.as_view(), name='import-csv'),
    path('update-prices/', UpdatePricesView.as_view(), name='update-prices'),
    path('cashflow/', CashFlowListCreateView.as_view(), name='cashflow-list-create'),
    path('cashflow/<int:pk>/', CashFlowDetailView.as_view(), name='cashflow-detail'),
    path('account-balance/', AccountBalanceView.as_view(), name='account-balance'),
]