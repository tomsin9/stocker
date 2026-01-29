from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

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
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', help_text="擁有此交易的用戶")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    date = models.DateField(default=timezone.now)
    
    # 價格與數量 (使用 Decimal 避免浮點數誤差)
    price = models.DecimalField(max_digits=12, decimal_places=4, help_text="成交單價")
    quantity = models.DecimalField(max_digits=12, decimal_places=4, help_text="股數 (賣出為負數?) - 建議這裡存絕對值，邏輯由 action 判斷")
    fees = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, help_text="手續費")
    
    # 多幣種支持
    currency = models.CharField(max_length=3, choices=Asset.CURRENCY_CHOICES, default='USD', help_text="交易幣種")
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="交易時的匯率（相對於基準幣種）")
    
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'asset']),
        ]

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


class AccountBalance(models.Model):
    """
    記錄用戶的可用現金餘額（作為 cache）
    每個用戶只有一條記錄，用於提升查詢性能
    實際的單一真實來源是動態計算（services.calculate_current_cash）
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='account_balance',
        unique=True,
        help_text="擁有此餘額的用戶"
    )
    
    # 多幣種現金餘額
    cash_usd = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text="USD 現金餘額"
    )
    cash_hkd = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text="HKD 現金餘額"
    )
    total_in_base = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text="以基準幣種（USD）計算的總額"
    )
    
    # 向後兼容字段（deprecated，保留用於遷移期間）
    available_cash = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0,
        help_text="目前可用現金（已棄用，使用 total_in_base）"
    )
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Account Balance"
        verbose_name_plural = "Account Balances"
    
    def __str__(self):
        return f"{self.user.username}: USD ${self.cash_usd}, HKD ${self.cash_hkd}"
    
    @classmethod
    def get_or_create_balance(cls, user):
        """
        獲取或創建用戶的餘額記錄
        返回: (AccountBalance instance, created: bool)
        """
        return cls.objects.get_or_create(user=user)
    
    @classmethod
    def get_current_balance(cls, user):
        """
        取得目前的現金餘額
        注意：實際計算在 services.calculate_current_cash() 中進行
        這個方法保留用於向後兼容
        """
        from .services import calculate_current_cash
        return calculate_current_cash(user)


class CashFlow(models.Model):
    """
    記錄現金流 (入金/出金)
    用於追蹤用戶投入了多少本金
    """
    TYPE_CHOICES = [
        ('DEPOSIT', 'Deposit (存入)'),
        ('WITHDRAW', 'Withdraw (提取)'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cashflows', help_text="擁有此現金流的用戶")
    amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="金額"
    )
    type = models.CharField(
        max_length=10, 
        choices=TYPE_CHOICES,
        help_text="類型：存入或提取"
    )
    # 多幣種支持
    currency = models.CharField(max_length=3, choices=Asset.CURRENCY_CHOICES, default='USD', help_text="現金流幣種")
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="交易時的匯率（相對於基準幣種）")
    date = models.DateField(
        default=timezone.now,
        help_text="日期"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        help_text="備註"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
        verbose_name = "Cash Flow"
        verbose_name_plural = "Cash Flows"
    
    def __str__(self):
        return f"{self.date} - {self.type} ${self.amount}"


class DailySnapshot(models.Model):
    """
    每日投資組合快照
    用於追蹤歷史淨資產、回報率等，並作為「今日變動」的基準
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='daily_snapshots',
        help_text="擁有此快照的用戶"
    )
    date = models.DateField(
        help_text="快照日期"
    )
    
    # 淨資產與現金
    net_liquidity = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="淨資產（總市值 + 總現金）"
    )
    current_cash = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="可用現金（USD 基準）"
    )
    cash_usd = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=0.0,
        help_text="USD 現金餘額"
    )
    cash_hkd = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        default=0.0,
        help_text="HKD 現金餘額"
    )
    
    # 市值與投入本金
    total_market_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="總持倉市值"
    )
    total_invested = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="總投入本金"
    )
    
    # 回報
    net_profit = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        help_text="淨利潤"
    )
    roi_percentage = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="總回報率 (%)"
    )
    
    # 匯率
    exchange_rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4,
        help_text="USD/HKD 匯率"
    )
    
    # 各持倉詳情 (JSON)
    positions = models.JSONField(
        default=dict,
        help_text="各持倉快照 { symbol: { quantity, current_market_value, avg_cost, ... } }"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['user', 'date']),
        ]
        verbose_name = "Daily Snapshot"
        verbose_name_plural = "Daily Snapshots"
    
    def __str__(self):
        return f"{self.user.username} - {self.date}: ${self.net_liquidity}"
    