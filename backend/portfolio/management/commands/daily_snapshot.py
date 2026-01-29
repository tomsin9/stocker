"""
每日投資組合快照 Management Command

用途：
1. 更新所有持倉的股票價格（呼叫 yfinance）
2. 為每個用戶計算當日的淨資產、持倉市值、現金餘額等
3. 儲存到 DailySnapshot model

建議執行時間：
- 香港時間 05:00（美股收市後，港股開市前）
- 或香港時間 09:00（港股開市前）

Cron 設定範例：
0 5 * * * cd /path/to/backend && python manage.py daily_snapshot
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Prefetch
from portfolio.models import Asset, Transaction, DailySnapshot
from portfolio.services import (
    calculate_position,
    calculate_current_cash,
    get_total_invested_capital,
    get_usd_to_hkd_rate
)
from decimal import Decimal
import yfinance as yf

User = get_user_model()


class Command(BaseCommand):
    help = '每日抓取股票價格並儲存投資組合快照'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='快照日期 (YYYY-MM-DD)，預設為今日',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='只為指定用戶建立快照（username），留空則為所有用戶',
        )

    def handle(self, *args, **options):
        # 1. 決定快照日期
        if options['date']:
            snapshot_date = timezone.datetime.strptime(options['date'], '%Y-%m-%d').date()
        else:
            snapshot_date = timezone.now().date()
        
        self.stdout.write(f"開始建立快照：{snapshot_date}")
        
        # 2. 更新所有股票價格
        self.stdout.write("正在更新股票價格...")
        self.update_all_prices()
        
        # 3. 獲取要處理的用戶列表
        if options['user']:
            users = User.objects.filter(username=options['user'])
            if not users.exists():
                self.stdout.write(self.style.ERROR(f"找不到用戶: {options['user']}"))
                return
        else:
            users = User.objects.all()
        
        # 4. 為每個用戶建立快照
        success_count = 0
        for user in users:
            try:
                self.create_snapshot_for_user(user, snapshot_date)
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f"✓ {user.username}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ {user.username}: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n完成！成功建立 {success_count}/{users.count()} 個快照"))

    def update_all_prices(self):
        """更新所有持倉股票的價格"""
        assets = Asset.objects.all()
        updated_count = 0
        
        for asset in assets:
            try:
                ticker = yf.Ticker(asset.symbol)
                info = ticker.info
                
                # 嘗試獲取當前價格
                current_price = None
                if 'currentPrice' in info and info['currentPrice']:
                    current_price = info['currentPrice']
                elif 'regularMarketPrice' in info and info['regularMarketPrice']:
                    current_price = info['regularMarketPrice']
                elif 'previousClose' in info and info['previousClose']:
                    current_price = info['previousClose']
                
                if current_price:
                    asset.current_price = Decimal(str(current_price))
                    asset.last_price_updated = timezone.now()
                    asset.save()
                    updated_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  無法更新 {asset.symbol}: {str(e)}"))
        
        self.stdout.write(f"  已更新 {updated_count}/{assets.count()} 個股票價格")

    def create_snapshot_for_user(self, user, snapshot_date):
        """為單一用戶建立快照"""
        # 獲取匯率
        usd_to_hkd_rate = get_usd_to_hkd_rate()
        
        # 預載交易記錄以避免 N+1 查詢
        user_assets = Asset.objects.filter(
            transactions__user=user
        ).distinct().prefetch_related(
            Prefetch(
                'transactions',
                queryset=Transaction.objects.filter(user=user).order_by('date'),
                to_attr='user_transactions'
            )
        )
        
        # 計算各持倉
        data = []
        total_market_value = Decimal('0.00')
        positions_dict = {}
        
        for asset in user_assets:
            prefetched_txns = getattr(asset, 'user_transactions', None)
            stats = calculate_position(asset, user, usd_to_hkd_rate, prefetched_transactions=prefetched_txns)
            
            if stats['quantity'] != 0:
                data.append(stats)
                total_market_value += Decimal(str(stats['current_market_value']))
                
                # 儲存到 positions dict
                positions_dict[stats['symbol']] = {
                    'quantity': float(stats['quantity']),
                    'current_market_value': float(stats['current_market_value']),
                    'avg_cost': float(stats['avg_cost']),
                    'current_price': float(stats.get('current_price', 0)),
                    'unrealized_pl': float(stats.get('unrealized_pl', 0)),
                    'currency': stats.get('currency', 'USD')
                }
        
        # 計算現金
        cash_data = calculate_current_cash(user, base_currency='USD')
        current_cash_usd = cash_data['USD']
        current_cash_hkd = cash_data['HKD']
        current_cash_total = cash_data['total_in_base']
        
        # 計算總投入本金
        total_invested = get_total_invested_capital(user)
        
        # 計算淨資產
        net_liquidity = total_market_value + current_cash_total
        
        # 計算淨利潤與回報率
        net_profit = net_liquidity - total_invested
        roi_percentage = Decimal('0.00')
        if total_invested > 0:
            roi_percentage = (net_profit / total_invested) * Decimal('100.00')
        
        # 建立或更新快照
        snapshot, created = DailySnapshot.objects.update_or_create(
            user=user,
            date=snapshot_date,
            defaults={
                'net_liquidity': float(net_liquidity),
                'current_cash': float(current_cash_total),
                'cash_usd': float(current_cash_usd),
                'cash_hkd': float(current_cash_hkd),
                'total_market_value': float(total_market_value),
                'total_invested': float(total_invested),
                'net_profit': float(net_profit),
                'roi_percentage': float(roi_percentage),
                'exchange_rate': float(usd_to_hkd_rate),
                'positions': positions_dict
            }
        )
        
        action = "建立" if created else "更新"
        return snapshot, action
