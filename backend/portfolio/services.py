# backend/portfolio/services.py
from decimal import Decimal
from .models import Transaction

def calculate_position(asset):
    """
    使用 FIFO (先進先出) 邏輯計算某檔股票的：
    1. 當前持倉數量
    2. 平均成本 (剩餘持倉的加權平均)
    3. 已實現損益 (Realized P&L)
    """
    # 拿出這隻股票的所有交易，按日期排序 (最舊的在前面 -> FIFO)
    transactions = asset.transactions.all().order_by('date', 'created_at')
    
    inventory = []  # 倉庫：存這檔股票目前的持倉 [(price, quantity), ...]
    realized_pl = Decimal('0.00') # 已實現損益
    total_dividends = Decimal('0.00')

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
            
            while qty_to_sell > 0:
                if not inventory:
                    # 異常狀況：賣出的比庫存多 (可能是放空或資料漏記)
                    # 這裡暫時當作成本為 0 處理，或者你可以 raise Error
                    remaining_gain = qty_to_sell * t.price
                    realized_pl += remaining_gain
                    qty_to_sell = 0
                    break

                # 拿出第一批貨 (FIFO)
                batch = inventory[0]
                
                if batch['quantity'] > qty_to_sell:
                    # 這批貨夠賣，且還有剩
                    # 獲利 = (賣價 - 成本價) * 賣出數量
                    gain = (t.price - batch['price']) * qty_to_sell
                    realized_pl += gain - t.fees # 扣掉交易手續費
                    
                    # 更新庫存數量
                    batch['quantity'] -= qty_to_sell
                    qty_to_sell = 0
                    
                else:
                    # 這批貨不夠賣，全部賣光，再拿下一批
                    sold_qty = batch['quantity']
                    gain = (t.price - batch['price']) * sold_qty
                    realized_pl += gain
                    
                    # 扣除這部分的比例手續費 (簡單起見，手續費可以在最後一次扣，這裡先不分拆)
                    
                    qty_to_sell -= sold_qty
                    inventory.pop(0) # 這批貨賣光了，移除
            
            # 把整筆賣單的手續費扣除 (如果上面沒有分批扣)
            realized_pl -= t.fees

        elif t.action == 'DIVIDEND':
            total_dividends += t.total_amount

    # --- 計算結果 ---
    
    # 1. 剩餘持倉股數
    current_quantity = sum(item['quantity'] for item in inventory)
    
    # 2. 剩餘持倉的總成本
    total_cost = sum(item['price'] * item['quantity'] for item in inventory)
    
    # 3. 平均成本 (Avg Cost)
    avg_cost = Decimal('0.00')
    if current_quantity > 0:
        avg_cost = total_cost / current_quantity

    return {
        'symbol': asset.symbol,
        'quantity': current_quantity,
        'avg_cost': avg_cost,
        'realized_pl': realized_pl,
        'total_dividends': total_dividends,
        'current_market_value': current_quantity * asset.current_price,
        'unrealized_pl': (asset.current_price - avg_cost) * current_quantity if current_quantity > 0 else 0
    }