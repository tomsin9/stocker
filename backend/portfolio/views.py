
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch
from .models import Asset, Transaction, CashFlow, AccountBalance, DailySnapshot
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
    is_cache_valid,
    update_account_balance_cache,
    recalculate_account_balance,
    calculate_monthly_tracking
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
        # 使用 Prefetch 來過濾用戶的交易，避免在 calculate_position 中再次查詢
        user_transactions_prefetch = Prefetch(
            'transactions',
            queryset=Transaction.objects.filter(user=user).order_by('date', 'created_at'),
            to_attr='user_transactions'
        )
        user_assets = Asset.objects.filter(
            transactions__user=user
        ).distinct().prefetch_related(user_transactions_prefetch)
        
        data = []
        
        # 計算總持股市值（統一為 USD）
        total_market_value = Decimal('0.00')
        # 分別計算多頭和空頭市值（用於 Gross Position）
        total_long_market_value = Decimal('0.00')
        total_short_market_value = Decimal('0.00')
        
        for asset in user_assets:
            # 呼叫我們的 FIFO 計算邏輯（統一轉換為 USD）
            # 傳入 prefetched transactions 以避免 N+1 查詢
            prefetched_txns = getattr(asset, 'user_transactions', None)
            stats = calculate_position(asset, user, usd_to_hkd_rate, prefetched_transactions=prefetched_txns)
            
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
    支援格式：Ticker, 股數, 買入價, 賣出價, 買入時間, 賣出時間（一行代表一筆來回，會自動拆成 BUY + SELL）
    權限：需要登入，所有交易自動關聯到當前用戶
    """
    permission_classes = [IsAuthenticated]

    def _parse_date(self, s):
        """Parse DD/MM/YYYY or YYYY-MM-DD."""
        if not s or str(s).strip().lower() in ('', 'nan'):
            return None
        s = str(s).strip()
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except ValueError:
            try:
                return datetime.strptime(s, "%Y-%m-%d").date()
            except ValueError:
                return None

    def _normalize_symbol(self, ticker_raw):
        """700 -> 0700.HK, 9988 -> 9988.HK, AAPL -> AAPL."""
        if not ticker_raw:
            return None
        raw = str(ticker_raw).strip().upper()
        if not raw:
            return None
        if str(ticker_raw).replace('.', '').isdigit():
            symbol_int = int(float(ticker_raw))
            return f"{symbol_int:04d}.HK"
        return raw

    def post(self, request):
        user = request.user
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file uploaded"}, status=400)

        try:
            decoded_file = file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            rows = list(reader)
        except Exception as e:
            return Response({"error": f"Failed to read CSV file: {str(e)}"}, status=400)

        # 偵測格式：有 Ticker 欄位則用「一行來回」格式
        if not rows:
            return Response({"message": "Successfully imported 0 transactions", "count": 0}, status=status.HTTP_200_OK)

        first_row = rows[0]
        has_ticker_format = 'Ticker' in first_row and ('買入價' in first_row or '買入時間' in first_row)

        count_created = 0
        errors = []

        if has_ticker_format:
            # 格式：Ticker, 股數, 買入價, 賣出價, 買入時間, 賣出時間（一行拆成 BUY + SELL）
            for row_num, row in enumerate(rows, start=2):
                try:
                    ticker_raw = row.get('Ticker')
                    if ticker_raw is None or str(ticker_raw).strip() == '':
                        continue

                    symbol = self._normalize_symbol(ticker_raw)
                    if not symbol:
                        continue

                    currency = 'HKD' if '.HK' in symbol else 'USD'
                    asset, _ = Asset.objects.get_or_create(symbol=symbol, defaults={'currency': currency})

                    try:
                        quantity = float(row.get('股數', 0) or 0)
                        buy_price = float(row.get('買入價', 0) or 0)
                        sell_price = float(row.get('賣出價', 0) or 0)
                    except (ValueError, TypeError):
                        errors.append(f"Row {row_num}: Invalid 股數/買入價/賣出價")
                        continue

                    buy_date = self._parse_date(row.get('買入時間', ''))
                    sell_date = self._parse_date(row.get('賣出時間', ''))

                    if buy_date and buy_price > 0:
                        Transaction.objects.create(
                            user=user,
                            asset=asset,
                            action='BUY',
                            date=buy_date,
                            price=Decimal(str(buy_price)),
                            quantity=Decimal(str(quantity)),
                            fees=Decimal('0'),
                        )
                        count_created += 1
                    if sell_date and sell_price > 0:
                        Transaction.objects.create(
                            user=user,
                            asset=asset,
                            action='SELL',
                            date=sell_date,
                            price=Decimal(str(sell_price)),
                            quantity=Decimal(str(quantity)),
                            fees=Decimal('0'),
                        )
                        count_created += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
        else:
            # 舊格式：symbol, action, date, price, quantity, fees
            for row_num, row in enumerate(rows, start=2):
                try:
                    symbol = (row.get('symbol') or '').strip().upper()
                    if not symbol:
                        continue
                    from .services import validate_symbol_with_yfinance, add_stock_to_cache
                    try:
                        is_valid, symbol_normalized, name, currency, _ = validate_symbol_with_yfinance(symbol)
                        if is_valid:
                            add_stock_to_cache(symbol_normalized, name, currency)
                            symbol = symbol_normalized
                    except Exception:
                        pass
                    asset, _ = Asset.objects.get_or_create(symbol=symbol)
                    action = (row.get('action') or 'BUY').strip().upper()
                    if action not in ('BUY', 'SELL', 'DIVIDEND'):
                        action = 'BUY'
                    date_str = row.get('date') or ''
                    dt = self._parse_date(date_str) if date_str else timezone.now().date()
                    price = Decimal(row.get('price') or 0)
                    quantity = Decimal(row.get('quantity') or 0)
                    fees = Decimal(row.get('fees') or 0)
                    Transaction.objects.create(
                        user=user,
                        asset=asset,
                        action=action,
                        date=dt,
                        price=price,
                        quantity=quantity,
                        fees=fees,
                    )
                    count_created += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")

        response_data = {
            "message": f"Successfully imported {count_created} transactions",
            "count": count_created,
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
    優先從 AccountBalance cache 讀取，如果不存在則 fallback 到動態計算
    權限：需要登入，只返回當前用戶的現金餘額
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # 嘗試從 cache 讀取
        try:
            balance = AccountBalance.objects.filter(user=user).first()
            if balance:
                # 返回 cache 中的數據
                return Response({
                    'available_cash': float(balance.available_cash),  # 向後兼容
                    'cash_usd': float(balance.cash_usd),
                    'cash_hkd': float(balance.cash_hkd),
                    'total_in_base': float(balance.total_in_base),
                    'last_updated': balance.last_updated.isoformat() if balance.last_updated else None
                })
        except Exception as e:
            # 如果讀取 cache 失敗，fallback 到動態計算
            pass
        
        # Fallback: 動態計算
        cash_data = calculate_current_cash(user, base_currency='USD')
        return Response({
            'available_cash': float(cash_data['total_in_base']),  # 向後兼容
            'cash_usd': float(cash_data['USD']),
            'cash_hkd': float(cash_data['HKD']),
            'total_in_base': float(cash_data['total_in_base']),
            'last_updated': None
        })


class RecalculateBalanceView(APIView):
    """
    強制重新計算並更新用戶的現金餘額 cache
    權限：需要登入，只處理當前用戶的餘額
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        try:
            result = recalculate_account_balance(user)
            return Response({
                'message': 'Balance recalculated successfully',
                'balance': result
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Failed to recalculate balance: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        date_range = request.query_params.get('date_range', '7d')  # 7d, 30d, 90d, all, custom
        start_date_param = request.query_params.get('start_date', None)  # YYYY-MM-DD
        end_date_param = request.query_params.get('end_date', None)  # YYYY-MM-DD
        symbol = request.query_params.get('symbol', None)

        # 自訂日期範圍：若有 start_date 與 end_date 則優先使用
        start_date = None
        end_date = None
        if start_date_param and end_date_param:
            try:
                start_date = datetime.strptime(start_date_param, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_param, "%Y-%m-%d").date()
                if start_date > end_date:
                    start_date, end_date = end_date, start_date
            except ValueError:
                pass
        if start_date is None or end_date is None:
            # 計算日期範圍（默認最近7天）
            today = timezone.now().date()
            if date_range == '7d':
                start_date = today - timedelta(days=7)
                end_date = today
            elif date_range == '30d':
                start_date = today - timedelta(days=30)
                end_date = today
            elif date_range == '90d':
                start_date = today - timedelta(days=90)
                end_date = today
            else:  # 'all' or unknown
                start_date = None
                end_date = None

        # 獲取交易記錄
        transactions = Transaction.objects.filter(
            user=user
        ).select_related('asset')
        
        # 獲取現金流記錄
        cashflows = CashFlow.objects.filter(
            user=user
        )
        
        # 應用日期過濾
        if start_date is not None:
            transactions = transactions.filter(date__gte=start_date)
            cashflows = cashflows.filter(date__gte=start_date)
        if end_date is not None:
            transactions = transactions.filter(date__lte=end_date)
            cashflows = cashflows.filter(date__lte=end_date)
        
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
        
        # 排序並評估查詢（避免在序列化時再次查詢）
        transactions = list(transactions.order_by('-date', '-created_at'))
        cashflows = list(cashflows.order_by('-date', '-created_at'))
        
        # 合併兩種記錄
        all_records = transactions + cashflows
        
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

class PortfolioHistoryView(APIView):
    """
    獲取投資組合歷史數據
    權限：需要登入，只返回當前用戶的數據
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/portfolio-history/?period=1y&interval=1d
        返回投資組合歷史價值數據
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        """
        user = request.user
        period = request.query_params.get('period', '1y')
        interval = request.query_params.get('interval', '1d')
        
        # 獲取匯率
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        
        # 獲取當前用戶有交易的所有資產（避免 N+1 查詢）
        user_transactions_prefetch = Prefetch(
            'transactions',
            queryset=Transaction.objects.filter(user=user).order_by('date', 'created_at'),
            to_attr='user_transactions'
        )
        user_assets = Asset.objects.filter(
            transactions__user=user
        ).distinct().prefetch_related(user_transactions_prefetch)
        
        # 獲取所有交易記錄，按日期排序（評估查詢以避免重複查詢）
        all_transactions = list(Transaction.objects.filter(
            user=user
        ).select_related('asset').order_by('date'))
        
        if not all_transactions:
            return Response({
                'dates': [],
                'portfolio_values': [],
                'cash_values': []
            })
        
        # 獲取最早和最新的交易日期
        first_transaction = all_transactions[0] if all_transactions else None
        last_transaction = all_transactions[-1] if all_transactions else None
        
        # 獲取所有涉及的股票代號
        symbols = list(set([asset.symbol for asset in user_assets]))
        
        if not symbols:
            return Response({
                'dates': [],
                'portfolio_values': [],
                'cash_values': []
            })
        
        # 使用 yfinance 獲取歷史價格
        historical_data = {}
        errors = []
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period, interval=interval)
                if not hist.empty:
                    historical_data[symbol] = hist['Close'].to_dict()
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                historical_data[symbol] = {}
        
        # 計算每日的投資組合價值
        dates = []
        portfolio_values = []
        cash_values = []
        
        # 獲取歷史日期範圍（從 yfinance 數據中）
        all_dates = set()
        for symbol_data in historical_data.values():
            all_dates.update(symbol_data.keys())
        
        if not all_dates:
            return Response({
                'dates': [],
                'portfolio_values': [],
                'cash_values': [],
                'errors': errors
            })
        
        sorted_dates = sorted(all_dates)
        
        # 計算每日的持倉和現金
        for date in sorted_dates:
            # 計算該日期之前的交易，使用 FIFO 邏輯計算持倉
            transactions_before_date = all_transactions.filter(date__lte=date)
            
            # 簡化計算：使用當前持倉數量，但用歷史價格計算市值
            # 這是一個近似值，因為實際持倉數量會隨時間變化
            daily_portfolio_value = Decimal('0.00')
            
            for asset in user_assets:
                # 計算該日期時的持倉（簡化：使用當前持倉）
                # 實際應該根據該日期前的交易計算持倉
                # 使用 prefetched transactions 以避免 N+1 查詢
                prefetched_txns = getattr(asset, 'user_transactions', None)
                stats = calculate_position(asset, user, usd_to_hkd_rate, prefetched_transactions=prefetched_txns)
                quantity = stats.get('quantity', 0)
                
                if quantity != 0 and asset.symbol in historical_data:
                    price_data = historical_data[asset.symbol]
                    # 找到最接近該日期的價格
                    closest_date = None
                    min_diff = None
                    for hist_date in price_data.keys():
                        if hist_date <= date:
                            diff = (date - hist_date).days
                            if min_diff is None or diff < min_diff:
                                min_diff = diff
                                closest_date = hist_date
                    
                    if closest_date and closest_date in price_data:
                        price = Decimal(str(price_data[closest_date]))
                        daily_portfolio_value += price * Decimal(str(abs(quantity)))
            
            # 計算該日期的現金餘額（簡化：使用當前現金）
            # 實際應該根據該日期前的現金流計算
            cash_data = calculate_current_cash(user, base_currency='USD')
            daily_cash = cash_data['total_in_base']
            
            dates.append(date.strftime('%Y-%m-%d'))
            portfolio_values.append(float(daily_portfolio_value))
            cash_values.append(float(daily_cash))
        
        return Response({
            'dates': dates,
            'portfolio_values': portfolio_values,
            'cash_values': cash_values,
            'total_values': [p + c for p, c in zip(portfolio_values, cash_values)],
            'errors': errors if errors else None
        })

class StockHistoryView(APIView):
    """
    獲取單個股票的歷史價格數據
    權限：需要登入
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/stock-history/?symbol=AAPL&period=1y&interval=1d
        返回單個股票的歷史價格數據
        """
        symbol = request.query_params.get('symbol', '')
        period = request.query_params.get('period', '1y')
        interval = request.query_params.get('interval', '1d')
        
        if not symbol:
            return Response(
                {"error": "Symbol parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return Response({
                    'symbol': symbol,
                    'dates': [],
                    'prices': []
                })
            
            # 轉換為列表格式
            dates = [date.strftime('%Y-%m-%d') for date in hist.index]
            prices = [float(price) for price in hist['Close'].values]
            
            return Response({
                'symbol': symbol,
                'dates': dates,
                'prices': prices
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch history for {symbol}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MonthlyTrackingView(APIView):
    """
    獲取月份追蹤資料
    權限：需要登入，只返回當前用戶的數據
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/monthly-tracking/?year=2025
        返回指定年份的每月交易統計數據
        """
        user = request.user
        
        # 獲取年份參數，預設為當前年份
        try:
            year = int(request.query_params.get('year', timezone.now().year))
        except (ValueError, TypeError):
            year = timezone.now().year
        
        # 計算月度追蹤數據
        try:
            result = calculate_monthly_tracking(user, year)
            
            # 轉換為可序列化的格式
            months_data = []
            for month in result['months']:
                months_data.append({
                    'month': month['month'],
                    'month_name': month['month_name'],
                    'avg_profit': float(month['avg_profit']),
                    'avg_profit_percent': float(month['avg_profit_percent']),
                    'avg_loss': float(month['avg_loss']),
                    'avg_loss_percent': float(month['avg_loss_percent']),
                    'win_rate': float(month['win_rate']),
                    'total_trades': month['total_trades'],
                    'max_profit': float(month['max_profit']),
                    'max_profit_percent': float(month['max_profit_percent']),
                    'max_loss': float(month['max_loss']),
                    'max_loss_percent': float(month['max_loss_percent']),
                    'avg_holding_days_success': float(month['avg_holding_days_success']) if month['avg_holding_days_success'] is not None else None,
                    'avg_holding_days_fail': float(month['avg_holding_days_fail']) if month['avg_holding_days_fail'] is not None else None,
                    'profit': float(month['profit'])
                })
            
            return Response({
                'year': result['year'],
                'months': months_data,
                'summary': {
                    'starting_capital': float(result['summary']['starting_capital']),
                    'total_profit': float(result['summary']['total_profit']),
                    'total_profit_percent': float(result['summary']['total_profit_percent']),
                    'unrealized_profit': float(result['summary'].get('unrealized_profit', 0.0)),
                    'unrealized_profit_percent': float(result['summary'].get('unrealized_profit_percent', 0.0))
                }
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to calculate monthly tracking: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class MonthlyTrackingYearsView(APIView):
    """
    獲取用戶有交易或現金流記錄的年份列表
    權限：需要登入，只返回當前用戶的數據
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        GET /api/monthly-tracking-years/
        返回用戶有交易或現金流記錄的年份列表（降序排列）
        """
        user = request.user
        
        try:
            # 獲取所有有交易的年份
            transaction_years = Transaction.objects.filter(
                user=user
            ).values_list('date__year', flat=True).distinct()
            
            # 獲取所有有現金流的年份
            cashflow_years = CashFlow.objects.filter(
                user=user
            ).values_list('date__year', flat=True).distinct()
            
            # 合併並去重，然後排序（降序）
            all_years = sorted(set(list(transaction_years) + list(cashflow_years)), reverse=True)
            
            return Response({
                'years': all_years
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to fetch available years: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DailySnapshotView(APIView):
    """
    獲取每日投資組合快照
    用於前端顯示「今日變動」的基準，以及未來做歷史數據分析
    
    GET /api/daily-snapshot/?date=YYYY-MM-DD
    - date: 快照日期，預設為今日
    - 返回該日期的 snapshot，若不存在則返回 null
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        date_str = request.query_params.get('date', 'today')
        
        # 解析日期
        if date_str == 'today':
            target_date = timezone.now().date()
        else:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD or 'today'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 查找快照
        try:
            snapshot = DailySnapshot.objects.get(user=user, date=target_date)
            return Response({
                'snapshot': {
                    'date': snapshot.date.strftime('%Y-%m-%d'),
                    'net_liquidity': float(snapshot.net_liquidity),
                    'current_cash': float(snapshot.current_cash),
                    'cash_usd': float(snapshot.cash_usd),
                    'cash_hkd': float(snapshot.cash_hkd),
                    'total_market_value': float(snapshot.total_market_value),
                    'total_invested': float(snapshot.total_invested),
                    'net_profit': float(snapshot.net_profit),
                    'roi_percentage': float(snapshot.roi_percentage),
                    'exchange_rate': float(snapshot.exchange_rate),
                    'positions': snapshot.positions
                }
            })
        except DailySnapshot.DoesNotExist:
            return Response({
                'snapshot': None,
                'message': f'No snapshot found for {target_date}'
            })


class DailySnapshotHistoryView(APIView):
    """
    獲取歷史快照列表
    用於未來做歷史走勢圖、回報率分析等
    
    GET /api/daily-snapshot/history/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=30
    - start_date: 開始日期（選填）
    - end_date: 結束日期（選填）
    - limit: 限制返回數量（預設 30 天）
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = int(request.query_params.get('limit', 30))
        
        # 查詢快照
        snapshots = DailySnapshot.objects.filter(user=user)
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                snapshots = snapshots.filter(date__gte=start)
            except ValueError:
                return Response(
                    {"error": "Invalid start_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                snapshots = snapshots.filter(date__lte=end)
            except ValueError:
                return Response(
                    {"error": "Invalid end_date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 限制數量並排序
        snapshots = snapshots.order_by('-date')[:limit]
        
        # 序列化
        data = [{
            'date': snapshot.date.strftime('%Y-%m-%d'),
            'net_liquidity': float(snapshot.net_liquidity),
            'current_cash': float(snapshot.current_cash),
            'total_market_value': float(snapshot.total_market_value),
            'total_invested': float(snapshot.total_invested),
            'net_profit': float(snapshot.net_profit),
            'roi_percentage': float(snapshot.roi_percentage),
        } for snapshot in snapshots]
        
        return Response({
            'snapshots': data,
            'count': len(data)
        })