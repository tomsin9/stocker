# backend/portfolio/services.py
from decimal import Decimal
from django.db import models
from django.conf import settings
from .models import Transaction, CashFlow, AccountBalance, Asset
import yfinance as yf
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import time

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
    deposits = CashFlow.objects.filter(user=user, type='DEPOSIT')
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
    cashflows = CashFlow.objects.filter(user=user)
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

def calculate_position(asset, user, usd_to_hkd_rate=None):
    """
    使用 FIFO (先進先出) 邏輯計算某檔股票的：
    1. 當前持倉數量（支援負數，表示賣空）
    2. 平均成本 (剩餘持倉的加權平均)
    3. 已實現損益 (Realized P&L)
    
    所有計算結果統一轉換為 USD
    支援賣空：允許負數持倉
    """
    if usd_to_hkd_rate is None:
        usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    # 判斷資產幣種
    asset_currency = asset.currency or detect_asset_currency(asset.symbol)
    
    # 拿出這隻股票的所有交易，按日期排序 (最舊的在前面 -> FIFO)
    # 只獲取當前用戶的交易
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