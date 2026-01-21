# backend/portfolio/services.py
import json, os, time
import yfinance as yf

from datetime import datetime, timedelta
from decimal import Decimal
from django.conf import settings
from django.db import models
from pathlib import Path

from .models import Transaction, CashFlow, AccountBalance, Asset

# 匯率緩存（模塊級變量）
_exchange_rate_cache = {
    'rate': None,
    'timestamp': None,
    'cache_duration': 6400  # 緩存 2 小時（6400 秒）
}

def get_usd_to_hkd_rate():
    """
    獲取 USD 到 HKD 的匯率（帶緩存）
    使用 yfinance 獲取 HKD=X 匯率，如果失敗則使用固定匯率 7.8 作為 fallback
    緩存時間：1 小時，避免頻繁請求導致 rate limiting
    """
    global _exchange_rate_cache
    
    current_time = time.time()
    
    # 檢查緩存是否有效
    if (_exchange_rate_cache['rate'] is not None and 
        _exchange_rate_cache['timestamp'] is not None and
        (current_time - _exchange_rate_cache['timestamp']) < _exchange_rate_cache['cache_duration']):
        return _exchange_rate_cache['rate']
    
    # 緩存無效或不存在，從 API 獲取
    try:
        ticker = yf.Ticker("HKD=X")
        info = ticker.info
        rate = info.get('regularMarketPrice') or info.get('currentPrice')
        if rate:
            rate_decimal = Decimal(str(rate))
            # 更新緩存
            _exchange_rate_cache['rate'] = rate_decimal
            _exchange_rate_cache['timestamp'] = current_time
            return rate_decimal
    except Exception as e:
        print(f"無法獲取匯率: {e}")
        # 如果 API 請求失敗，但緩存中有舊值，使用舊值
        if _exchange_rate_cache['rate'] is not None:
            print(f"使用緩存的匯率: {_exchange_rate_cache['rate']}")
            return _exchange_rate_cache['rate']
    
    # Fallback: 使用固定匯率 7.8
    fallback_rate = Decimal('7.8')
    _exchange_rate_cache['rate'] = fallback_rate
    _exchange_rate_cache['timestamp'] = current_time
    return fallback_rate

def get_total_invested_capital(user):
    """
    計算總投入本金：所有 CashFlow 中 DEPOSIT 減去 WITHDRAW 的總和（統一轉換為 USD）
    """
    usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    total_deposits_usd = Decimal('0.00')
    total_withdraws_usd = Decimal('0.00')
    
    # 計算所有存款（轉換為 USD）
    # 評估查詢以避免重複查詢
    deposits = list(CashFlow.objects.filter(user=user, type='DEPOSIT'))
    for deposit in deposits:
        if deposit.currency == 'USD':
            total_deposits_usd += deposit.amount
        elif deposit.currency == 'HKD':
            total_deposits_usd += deposit.amount / usd_to_hkd_rate
    
    # 計算所有提款（轉換為 USD）
    withdraws = CashFlow.objects.filter(user=user, type='WITHDRAW')
    for withdraw in withdraws:
        if withdraw.currency == 'USD':
            total_withdraws_usd += withdraw.amount
        elif withdraw.currency == 'HKD':
            total_withdraws_usd += withdraw.amount / usd_to_hkd_rate
    
    return total_deposits_usd - total_withdraws_usd

def calculate_current_cash(user, base_currency='USD'):
    """
    計算目前的可用現金（支持多幣種）：
    現金流 (存入 - 提取) + 賣出收入 - 買入支出 + 股息收入
    
    返回: {
        'USD': Decimal,
        'HKD': Decimal,
        'total_in_base': Decimal  # 以基準幣種計算的總額
    }
    """
    usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    # 初始化各幣種現金
    cash_usd = Decimal('0.00')
    cash_hkd = Decimal('0.00')
    
    # 1. 計算現金流（按幣種分開計算）
    # 評估查詢以避免重複查詢
    cashflows = list(CashFlow.objects.filter(user=user))
    for cf in cashflows:
        amount = cf.amount
        if cf.type == 'DEPOSIT':
            if cf.currency == 'USD':
                cash_usd += amount
            elif cf.currency == 'HKD':
                cash_hkd += amount
        elif cf.type == 'WITHDRAW':
            if cf.currency == 'USD':
                cash_usd -= amount
            elif cf.currency == 'HKD':
                cash_hkd -= amount
    
    # 2. 計算交易影響（按幣種分開計算）
    transactions = Transaction.objects.filter(user=user).select_related('asset')
    for txn in transactions:
        if not txn.asset:
            continue
            
        txn_currency = txn.currency or txn.asset.currency or 'USD'
        amount = Decimal('0.00')
        
        if txn.action == 'BUY':
            amount = -(txn.price * txn.quantity + txn.fees)
        elif txn.action == 'SELL':
            amount = txn.price * txn.quantity - txn.fees
        elif txn.action == 'DIVIDEND':
            amount = txn.price * txn.quantity
        
        if txn_currency == 'USD':
            cash_usd += amount
        elif txn_currency == 'HKD':
            cash_hkd += amount
    
    # 3. 計算基準幣種總額
    if base_currency == 'USD':
        total_in_base = cash_usd + (cash_hkd / usd_to_hkd_rate)
    else:  # HKD
        total_in_base = (cash_usd * usd_to_hkd_rate) + cash_hkd
    
    return {
        'USD': cash_usd,
        'HKD': cash_hkd,
        'total_in_base': total_in_base
    }

