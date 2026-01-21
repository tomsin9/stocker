
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Asset, Transaction, CashFlow, AccountBalance
from .services import (
    calculate_position, 
    get_total_invested_capital, 
    calculate_current_cash,
    get_usd_to_hkd_rate,
    validate_symbol_with_yfinance,
    normalize_symbol,
    search_stocks_in_cache,
    add_stock_to_cache,
    load_stock_list_cache,
    is_cache_valid
)
from .serializers import (
    PortfolioSummarySerializer, 
    TransactionSerializer, 
    CashFlowSerializer,
    AccountBalanceSerializer,
    TransactionListSerializer,
    UnifiedTransactionSerializer
)
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import yfinance as yf
import csv, io

class PortfolioDashboardView(APIView):
    """
    獲取投資組合儀表板數據
    權限：需要登入，只返回當前用戶的數據
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # 獲取匯率
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        
        # 獲取當前用戶有交易的所有資產（避免 N+1 查詢）
        user_assets = Asset.objects.filter(
            transactions__user=user
        ).distinct().prefetch_related('transactions')
        
        data = []
        
        # 計算總持股市值（統一為 USD）
        total_market_value = Decimal('0.00')
        # 分別計算多頭和空頭市值（用於 Gross Position）
        total_long_market_value = Decimal('0.00')
        total_short_market_value = Decimal('0.00')
        
        for asset in user_assets:
            # 呼叫我們的 FIFO 計算邏輯（統一轉換為 USD）
            stats = calculate_position(asset, user, usd_to_hkd_rate)
            
            # 只回傳目前還有持倉的（包括負數持倉/賣空）
            # 已平倉（quantity = 0）的資產不顯示，即使有已實現損益
            if stats['quantity'] != 0:
                data.append(stats)
                total_market_value += Decimal(str(stats['current_market_value']))  # 負數持倉時市值為負值
                total_long_market_value += Decimal(str(stats.get('long_market_value', 0)))  # 多頭市值
                total_short_market_value += Decimal(str(stats.get('short_market_value', 0)))  # 空頭市值（絕對值）
        
        # 計算目前可用現金（支持多幣種）
        cash_data = calculate_current_cash(user, base_currency='USD')
        current_cash_usd = cash_data['USD']
        current_cash_hkd = cash_data['HKD']
        current_cash_total = cash_data['total_in_base']  # 以 USD 為基準的總額
        
        # 計算總投入本金（假設為 USD）
        total_invested = get_total_invested_capital(user)
        
        # 計算 Net Liquidity (淨資產) = 總持股市值 + 目前可用現金（全部為 USD）
        # 這是真正擁有的錢
        net_liquidity = total_market_value + current_cash_total
        
        # 計算 Gross Position (總部位) = 做多市值 + 做空市值的絕對值
        # 代表你玩多大
        gross_position = total_long_market_value + total_short_market_value
        
        # 保持向後兼容：total_assets = net_liquidity
        total_assets = net_liquidity
        
        # 計算所有資產折算為港幣的總額
        total_equity_hks = (total_market_value * usd_to_hkd_rate) + current_cash_hkd + (current_cash_usd * usd_to_hkd_rate)
        
        # 計算淨利潤 = 淨資產 - 總投入本金
        net_profit = net_liquidity - total_invested
        
        # 計算總回報率 = (淨資產 - 總投入本金) / 總投入本金 * 100%
        roi_percentage = Decimal('0.00')
        if total_invested > 0:
            roi_percentage = (net_profit / total_invested) * Decimal('100.00')
        
        # 序列化並回傳
        serializer = PortfolioSummarySerializer(data, many=True)
        
        return Response({
            'positions': serializer.data,
            'summary': {
                'total_invested': float(total_invested),
                'current_cash': float(current_cash_total),  # 保持向後兼容
                'current_cash_usd': float(current_cash_usd),
                'current_cash_hkd': float(current_cash_hkd),
                'cash_balances': {
                    'USD': float(current_cash_usd),
                    'HKD': float(current_cash_hkd)
                },
                'total_market_value': float(total_market_value),
                'total_equity_hks': float(total_equity_hks),  # 所有資產折算為港幣的總額
                'total_assets': float(total_assets),  # 保持向後兼容，等於 net_liquidity
                'net_liquidity': float(net_liquidity),  # 淨資產：總市值 + 總現金（真正擁有的錢）
                'gross_position': float(gross_position),  # 總部位：做多市值 + 做空市值的絕對值（代表玩多大）
                'net_profit': float(net_profit),
                'roi_percentage': float(roi_percentage),
                'exchange_rate': float(usd_to_hkd_rate),
                'usd_to_hkd_rate': float(usd_to_hkd_rate)  # 保持向後兼容
            }
        })

# 1. 處理單筆新增
class AddTransactionView(APIView):
    """
    新增單筆交易記錄
    權限：需要登入，自動關聯到當前用戶
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. 處理 CSV 上傳
class CSVImportView(APIView):
    """
    匯入 CSV 交易記錄
    權限：需要登入，所有交易自動關聯到當前用戶
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=400)
        
        # 讀取 CSV 內容
        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
        except Exception as e:
            return Response({"error": f"Failed to read CSV file: {str(e)}"}, status=400)
        
        count_created = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):  # 從第2行開始（第1行是header）
            try:
                # 解析 CSV 行並創建交易
                # 注意：這裡需要根據實際 CSV 格式調整
                symbol = row.get('symbol', '').strip().upper()
                if not symbol:
                    continue
                
                # 獲取或創建資產（不需要保存公司名稱，從緩存中獲取即可）
                # 如果緩存中沒有，嘗試通過 yfinance 獲取並添加到緩存
                from .services import load_stock_list_cache, validate_symbol_with_yfinance, add_stock_to_cache
                cache_data = load_stock_list_cache()
                stocks = cache_data.get('stocks', [])
                cached_stock = next((s for s in stocks if s.get('symbol') == symbol), None)
                
                # 如果緩存中沒有，嘗試通過 yfinance 獲取並添加到緩存
                if not cached_stock:
                    try:
                        is_valid, symbol_normalized, name, currency, _ = validate_symbol_with_yfinance(symbol)
                        if is_valid:
                            add_stock_to_cache(symbol_normalized, name, currency)
                    except:
                        pass  # 如果獲取失敗，繼續
                
                asset, created = Asset.objects.get_or_create(symbol=symbol)
                
                # 創建交易記錄（需要根據實際 CSV 格式調整）
                # 這裡只是示例，實際需要根據 CSV 格式解析
                transaction = Transaction.objects.create(
                    user=user,  # 確保關聯到當前用戶
                    asset=asset,
                    action=row.get('action', 'BUY'),
                    date=row.get('date', timezone.now().date()),
                    price=Decimal(row.get('price', 0)),
                    quantity=Decimal(row.get('quantity', 0)),
                    fees=Decimal(row.get('fees', 0)),
                )
                count_created += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        response_data = {
            "message": f"Successfully imported {count_created} transactions",
            "count": count_created
        }
        
        if errors:
            response_data["errors"] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)

# 3. 更新所有資產的價格（只更新當前用戶有交易的資產）
class UpdatePricesView(APIView):
    """
    更新股票價格（使用 yfinance）
    權限：需要登入，只更新當前用戶有交易的資產
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        # 只更新當前用戶有交易的資產
        assets = Asset.objects.filter(transactions__user=user).distinct()
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
    權限：需要登入，只返回當前用戶的記錄
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CashFlowSerializer
    
    def get_queryset(self):
        """只返回當前用戶的現金流記錄"""
        return CashFlow.objects.filter(user=self.request.user).order_by('-date', '-created_at')
    
    def get_serializer_context(self):
        """傳遞 request 到 serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

class CashFlowDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    取得、更新或刪除單筆現金流記錄
    權限檢查：需要登入，只能訪問自己的記錄
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CashFlowSerializer
    
    def get_queryset(self):
        """只返回當前用戶的現金流記錄，確保用戶無法訪問其他用戶的數據"""
        return CashFlow.objects.filter(user=self.request.user)
    
    def get_serializer_context(self):
        """傳遞 request 到 serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def get_object(self):
        """
        獲取對象，如果對象不屬於當前用戶則返回 404
        這樣不會洩露資源是否存在的信息
        """
        obj = super().get_object()
        # get_queryset 已經過濾了，這裡再次確認（雙重保護）
        if obj.user != self.request.user:
            from rest_framework.exceptions import NotFound
            raise NotFound("Not found.")
        return obj

