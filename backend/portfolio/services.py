# backend/portfolio/services.py
from decimal import Decimal
from django.db import models
from .models import Transaction, CashFlow, AccountBalance, Asset
import yfinance as yf

def get_usd_to_hkd_rate():
    """
    獲取 USD 到 HKD 的匯率
    使用 yfinance 獲取 HKD=X 匯率，如果失敗則使用固定匯率 7.8 作為 fallback
    """
    try:
        ticker = yf.Ticker("HKD=X")
        info = ticker.info
        rate = info.get('regularMarketPrice') or info.get('currentPrice')
        if rate:
            return Decimal(str(rate))
    except Exception as e:
        print(f"無法獲取匯率: {e}")
    
    # Fallback: 使用固定匯率 7.8
    return Decimal('7.8')

def get_total_invested_capital():
    """
    計算總投入本金：所有 CashFlow 中 DEPOSIT 減去 WITHDRAW 的總和
    """
    total_deposits = CashFlow.objects.filter(type='DEPOSIT').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_withdraws = CashFlow.objects.filter(type='WITHDRAW').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    return total_deposits - total_withdraws

def calculate_current_cash():
    """
    計算目前的可用現金：
    現金流 (存入 - 提取) + 賣出收入 - 買入支出 + 股息收入
    """
    # 現金流
    total_deposits = CashFlow.objects.filter(type='DEPOSIT').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    total_withdraws = CashFlow.objects.filter(type='WITHDRAW').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    # 交易影響
    buy_transactions = Transaction.objects.filter(action='BUY').aggregate(
        total=models.Sum(models.F('price') * models.F('quantity') + models.F('fees'))
    )['total'] or Decimal('0.00')
    
    sell_transactions = Transaction.objects.filter(action='SELL').aggregate(
        total=models.Sum(models.F('price') * models.F('quantity') - models.F('fees'))
    )['total'] or Decimal('0.00')
    
    dividend_transactions = Transaction.objects.filter(action='DIVIDEND').aggregate(
        total=models.Sum(models.F('price') * models.F('quantity'))
    )['total'] or Decimal('0.00')
    
    # 現金餘額 = 存入 - 提取 + 賣出 - 買入 + 股息
    current_cash = (
        total_deposits - total_withdraws + 
        sell_transactions - buy_transactions + 
        dividend_transactions
    )
    
    return current_cash

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

def calculate_position(asset, usd_to_hkd_rate=None):
    """
    使用 FIFO (先進先出) 邏輯計算某檔股票的：
    1. 當前持倉數量
    2. 平均成本 (剩餘持倉的加權平均)
    3. 已實現損益 (Realized P&L)
    
    所有計算結果統一轉換為 USD
    """
    if usd_to_hkd_rate is None:
        usd_to_hkd_rate = get_usd_to_hkd_rate()
    
    # 判斷資產幣種
    asset_currency = asset.currency or detect_asset_currency(asset.symbol)
    
    # 拿出這隻股票的所有交易，按日期排序 (最舊的在前面 -> FIFO)
    transactions = asset.transactions.all().order_by('date', 'created_at')
    
    inventory = []  # 倉庫：存這檔股票目前的持倉 [(price, quantity), ...]
    realized_pl = Decimal('0.00') # 已實現損益（USD）
    total_dividends = Decimal('0.00') # 股息（USD）

    for t in transactions:
        if t.action == 'BUY':
            # 買入：入庫
            inventory.append({
                'price': t.price,
                'quantity': t.quantity,
                'date': t.date
            })
            
        elif t.action == 'SELL':
            # 賣出：從倉庫最前面開始拿貨 (FIFO)
            qty_to_sell = t.quantity
            total_gain = Decimal('0.00')  # 累計獲利
            
            while qty_to_sell > 0:
                if not inventory:
                    # 異常狀況：賣出的比庫存多 (可能是放空或資料漏記)
                    # 這裡暫時當作成本為 0 處理，或者你可以 raise Error
                    remaining_gain = qty_to_sell * t.price
                    # 轉換為 USD
                    remaining_gain_usd = convert_to_usd(remaining_gain, asset_currency, usd_to_hkd_rate)
                    total_gain += remaining_gain_usd
                    qty_to_sell = 0
                    break

                # 拿出第一批貨 (FIFO)
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
    
    # 1. 剩餘持倉股數
    current_quantity = sum(item['quantity'] for item in inventory)
    
    # 2. 剩餘持倉的總成本（轉換為 USD）
    total_cost = sum(item['price'] * item['quantity'] for item in inventory)
    total_cost_usd = convert_to_usd(total_cost, asset_currency, usd_to_hkd_rate)
    
    # 3. 平均成本 (Avg Cost) - USD
    avg_cost_usd = Decimal('0.00')
    if current_quantity > 0:
        avg_cost_usd = total_cost_usd / current_quantity

    # 4. 當前市值（轉換為 USD）
    current_market_value = current_quantity * asset.current_price
    current_market_value_usd = convert_to_usd(current_market_value, asset_currency, usd_to_hkd_rate)
    
    # 5. 未實現損益（USD）
    unrealized_pl_usd = current_market_value_usd - total_cost_usd if current_quantity > 0 else Decimal('0.00')

    return {
        'symbol': asset.symbol,
        'currency': asset_currency,
        'quantity': current_quantity,
        'avg_cost': avg_cost_usd,  # USD
        'realized_pl': realized_pl,  # USD
        'total_dividends': total_dividends,  # USD
        'current_market_value': current_market_value_usd,  # USD
        'unrealized_pl': unrealized_pl_usd  # USD
    }