def update_account_balance_cache(user):
    """
    更新用戶的現金餘額 cache
    調用 calculate_current_cash() 獲取最新餘額，然後更新 AccountBalance 模型
    使用 update_or_create 確保原子性操作，避免 race condition
    """
    from django.db import transaction as db_transaction
    
    try:
        # 計算最新餘額（Single Source of Truth）
        cash_data = calculate_current_cash(user, base_currency='USD')
        
        # 使用 database transaction 確保原子性
        with db_transaction.atomic():
            # 使用 select_for_update 避免併發問題
            balance, created = AccountBalance.objects.select_for_update().get_or_create(
                user=user,
                defaults={
                    'cash_usd': cash_data['USD'],
                    'cash_hkd': cash_data['HKD'],
                    'total_in_base': cash_data['total_in_base'],
                    'available_cash': cash_data['total_in_base'],  # 向後兼容
                }
            )
            
            if not created:
                # 更新現有記錄
                balance.cash_usd = cash_data['USD']
                balance.cash_hkd = cash_data['HKD']
                balance.total_in_base = cash_data['total_in_base']
                balance.available_cash = cash_data['total_in_base']  # 向後兼容
                balance.save(update_fields=['cash_usd', 'cash_hkd', 'total_in_base', 'available_cash', 'last_updated'])
        
        return balance
    except Exception as e:
        # 記錄錯誤但不拋出異常，避免影響主業務流程
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to update account balance cache for user {user.id}: {e}", exc_info=True)
        raise


def recalculate_account_balance(user):
    """
    強制重新計算並更新用戶的現金餘額 cache
    用於 fallback 和數據修復場景
    返回更新後的餘額數據
    """
    try:
        balance = update_account_balance_cache(user)
        return {
            'USD': float(balance.cash_usd),
            'HKD': float(balance.cash_hkd),
            'total_in_base': float(balance.total_in_base),
            'available_cash': float(balance.available_cash),  # 向後兼容
            'last_updated': balance.last_updated.isoformat() if balance.last_updated else None
        }
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to recalculate account balance for user {user.id}: {e}", exc_info=True)
        # 如果更新失敗，返回動態計算的結果
        cash_data = calculate_current_cash(user, base_currency='USD')
        return {
            'USD': float(cash_data['USD']),
            'HKD': float(cash_data['HKD']),
            'total_in_base': float(cash_data['total_in_base']),
            'available_cash': float(cash_data['total_in_base']),  # 向後兼容
            'last_updated': None
        }

def detect_asset_currency(symbol):
    """
    根據股票代號判斷幣種
    規則：
    - 4 位數字或以 .HK 結尾的視為 HKD
    - 其他視為 USD
    """
    symbol_upper = symbol.upper().strip()
    if symbol_upper.endswith('.HK') or (symbol_upper.isdigit() and len(symbol_upper) == 4):
        return 'HKD'
    return 'USD'

def normalize_symbol(symbol):
    """
    標準化股票代號
    - 港股：0700 -> 0700.HK, 700 -> 0700.HK
    - 美股：保持原樣 (如 AAPL, TSLA)
    """
    symbol = symbol.strip().upper()
    
    # 如果已經是 .HK 結尾，直接返回
    if symbol.endswith('.HK'):
        return symbol
    
    # 判斷是否為港股（純數字，1-4位）
    if symbol.isdigit():
        # 補零至4位並加 .HK
        symbol_int = int(symbol)
        return f"{symbol_int:04d}.HK"
    
    # 美股，保持原樣
    return symbol

def get_stock_list_cache_path():
    """
    獲取股票列表緩存文件路徑
    """
    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)
    return media_root / 'stock_list.json'

def load_stock_list_cache():
    """
    從緩存文件加載股票列表
    返回格式: {
        'stocks': [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'currency': 'USD'}, ...],
        'last_updated': '2024-01-01T00:00:00'
    }
    """
    cache_path = get_stock_list_cache_path()
    
    if not cache_path.exists():
        return {'stocks': [], 'last_updated': None}
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except (json.JSONDecodeError, IOError) as e:
        print(f"無法讀取緩存文件: {e}")
        return {'stocks': [], 'last_updated': None}