class AccountBalanceView(APIView):
    """
    取得目前的現金餘額
    權限：需要登入，只返回當前用戶的現金餘額
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        current_cash = calculate_current_cash(user)
        return Response({
            'available_cash': float(current_cash)
        })

class TransactionListView(APIView):
    """
    列出所有交易記錄（包括 Transaction 和 CashFlow）
    權限：需要登入，只返回當前用戶的交易記錄
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """合併返回 Transaction 和 CashFlow 記錄"""
        user = request.user
        
        # 獲取過濾參數
        action = request.query_params.get('action', None)  # BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW
        date_range = request.query_params.get('date_range', '7d')  # 7d, 30d, 90d, all
        symbol = request.query_params.get('symbol', None)
        
        # 計算日期範圍（默認最近7天）
        today = timezone.now().date()
        if date_range == '7d':
            start_date = today - timedelta(days=7)
        elif date_range == '30d':
            start_date = today - timedelta(days=30)
        elif date_range == '90d':
            start_date = today - timedelta(days=90)
        else:  # 'all'
            start_date = None
        
        # 獲取交易記錄
        transactions = Transaction.objects.filter(
            user=user
        ).select_related('asset')
        
        # 獲取現金流記錄
        cashflows = CashFlow.objects.filter(
            user=user
        )
        
        # 應用日期過濾
        if start_date:
            transactions = transactions.filter(date__gte=start_date)
            cashflows = cashflows.filter(date__gte=start_date)
        
        # 應用 action 過濾
        if action:
            if action in ['BUY', 'SELL', 'DIVIDEND']:
                transactions = transactions.filter(action=action)
                cashflows = cashflows.none()  # 現金流不匹配這些 action
            elif action in ['DEPOSIT', 'WITHDRAW']:
                transactions = transactions.none()  # 交易不匹配這些 action
                cashflows = cashflows.filter(type=action)
        
        # 如果提供了 symbol 參數，只過濾該股票的交易
        if symbol:
            transactions = transactions.filter(asset__symbol=symbol)
            # CashFlow 不受 symbol 參數影響
        
        # 排序
        transactions = transactions.order_by('-date', '-created_at')
        cashflows = cashflows.order_by('-date', '-created_at')
        
        # 合併兩種記錄
        all_records = []
        for tx in transactions:
            all_records.append(tx)
        for cf in cashflows:
            all_records.append(cf)
        
        # 按日期和創建時間排序（最新的在前）
        all_records.sort(key=lambda x: (x.date, x.created_at), reverse=True)
        
        # 序列化
        serializer = UnifiedTransactionSerializer(all_records, many=True)
        return Response(serializer.data)

class TransactionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    取得、更新或刪除單筆交易記錄
    權限檢查：需要登入，只能訪問自己的記錄
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionListSerializer
    
    def get_queryset(self):
        """只返回當前用戶的交易記錄，確保用戶無法訪問其他用戶的數據"""
        return Transaction.objects.filter(user=self.request.user).select_related('asset')
    
    def get_object(self):
        """
        獲取對象，如果對象不屬於當前用戶則返回 404
        這樣不會洩露資源是否存在的信息
        """
        obj = super().get_object()
        # get_queryset 已經過濾了，這裡再次確認（雙重保護）
        if obj.user != self.request.user:
            from rest_framework.exceptions import NotFound
            raise NotFound("Not found.")
        return obj
    
    def destroy(self, request, *args, **kwargs):
        """刪除交易後，返回成功訊息"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Transaction deleted successfully"},
            status=status.HTTP_200_OK
        )

class ValidateSymbolView(APIView):
    """
    驗證股票代號是否有效
    權限：需要登入
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/validate-symbol/
        請求體: {"symbol": "AAPL"} 或 {"symbol": "0700"}
        返回: {
            "valid": true,
            "symbol": "AAPL" 或 "0700.HK",
            "name": "Apple Inc.",
            "currency": "USD" 或 "HKD",
            "error": null
        }
        """
        symbol = request.data.get('symbol', '').strip()
        
        if not symbol:
            return Response(
                {"valid": False, "symbol": "", "name": None, "currency": None, "error": "股票代號不能為空"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 使用 yfinance 驗證
        is_valid, symbol_normalized, name, currency, error_msg = validate_symbol_with_yfinance(symbol)
        
        if is_valid:
            # 添加到緩存
            add_stock_to_cache(symbol_normalized, name, currency)
            
            return Response({
                "valid": True,
                "symbol": symbol_normalized,
                "name": name,
                "currency": currency,
                "error": None
            })
        else:
            return Response({
                "valid": False,
                "symbol": symbol_normalized,
                "name": None,
                "currency": None,
                "error": error_msg or "無法驗證股票代號"
            }, status=status.HTTP_400_BAD_REQUEST)

class SearchStocksView(APIView):
    """
    搜索股票（從緩存中）
    權限：需要登入
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/search-stocks/?q=AAPL
        返回匹配的股票列表
        """
        query = request.query_params.get('q', '').strip()
        
        # 從緩存中搜索
        matches = search_stocks_in_cache(query)
        
        return Response({
            "stocks": matches,
            "count": len(matches)
        })

class StockListCacheView(APIView):
    """
    獲取或刷新股票列表緩存
    權限：需要登入
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/stock-list-cache/
        返回緩存信息和股票列表
        """
        cache_data = load_stock_list_cache()
        is_valid = is_cache_valid(cache_data)
        
        return Response({
            "stocks": cache_data.get('stocks', []),
            "last_updated": cache_data.get('last_updated'),
            "is_valid": is_valid,
            "count": len(cache_data.get('stocks', []))
        })