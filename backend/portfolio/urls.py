from django.urls import path
from .views import PortfolioDashboardView

urlpatterns = [
    path('dashboard/', PortfolioDashboardView.as_view(), name='dashboard'),
]