def save_stock_list_cache(stocks):
    """
    保存股票列表到緩存文件
    stocks: [{'symbol': 'AAPL', 'name': 'Apple Inc.', 'currency': 'USD'}, ...]
    """
    cache_path = get_stock_list_cache_path()
    
    data = {
        'stocks': stocks,
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        print(f"無法寫入緩存文件: {e}")
        return False

def is_cache_valid(cache_data, max_age_days=7):
    """
    檢查緩存是否有效
    max_age_days: 緩存最大有效期（天數）
    """
    if not cache_data.get('last_updated'):
        return False
    
    try:
        last_updated = datetime.fromisoformat(cache_data['last_updated'])
        age = datetime.now() - last_updated
        return age < timedelta(days=max_age_days)
    except (ValueError, TypeError):
        return False

def validate_symbol_with_yfinance(symbol):
    """
    使用 yfinance 驗證股票代號是否有效
    返回: (is_valid, symbol_normalized, name, currency, error_message)
    """
    try:
        # 標準化股票代號
        symbol_normalized = normalize_symbol(symbol)
        
        # 使用 yfinance 獲取股票信息
        ticker = yf.Ticker(symbol_normalized)
        
        # 先嘗試獲取歷史數據（更可靠的方法）
        try:
            hist = ticker.history(period='5d')
            if hist.empty:
                return False, symbol_normalized, None, None, "股票代號無效或已下市"
        except Exception as hist_error:
            # 如果歷史數據獲取失敗，嘗試使用 info
            pass
        
        # 獲取股票信息
        try:
            info = ticker.info
        except Exception:
            info = {}
        
        # 檢查 info 是否為空或包含錯誤
        if not info or len(info) == 0:
            return False, symbol_normalized, None, None, "無法獲取股票信息"
        
        # 檢查是否有錯誤信息
        if 'error' in info or 'quoteSummary' in info:
            quote_summary = info.get('quoteSummary', {})
            if quote_summary:
                error_info = quote_summary.get('error')
                if error_info:
                    error_desc = error_info.get('description', '股票代號無效')
                    return False, symbol_normalized, None, None, error_desc
        
        # 檢查是否有價格信息（多種可能的字段）
        has_price = (
            info.get('regularMarketPrice') is not None or
            info.get('currentPrice') is not None or
            info.get('previousClose') is not None or
            info.get('regularMarketPreviousClose') is not None
        )
        
        if not has_price:
            # 如果沒有價格信息，再次檢查歷史數據
            try:
                hist = ticker.history(period='1d')
                if hist.empty:
                    return False, symbol_normalized, None, None, "股票代號無效或已下市"
            except Exception:
                return False, symbol_normalized, None, None, "無法獲取股票價格信息"
        
        # 獲取股票名稱
        name = (
            info.get('longName') or 
            info.get('shortName') or 
            info.get('name') or
            info.get('symbol', symbol_normalized)
        )
        
        # 如果名稱還是空的，使用 symbol
        if not name or name == symbol_normalized:
            name = symbol_normalized
        
        # 判斷幣種
        currency = detect_asset_currency(symbol_normalized)
        
        return True, symbol_normalized, name, currency, None
        
    except Exception as e:
        error_msg = str(e)
        # 標準化股票代號以便返回
        symbol_normalized = normalize_symbol(symbol)
        
        # 提供更友好的錯誤訊息
        if '404' in error_msg or 'Not Found' in error_msg or 'delisted' in error_msg.lower():
            return False, symbol_normalized, None, None, "股票代號無效或已下市"
        elif 'quote' in error_msg.lower() or 'symbol' in error_msg.lower():
            return False, symbol_normalized, None, None, "無法找到該股票代號"
        else:
            return False, symbol_normalized, None, None, f"驗證失敗: {error_msg}"

def search_stocks_in_cache(query):
    """
    在緩存中搜索股票
    query: 搜索關鍵字（股票代號或名稱）
    返回匹配的股票列表
    """
    cache_data = load_stock_list_cache()
    stocks = cache_data.get('stocks', [])
    
    if not query:
        return stocks[:50]  # 返回前50個
    
    query_upper = query.upper().strip()
    matches = []
    
    for stock in stocks:
        symbol = stock.get('symbol', '').upper()
        name = stock.get('name', '').upper()
        
        # 匹配股票代號或名稱
        if query_upper in symbol or query_upper in name:
            matches.append(stock)
    
    return matches[:20]  # 返回前20個匹配結果

def add_stock_to_cache(symbol, name=None, currency=None):
    """
    將驗證過的股票添加到緩存
    """
    cache_data = load_stock_list_cache()
    stocks = cache_data.get('stocks', [])
    
    symbol_normalized = normalize_symbol(symbol)
    
    # 檢查是否已存在
    existing = next((s for s in stocks if s.get('symbol') == symbol_normalized), None)
    if existing:
        # 更新現有記錄
        if name:
            existing['name'] = name
        if currency:
            existing['currency'] = currency
        existing['last_validated'] = datetime.now().isoformat()
    else:
        # 添加新記錄
        if not name:
            name = symbol_normalized
        if not currency:
            currency = detect_asset_currency(symbol_normalized)
        
        stocks.append({
            'symbol': symbol_normalized,
            'name': name,
            'currency': currency,
            'last_validated': datetime.now().isoformat()
        })
    
    # 保存緩存
    save_stock_list_cache(stocks)

def convert_to_usd(amount, from_currency, usd_to_hkd_rate):
    """
    將金額轉換為 USD
    """
    if from_currency == 'USD':
        return amount
    elif from_currency == 'HKD':
        # HKD 轉 USD: 除以匯率
        return amount / usd_to_hkd_rate
    return amount

def convert_from_usd(amount, to_currency, usd_to_hkd_rate):
    """
    將 USD 金額轉換為目標幣種
    """
    if to_currency == 'USD':
        return amount
    elif to_currency == 'HKD':
        # USD 轉 HKD: 乘以匯率
        return amount * usd_to_hkd_rate
    return amount

def calculate_position(asset, user, usd_to_hkd_rate=None, prefetched_transactions=None):
    """
    使用 FIFO (先進先出) 邏輯計算某檔股票的：
    1. 當前持倉數量（支援負數，表示賣空）
    2. 平均成本 (剩餘持倉的加權平均)
    3. 已實現損益 (Realized P&L)
    
    所有計算結果統一轉換為 USD
    支援賣空：允許負數持倉
    
    Args:
        asset: Asset 對象
        user: User 對象
        usd_to_hkd_rate: USD 到 HKD 的匯率（可選）
        prefetched_transactions: 預先獲取的交易列表（可選，用於避免 N+1 查詢）
    """
    if usd_to_hkd_rate is None:
        usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    # 判斷資產幣種
    asset_currency = asset.currency or detect_asset_currency(asset.symbol)
    
    # 拿出這隻股票的所有交易，按日期排序 (最舊的在前面 -> FIFO)
    # 優先使用 prefetched_transactions，避免 N+1 查詢
    if prefetched_transactions is not None:
        transactions = prefetched_transactions
    elif hasattr(asset, 'user_transactions'):
        # 使用 Prefetch 的 to_attr 結果
        transactions = asset.user_transactions
    else:
        # Fallback: 如果沒有 prefetch，才進行查詢（會導致 N+1）
        transactions = asset.transactions.filter(user=user).order_by('date', 'created_at')
    
    inventory = []  # 倉庫：存這檔股票目前的多頭持倉 [(price, quantity), ...]
    short_inventory = []  # 賣空倉庫：存這檔股票目前的空頭持倉 [(price, quantity), ...]
    realized_pl = Decimal('0.00') # 已實現損益（USD）
    total_dividends = Decimal('0.00') # 股息（USD）

    for t in transactions:
        if t.action == 'BUY':
            # 買入：先嘗試平倉賣空，剩餘的再入庫
            qty_to_buy = t.quantity
            total_gain = Decimal('0.00')  # 累計獲利（平倉賣空）
            
            while qty_to_buy > 0 and short_inventory:
                # 有賣空倉位需要平倉
                batch = short_inventory[0]
                
                if batch['quantity'] > qty_to_buy:
                    # 這批賣空倉位夠平，且還有剩
                    # 賣空平倉獲利 = (賣空價格 - 買入價格) * 平倉數量
                    gain = (batch['price'] - t.price) * qty_to_buy
                    gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                    total_gain += gain_usd
                    
                    # 更新賣空倉位數量
                    batch['quantity'] -= qty_to_buy
                    qty_to_buy = 0
                    
                else:
                    # 這批賣空倉位不夠平，全部平掉
                    closed_qty = batch['quantity']
                    gain = (batch['price'] - t.price) * closed_qty
                    gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                    total_gain += gain_usd
                    
                    qty_to_buy -= closed_qty
                    short_inventory.pop(0)  # 這批賣空倉位平光了，移除
            
            # 如果還有剩餘，入庫（多頭持倉）
            if qty_to_buy > 0:
                inventory.append({
                    'price': t.price,
                    'quantity': qty_to_buy,
                    'date': t.date
                })
            
            # 扣除整筆買單的手續費並加上平倉獲利
            fees_usd = convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
            realized_pl += total_gain - fees_usd
            
        elif t.action == 'SELL':
            # 賣出：先從多頭倉庫拿貨 (FIFO)，如果沒有多頭持倉則開賣空倉位
            qty_to_sell = t.quantity
            total_gain = Decimal('0.00')  # 累計獲利
            
            while qty_to_sell > 0:
                if not inventory:
                    # 沒有多頭持倉了，開賣空倉位
                    short_inventory.append({
                        'price': t.price,
                        'quantity': qty_to_sell,
                        'date': t.date
                    })
                    # 賣空開倉：獲利 = 賣出價格 * 數量（因為是借來的股票，成本為 0）
                    remaining_gain = qty_to_sell * t.price
                    remaining_gain_usd = convert_to_usd(remaining_gain, asset_currency, usd_to_hkd_rate)
                    total_gain += remaining_gain_usd
                    qty_to_sell = 0
                    break

                # 拿出第一批多頭持倉 (FIFO)
                batch = inventory[0]
                
                if batch['quantity'] > qty_to_sell:
                    # 這批貨夠賣，且還有剩
                    # 獲利 = (賣價 - 成本價) * 賣出數量
                    gain = (t.price - batch['price']) * qty_to_sell
                    # 轉換為 USD
                    gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                    total_gain += gain_usd
                    
                    # 更新庫存數量
                    batch['quantity'] -= qty_to_sell
                    qty_to_sell = 0
                    
                else:
                    # 這批貨不夠賣，全部賣光，再拿下一批
                    sold_qty = batch['quantity']
                    gain = (t.price - batch['price']) * sold_qty
                    # 轉換為 USD
                    gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                    total_gain += gain_usd
                    
                    qty_to_sell -= sold_qty
                    inventory.pop(0) # 這批貨賣光了，移除
            
            # 扣除整筆賣單的手續費
            fees_usd = convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
            realized_pl += total_gain - fees_usd

        elif t.action == 'DIVIDEND':
            dividend_amount = t.total_amount
            dividend_usd = convert_to_usd(dividend_amount, asset_currency, usd_to_hkd_rate)
            total_dividends += dividend_usd

    # --- 計算結果 ---
    
    # 1. 剩餘持倉股數（多頭 - 空頭，可能為負數）
    long_quantity = sum(item['quantity'] for item in inventory)
    short_quantity = sum(item['quantity'] for item in short_inventory)
    current_quantity = long_quantity - short_quantity
    
    # 2. 多頭持倉的總成本（轉換為 USD）
    long_total_cost = sum(item['price'] * item['quantity'] for item in inventory)
    long_total_cost_usd = convert_to_usd(long_total_cost, asset_currency, usd_to_hkd_rate)
    
    # 3. 空頭持倉的總成本（賣空價格，轉換為 USD）
    short_total_cost = sum(item['price'] * item['quantity'] for item in short_inventory)
    short_total_cost_usd = convert_to_usd(short_total_cost, asset_currency, usd_to_hkd_rate)
    
    # 4. 平均成本 (Avg Cost) - USD
    avg_cost_usd = Decimal('0.00')
    if current_quantity > 0:
        # 多頭持倉：平均成本 = 總成本 / 數量
        avg_cost_usd = long_total_cost_usd / long_quantity
    elif current_quantity < 0:
        # 空頭持倉：平均成本 = 總賣空價格 / 數量（絕對值）
        avg_cost_usd = short_total_cost_usd / short_quantity

    # 5. 當前市值（轉換為 USD）
    # 多頭持倉市值為正，空頭持倉市值為負
    long_market_value = long_quantity * asset.current_price
    short_market_value = short_quantity * asset.current_price
    current_market_value = long_market_value - short_market_value  # 空頭市值為負
    current_market_value_usd = convert_to_usd(current_market_value, asset_currency, usd_to_hkd_rate)
    
    # 6. 未實現損益（USD）
    if current_quantity > 0:
        # 多頭持倉：未實現損益 = 市值 - 成本
        unrealized_pl_usd = current_market_value_usd - long_total_cost_usd
    elif current_quantity < 0:
        # 空頭持倉：未實現損益 = (平均成本 - 現價) * 絕對值(數量)
        # 因為市值已經是負數，所以公式是：市值 - (-成本) = 市值 + 成本
        # 但更直觀的是：(平均成本 - 現價) * 絕對值(數量)
        unrealized_pl_usd = (avg_cost_usd - convert_to_usd(asset.current_price, asset_currency, usd_to_hkd_rate)) * abs(current_quantity)
    else:
        unrealized_pl_usd = Decimal('0.00')

    # 7. 分別計算多頭和空頭市值（用於 Gross Position 計算）
    long_market_value_usd = convert_to_usd(long_market_value, asset_currency, usd_to_hkd_rate)
    short_market_value_usd = convert_to_usd(short_market_value, asset_currency, usd_to_hkd_rate)
    
    # 從緩存中獲取公司名稱
    cache_data = load_stock_list_cache()
    stocks = cache_data.get('stocks', [])
    cached_stock = next((s for s in stocks if s.get('symbol') == asset.symbol), None)
    company_name = cached_stock.get('name', '') if cached_stock else ''
    
    return {
        'symbol': asset.symbol,
        'name': company_name,  # 從緩存獲取公司名稱
        'currency': asset_currency,
        'quantity': current_quantity,  # 可能為負數
        'avg_cost': avg_cost_usd,  # USD
        'realized_pl': realized_pl,  # USD
        'total_dividends': total_dividends,  # USD
        'current_market_value': current_market_value_usd,  # USD（負數持倉時為負值）
        'unrealized_pl': unrealized_pl_usd,  # USD
        'long_market_value': long_market_value_usd,  # USD（多頭市值，正數）
        'short_market_value': abs(short_market_value_usd)  # USD（空頭市值絕對值，正數）
    }

def calculate_monthly_tracking(user, year):
    """
    計算指定年份的每月交易統計數據
    返回格式：
    {
        'year': int,
        'months': [
            {
                'month': int (1-12),
                'month_name': str (JAN-DEC),
                'avg_profit': Decimal,
                'avg_loss': Decimal,
                'win_rate': Decimal,
                'total_trades': int,
                'max_profit': Decimal,
                'max_loss': Decimal,
                'avg_holding_days_success': Decimal,
                'avg_holding_days_fail': Decimal,
                'profit': Decimal
            },
            ...
        ],
        'summary': {
            'starting_capital': Decimal,
            'total_profit': Decimal,
            'total_profit_percent': Decimal
        }
    }
    """
    from django.utils import timezone
    from collections import defaultdict
    
    usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    # 獲取該年份的所有交易，按日期排序
    start_date = timezone.datetime(year, 1, 1).date()
    end_date = timezone.datetime(year, 12, 31).date()
    
    # 評估查詢以避免重複查詢
    all_transactions = list(Transaction.objects.filter(
        user=user,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('asset').order_by('date', 'created_at'))
    
    # 計算起始資金（該年1月1日0:00時的 portfolio 資產總值 = 現金 + 持倉市值）
    
    # 1. 計算該年1月1日之前的現金餘額
    cash_usd = Decimal('0.00')
    cash_hkd = Decimal('0.00')
    
    # 現金流（該年1月1日之前）
    # 評估查詢以避免重複查詢
    cashflows_before_start = list(CashFlow.objects.filter(
        user=user,
        date__lt=start_date  # 使用 < 而不是 <=，確保是1月1日0:00之前
    ))
    for cf in cashflows_before_start:
        if cf.currency == 'USD':
            if cf.type == 'DEPOSIT':
                cash_usd += cf.amount
            else:  # WITHDRAW
                cash_usd -= cf.amount
        elif cf.currency == 'HKD':
            if cf.type == 'DEPOSIT':
                cash_hkd += cf.amount
            else:  # WITHDRAW
                cash_hkd -= cf.amount
    
    # 交易影響（該年1月1日之前）
    transactions_before_start = Transaction.objects.filter(
        user=user,
        date__lt=start_date
    ).select_related('asset')
    for txn in transactions_before_start:
        if not txn.asset:
            continue
        txn_currency = txn.currency or txn.asset.currency or 'USD'
        amount = Decimal('0.00')
        if txn.action == 'BUY':
            amount = -(txn.price * txn.quantity + txn.fees)
        elif txn.action == 'SELL':
            amount = txn.price * txn.quantity - txn.fees
        elif txn.action == 'DIVIDEND':
            amount = txn.price * txn.quantity
        
        if txn_currency == 'USD':
            cash_usd += amount
        elif txn_currency == 'HKD':
            cash_hkd += amount
    
    cash_before_start = cash_usd + (cash_hkd / usd_to_hkd_rate)
    
    # 2. 計算該年1月1日之前的持倉市值
    # 獲取所有有交易的資產（包括該年之前的交易），並 prefetch 該年之前的交易
    from django.db.models import Prefetch
    transactions_before_prefetch = Prefetch(
        'transactions',
        queryset=Transaction.objects.filter(
            user=user,
            date__lt=start_date
        ).order_by('date', 'created_at'),
        to_attr='transactions_before_start'
    )
    all_user_assets = Asset.objects.filter(
        transactions__user=user
    ).distinct().prefetch_related(transactions_before_prefetch)
    
    portfolio_value_before_start = Decimal('0.00')
    
    for asset in all_user_assets:
        # 計算該年1月1日之前的持倉（使用 FIFO）
        asset_currency = asset.currency or detect_asset_currency(asset.symbol)
        # 使用 prefetched transactions，避免 N+1 查詢
        asset_transactions_before = getattr(asset, 'transactions_before_start', [])
        
        inventory = []
        short_inventory = []
        
        for t in asset_transactions_before:
            if t.action == 'BUY':
                qty_to_buy = t.quantity
                # 先平倉賣空
                while qty_to_buy > 0 and short_inventory:
                    batch = short_inventory[0]
                    if batch['quantity'] > qty_to_buy:
                        batch['quantity'] -= qty_to_buy
                        qty_to_buy = 0
                    else:
                        qty_to_buy -= batch['quantity']
                        short_inventory.pop(0)
                # 剩餘的入庫
                if qty_to_buy > 0:
                    inventory.append({
                        'price': t.price,
                        'quantity': qty_to_buy,
                        'date': t.date
                    })
            elif t.action == 'SELL':
                qty_to_sell = t.quantity
                while qty_to_sell > 0:
                    if not inventory:
                        short_inventory.append({
                            'price': t.price,
                            'quantity': qty_to_sell,
                            'date': t.date
                        })
                        qty_to_sell = 0
                        break
                    batch = inventory[0]
                    if batch['quantity'] > qty_to_sell:
                        batch['quantity'] -= qty_to_sell
                        qty_to_sell = 0
                    else:
                        qty_to_sell -= batch['quantity']
                        inventory.pop(0)
        
        # 計算持倉市值（使用當前價格）
        long_quantity = sum(item['quantity'] for item in inventory)
        short_quantity = sum(item['quantity'] for item in short_inventory)
        net_quantity = long_quantity - short_quantity
        
        if net_quantity != 0:
            # 使用當前價格計算市值（如果沒有歷史價格數據）
            price = asset.current_price if asset.current_price > 0 else Decimal('0.00')
            market_value = net_quantity * price
            market_value_usd = convert_to_usd(market_value, asset_currency, usd_to_hkd_rate)
            portfolio_value_before_start += market_value_usd
    
    # 3. 起始資金 = 現金 + 持倉市值
    starting_capital = cash_before_start + portfolio_value_before_start
    
    # 按資產分組處理交易
    # 使用 prefetch 來優化查詢，避免 N+1
    year_transactions_prefetch = Prefetch(
        'transactions',
        queryset=Transaction.objects.filter(
            user=user,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('asset').order_by('date', 'created_at'),
        to_attr='year_transactions'
    )
    assets = Asset.objects.filter(
        transactions__user=user,
        transactions__date__gte=start_date,
        transactions__date__lte=end_date
    ).distinct().prefetch_related(year_transactions_prefetch)
    
    # 存儲每月的交易結果
    monthly_trades = defaultdict(list)  # {month: [{'profit': Decimal, 'holding_days': int, ...}, ...]}
    
    # 存儲每個資產處理完交易後的持倉狀態，用於計算未實現損益
    asset_inventories = {}  # {asset_id: {'inventory': [...], 'short_inventory': [...], 'currency': '...'}}
    
    for asset in assets:
        asset_currency = asset.currency or detect_asset_currency(asset.symbol)
        # 使用 prefetched transactions，避免 N+1 查詢
        asset_transactions = getattr(asset, 'year_transactions', [])
        
        inventory = []  # 多頭持倉 [(price, quantity, date), ...]
        short_inventory = []  # 空頭持倉 [(price, quantity, date), ...]
        
        for t in asset_transactions:
            if t.action == 'BUY':
                qty_to_buy = t.quantity
                total_gain = Decimal('0.00')
                
                # 先平倉賣空
                while qty_to_buy > 0 and short_inventory:
                    batch = short_inventory[0]
                    if batch['quantity'] > qty_to_buy:
                        gain = (batch['price'] - t.price) * qty_to_buy
                        gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                        total_gain += gain_usd
                        
                        # 記錄這筆平倉交易
                        holding_days = (t.date - batch['date']).days
                        monthly_trades[t.date.month].append({
                            'profit': gain_usd,
                            'holding_days': holding_days,
                            'fees': convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
                        })
                        
                        batch['quantity'] -= qty_to_buy
                        qty_to_buy = 0
                    else:
                        closed_qty = batch['quantity']
                        gain = (batch['price'] - t.price) * closed_qty
                        gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                        total_gain += gain_usd
                        
                        holding_days = (t.date - batch['date']).days
                        monthly_trades[t.date.month].append({
                            'profit': gain_usd,
                            'holding_days': holding_days,
                            'fees': convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
                        })
                        
                        qty_to_buy -= closed_qty
                        short_inventory.pop(0)
                
                # 剩餘的入庫
                if qty_to_buy > 0:
                    inventory.append({
                        'price': t.price,
                        'quantity': qty_to_buy,
                        'date': t.date
                    })
                
                # 扣除手續費
                fees_usd = convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
                if fees_usd > 0 and monthly_trades[t.date.month]:
                    monthly_trades[t.date.month][-1]['profit'] -= fees_usd
            
            elif t.action == 'SELL':
                qty_to_sell = t.quantity
                
                while qty_to_sell > 0:
                    if not inventory:
                        # 開賣空倉位
                        short_inventory.append({
                            'price': t.price,
                            'quantity': qty_to_sell,
                            'date': t.date
                        })
                        # 賣空開倉：獲利 = 賣出價格 * 數量（成本為0）
                        remaining_gain = qty_to_sell * t.price
                        remaining_gain_usd = convert_to_usd(remaining_gain, asset_currency, usd_to_hkd_rate)
                        
                        # 記錄賣空開倉（持有天數為0）
                        # 賣空開倉成本為0，所以百分比為無限大，設為特殊值或0
                        monthly_trades[t.date.month].append({
                            'profit': remaining_gain_usd,
                            'profit_percent': Decimal('0.00'),  # 賣空開倉時成本為0，無法計算百分比
                            'holding_days': 0,
                            'fees': Decimal('0.00')
                        })
                        
                        qty_to_sell = 0
                        break
                    
                    batch = inventory[0]
                    
                    if batch['quantity'] > qty_to_sell:
                        gain = (t.price - batch['price']) * qty_to_sell
                        gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                        holding_days = (t.date - batch['date']).days
                        cost_basis = batch['price'] * qty_to_sell
                        cost_basis_usd = convert_to_usd(cost_basis, asset_currency, usd_to_hkd_rate)
                        profit_percent = (gain_usd / cost_basis_usd * Decimal('100.00')) if cost_basis_usd > 0 else Decimal('0.00')
                        
                        monthly_trades[t.date.month].append({
                            'profit': gain_usd,
                            'profit_percent': profit_percent,
                            'holding_days': holding_days,
                            'fees': Decimal('0.00')
                        })
                        
                        batch['quantity'] -= qty_to_sell
                        qty_to_sell = 0
                    else:
                        sold_qty = batch['quantity']
                        gain = (t.price - batch['price']) * sold_qty
                        gain_usd = convert_to_usd(gain, asset_currency, usd_to_hkd_rate)
                        holding_days = (t.date - batch['date']).days
                        cost_basis = batch['price'] * sold_qty
                        cost_basis_usd = convert_to_usd(cost_basis, asset_currency, usd_to_hkd_rate)
                        profit_percent = (gain_usd / cost_basis_usd * Decimal('100.00')) if cost_basis_usd > 0 else Decimal('0.00')
                        
                        monthly_trades[t.date.month].append({
                            'profit': gain_usd,
                            'profit_percent': profit_percent,
                            'holding_days': holding_days,
                            'fees': Decimal('0.00')
                        })
                        
                        qty_to_sell -= sold_qty
                        inventory.pop(0)
                
                # 扣除賣出手續費
                fees_usd = convert_to_usd(t.fees, asset_currency, usd_to_hkd_rate)
                if fees_usd > 0 and monthly_trades[t.date.month]:
                    monthly_trades[t.date.month][-1]['profit'] -= fees_usd
        
        # 保存該資產處理完所有交易後的持倉狀態
        asset_inventories[asset.id] = {
            'inventory': inventory.copy(),
            'short_inventory': short_inventory.copy(),
            'currency': asset_currency
        }
    
    # 計算未實現損益（只在有未賣出持倉時才計算）
    from django.utils import timezone
    current_date = timezone.now().date()
    total_unrealized_profit = Decimal('0.00')
    
    for asset in assets:
        if asset.id not in asset_inventories:
            continue
        
        asset_data = asset_inventories[asset.id]
        inventory = asset_data['inventory']
        short_inventory = asset_data['short_inventory']
        asset_currency = asset_data['currency']
        current_price = asset.current_price or Decimal('0.00')
        
        # 只計算未賣出的持倉（inventory 和 short_inventory 不為空）
        if inventory:  # 多頭持倉
            for batch in inventory:
                unrealized_profit = (current_price - batch['price']) * batch['quantity']
                unrealized_profit_usd = convert_to_usd(unrealized_profit, asset_currency, usd_to_hkd_rate)
                holding_days = (current_date - batch['date']).days
                cost_basis = batch['price'] * batch['quantity']
                cost_basis_usd = convert_to_usd(cost_basis, asset_currency, usd_to_hkd_rate)
                profit_percent = (unrealized_profit_usd / cost_basis_usd * Decimal('100.00')) if cost_basis_usd > 0 else Decimal('0.00')
                
                # 累加未實現損益總額
                total_unrealized_profit += unrealized_profit_usd
                
                # 記錄到買入月份
                monthly_trades[batch['date'].month].append({
                    'profit': unrealized_profit_usd,
                    'profit_percent': profit_percent,
                    'holding_days': holding_days,
                    'fees': Decimal('0.00')
                })
        
        if short_inventory:  # 空頭持倉
            for batch in short_inventory:
                unrealized_profit = (batch['price'] - current_price) * batch['quantity']
                unrealized_profit_usd = convert_to_usd(unrealized_profit, asset_currency, usd_to_hkd_rate)
                holding_days = (current_date - batch['date']).days
                cost_basis = batch['price'] * batch['quantity']
                cost_basis_usd = convert_to_usd(cost_basis, asset_currency, usd_to_hkd_rate)
                profit_percent = (unrealized_profit_usd / cost_basis_usd * Decimal('100.00')) if cost_basis_usd > 0 else Decimal('0.00')
                
                # 累加未實現損益總額
                total_unrealized_profit += unrealized_profit_usd
                
                # 記錄到賣空月份
                monthly_trades[batch['date'].month].append({
                    'profit': unrealized_profit_usd,
                    'profit_percent': profit_percent,
                    'holding_days': holding_days,
                    'fees': Decimal('0.00')
                })
    
    # 計算每月統計
    # 注意：月份名稱由前端根據用戶語言設置進行翻譯
    # 這裡保留英文縮寫作為向後兼容的默認值
    month_names = ['', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    months_data = []
    total_profit = Decimal('0.00')
    
    for month in range(1, 13):
        trades = monthly_trades[month]
        
        if not trades:
            months_data.append({
                'month': month,
                'month_name': month_names[month],
                'avg_profit': Decimal('0.00'),
                'avg_profit_percent': Decimal('0.00'),
                'avg_loss': Decimal('0.00'),
                'avg_loss_percent': Decimal('0.00'),
                'win_rate': Decimal('0.00'),
                'total_trades': 0,
                'max_profit': Decimal('0.00'),
                'max_profit_percent': Decimal('0.00'),
                'max_loss': Decimal('0.00'),
                'max_loss_percent': Decimal('0.00'),
                'avg_holding_days_success': None,
                'avg_holding_days_fail': None,
                'profit': Decimal('0.00')
            })
            continue
        
        # 分離獲利和虧損交易
        profitable_trades = [t for t in trades if t['profit'] > 0]
        losing_trades = [t for t in trades if t['profit'] <= 0]
        
        # 計算統計
        total_trades = len(trades)
        win_count = len(profitable_trades)
        win_rate = (Decimal(str(win_count)) / Decimal(str(total_trades)) * Decimal('100.00')) if total_trades > 0 else Decimal('0.00')
        
        avg_profit = sum(t['profit'] for t in profitable_trades) / len(profitable_trades) if profitable_trades else Decimal('0.00')
        avg_loss = sum(t['profit'] for t in losing_trades) / len(losing_trades) if losing_trades else Decimal('0.00')
        
        # 計算平均百分比
        avg_profit_percent = sum(t.get('profit_percent', Decimal('0.00')) for t in profitable_trades) / len(profitable_trades) if profitable_trades else Decimal('0.00')
        avg_loss_percent = sum(t.get('profit_percent', Decimal('0.00')) for t in losing_trades) / len(losing_trades) if losing_trades else Decimal('0.00')
        
        # 最大獲利：從所有交易中找最大值
        max_profit = max((t['profit'] for t in trades), default=Decimal('0.00'))
        
        # 最大虧損：只從虧損交易中找最小值（最大的虧損）
        losing_profits = [t['profit'] for t in trades if t['profit'] < 0]
        max_loss = min(losing_profits, default=Decimal('0.00')) if losing_profits else Decimal('0.00')
        
        # 找到最大獲利和最大虧損對應的百分比
        max_profit_trade = next((t for t in trades if t['profit'] == max_profit), None)
        max_loss_trade = next((t for t in trades if t['profit'] == max_loss), None) if max_loss < 0 else None
        max_profit_percent = max_profit_trade.get('profit_percent', Decimal('0.00')) if max_profit_trade else Decimal('0.00')
        max_loss_percent = max_loss_trade.get('profit_percent', Decimal('0.00')) if max_loss_trade else Decimal('0.00')
        
        profit = sum(t['profit'] for t in trades)
        total_profit += profit
        
        # 計算平均持有天數
        success_holding_days = [t['holding_days'] for t in profitable_trades if t['holding_days'] > 0]
        fail_holding_days = [t['holding_days'] for t in losing_trades if t['holding_days'] > 0]
        
        avg_holding_days_success = sum(success_holding_days) / len(success_holding_days) if success_holding_days else None
        avg_holding_days_fail = sum(fail_holding_days) / len(fail_holding_days) if fail_holding_days else None
        
        months_data.append({
            'month': month,
            'month_name': month_names[month],
            'avg_profit': avg_profit,
            'avg_profit_percent': avg_profit_percent,
            'avg_loss': avg_loss,
            'avg_loss_percent': avg_loss_percent,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'max_profit': max_profit,
            'max_profit_percent': max_profit_percent,
            'max_loss': max_loss,
            'max_loss_percent': max_loss_percent,
            'avg_holding_days_success': avg_holding_days_success,
            'avg_holding_days_fail': avg_holding_days_fail,
            'profit': profit
        })
    
    # 計算總獲利百分比
    total_profit_percent = Decimal('0.00')
    if starting_capital > 0:
        total_profit_percent = (total_profit / starting_capital) * Decimal('100.00')
    
    # 計算未實現損益百分比
    total_unrealized_profit_percent = Decimal('0.00')
    if starting_capital > 0:
        total_unrealized_profit_percent = (total_unrealized_profit / starting_capital) * Decimal('100.00')
    
    return {
        'year': year,
        'months': months_data,
        'summary': {
            'starting_capital': starting_capital,
            'total_profit': total_profit,
            'total_profit_percent': total_profit_percent,
            'unrealized_profit': total_unrealized_profit,
            'unrealized_profit_percent': total_unrealized_profit_percent
        }
    }