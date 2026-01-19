from django.db import models
from django.utils import timezone

class Asset(models.Model):
    """
    代表一隻股票或資產 (例如: AAPL, 0700.HK)
    """
    CURRENCY_CHOICES = [
        ('USD', 'USD'),
        ('HKD', 'HKD'),
    ]

    symbol = models.CharField(max_length=20, unique=True, help_text="股票代號 (e.g. AAPL)")
    name = models.CharField(max_length=100, blank=True, help_text="公司名稱")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    sector = models.CharField(max_length=50, blank=True, help_text="板塊 (e.g. Tech)")
    
    # 用來緩存最新價格 (由 yfinance 更新)
    current_price = models.DecimalField(max_digits=12, decimal_places=4, default=0.0)
    last_price_updated = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.symbol} ({self.currency})"


class Transaction(models.Model):
    """
    代表一筆交易紀錄 (買入、賣出、股息)
    """
    ACTION_CHOICES = [
        ('BUY', 'Buy (買入)'),
        ('SELL', 'Sell (賣出)'),
        ('DIVIDEND', 'Dividend (股息)'),
        ('DEPOSIT', 'Deposit (入金)'),   # Optional: 如果你想記現金流
        ('WITHDRAW', 'Withdraw (出金)'), # Optional
    ]

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    date = models.DateField(default=timezone.now)
    
    # 價格與數量 (使用 Decimal 避免浮點數誤差)
    price = models.DecimalField(max_digits=12, decimal_places=4, help_text="成交單價")
    quantity = models.DecimalField(max_digits=12, decimal_places=4, help_text="股數 (賣出為負數?) - 建議這裡存絕對值，邏輯由 action 判斷")
    fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, help_text="手續費")
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.action} {self.asset.symbol} x {self.quantity}"

    @property
    def total_amount(self):
        """計算這筆交易的總金額 (含手續費)"""
        if self.action == 'BUY':
            return -(self.price * self.quantity + self.fees) # 買入是花錢 (負)
        elif self.action == 'SELL':
            return (self.price * self.quantity - self.fees)  # 賣出是賺錢 (正)
        elif self.action == 'DIVIDEND':
            return self.price * self.quantity # 這裡 price 可以當作每股股息
        return 0