
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from .models import Asset, Transaction, CashFlow, AccountBalance
from .services import (
    calculate_position, 
    get_total_invested_capital, 
    calculate_current_cash,
    get_usd_to_hkd_rate
)
from .serializers import (
    PortfolioSummarySerializer, 
    TransactionSerializer, 
    CashFlowSerializer,
    AccountBalanceSerializer,
    TransactionListSerializer
)
from django.utils import timezone
from decimal import Decimal
import yfinance as yf
import csv, io

class PortfolioDashboardView(APIView):
    def get(self, request):
        # 獲取匯率
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        
        assets = Asset.objects.all()
        data = []
        
        # 計算總持股市值（統一為 USD）
        total_market_value = Decimal('0.00')
        
        for asset in assets:
            # 呼叫我們的 FIFO 計算邏輯（統一轉換為 USD）
            stats = calculate_position(asset, usd_to_hkd_rate)
            
            # 只回傳目前還有持倉，或者曾經有賺賠紀錄的
            if stats['quantity'] > 0 or stats['realized_pl'] != 0:
                data.append(stats)
                total_market_value += Decimal(str(stats['current_market_value']))
        
        # 計算目前可用現金（考慮所有交易和現金流，假設為 USD）
        current_cash = calculate_current_cash()
        
        # 計算總投入本金（假設為 USD）
        total_invested = get_total_invested_capital()
        
        # 計算總資產 = 總持股市值 + 目前可用現金（全部為 USD）
        total_assets = total_market_value + Decimal(str(current_cash))
        
        # 計算淨利潤 = 總資產 - 總投入本金
        net_profit = total_assets - total_invested
        
        # 計算總回報率 = (總資產 - 總投入本金) / 總投入本金 * 100%
        roi_percentage = Decimal('0.00')
        if total_invested > 0:
            roi_percentage = (net_profit / total_invested) * Decimal('100.00')
        
        # 序列化並回傳
        serializer = PortfolioSummarySerializer(data, many=True)
        
        return Response({
            'positions': serializer.data,
            'summary': {
                'total_invested': float(total_invested),
                'current_cash': float(current_cash),
                'total_market_value': float(total_market_value),
                'total_assets': float(total_assets),
                'net_profit': float(net_profit),
                'roi_percentage': float(roi_percentage),
                'usd_to_hkd_rate': float(usd_to_hkd_rate)
            }
        })

# 1. 處理單筆新增
class AddTransactionView(APIView):
    def post(self, request):
        serializer = TransactionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. 處理 CSV 上傳
class CSVImportView(APIView):
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=400)
        
        # 讀取 CSV 內容 (這部分邏輯可以重用之前 import_trades.py 的代碼)
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        for row in reader:
            # 這裡實作跟之前 command 一樣的解析邏輯...
            # (為了簡潔，這裡省略重複代碼，重點在於透過 API 觸發)
            pass
            
        return Response({"message": "CSV processed successfully"})

# 3. 更新所有資產的價格
class UpdatePricesView(APIView):
    def post(self, request):
        assets = Asset.objects.all()
        updated_count = 0
        errors = []
        
        for asset in assets:
            try:
                ticker = yf.Ticker(asset.symbol)
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                
                if current_price:
                    asset.current_price = current_price
                    asset.last_price_updated = timezone.now()
                    asset.save()
                    updated_count += 1
                else:
                    errors.append(f"{asset.symbol}: 無法取得價格")
            except Exception as e:
                errors.append(f"{asset.symbol}: {str(e)}")
        
        response_data = {
            "message": f"已更新 {updated_count} 個資產的價格",
            "updated_count": updated_count
        }
        
        if errors:
            response_data["errors"] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)

# CashFlow CRUD Views
class CashFlowListCreateView(generics.ListCreateAPIView):
    """
    列出所有現金流記錄，或創建新的現金流記錄
    """
    queryset = CashFlow.objects.all()
    serializer_class = CashFlowSerializer

class CashFlowDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    取得、更新或刪除單筆現金流記錄
    """
    queryset = CashFlow.objects.all()
    serializer_class = CashFlowSerializer

class AccountBalanceView(APIView):
    """
    取得目前的現金餘額
    """
    def get(self, request):
        current_cash = AccountBalance.get_current_balance()
        return Response({
            'available_cash': float(current_cash)
        })

class TransactionListView(generics.ListAPIView):
    """
    列出所有交易記錄
    """
    queryset = Transaction.objects.select_related('asset').order_by('-date', '-created_at')
    serializer_class = TransactionListSerializer