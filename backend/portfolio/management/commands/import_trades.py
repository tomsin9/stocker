import csv
import pandas as pd
from datetime import datetime
from django.core.management.base import BaseCommand
from portfolio.models import Asset, Transaction
import math

class Command(BaseCommand):
    help = 'Import trades from Apple Numbers CSV export'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        self.stdout.write(f"Reading CSV from: {csv_file_path}")

        # 使用 pandas 讀取，因為它處理髒數據比較方便
        try:
            df = pd.read_csv(csv_file_path)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV: {e}"))
            return

        count_created = 0
        
        # 你的 CSV Headers (根據你提供的):
        # Ticker, 股數, 買入價, 賣出價, 獲利, 獲利%, 勝負, 買入時間, 賣出時間, 月份, 持有時間

        for index, row in df.iterrows():
            ticker_raw = row.get('Ticker')
            
            # 1. 檢查 Ticker 是否有效 (跳過空行)
            if pd.isna(ticker_raw) or str(ticker_raw).strip() == '':
                continue

            # 2. 處理股票代號 (Symbol Logic)
            symbol = str(ticker_raw).strip().upper()
            
            # 判斷是否為數字 (港股)，例如 700 -> 0700.HK
            # 這裡簡單判斷：如果移除小數點後全是數字，就當作港股
            is_digit = str(ticker_raw).replace('.', '').isdigit()
            if is_digit:
                # 轉成整數再轉字串，去掉可能的小數點 .0
                symbol_int = int(float(ticker_raw)) 
                symbol = f"{symbol_int:04d}.HK" # 補零至4位並加 .HK
            else:
                # 美股，保持原樣 (e.g., AAPL)
                pass

            # 3. 取得或建立 Asset
            # 簡單判斷幣種：有 .HK 是港幣，否則美金
            currency = 'HKD' if '.HK' in symbol else 'USD'
            
            asset, created = Asset.objects.get_or_create(
                symbol=symbol,
                defaults={'currency': currency}
            )

            # 4. 解析數值
            try:
                quantity = float(row.get('股數', 0))
                buy_price = float(row.get('買入價', 0))
                sell_price = float(row.get('賣出價', 0))
                
                # 處理日期 DD/MM/YYYY
                buy_date_str = str(row.get('買入時間', '')).strip()
                sell_date_str = str(row.get('賣出時間', '')).strip()
                
                buy_date = None
                sell_date = None

                if buy_date_str and buy_date_str.lower() != 'nan':
                    buy_date = datetime.strptime(buy_date_str, "%d/%m/%Y").date()
                
                if sell_date_str and sell_date_str.lower() != 'nan':
                    sell_date = datetime.strptime(sell_date_str, "%d/%m/%Y").date()

            except ValueError as e:
                self.stdout.write(self.style.WARNING(f"Skipping row {index}: Data format error ({e})"))
                continue

            # 5. 建立交易紀錄 (把一行拆成兩行)

            # --- PART A: 買入紀錄 (如果有買入時間和價格) ---
            if buy_date and buy_price > 0:
                Transaction.objects.create(
                    asset=asset,
                    action='BUY',
                    date=buy_date,
                    price=buy_price,
                    quantity=quantity, # 買入 N 股
                    fees=0  # 舊資料假設無手續費
                )
                count_created += 1

            # --- PART B: 賣出紀錄 (如果有賣出時間和價格) ---
            # 注意：Numbers 這一行如果是平倉單，代表這 N 股也賣出了
            if sell_date and sell_price > 0:
                Transaction.objects.create(
                    asset=asset,
                    action='SELL',
                    date=sell_date,
                    price=sell_price,
                    quantity=quantity, # 賣出 N 股
                    fees=0
                )
                count_created += 1

            self.stdout.write(f"Processed {symbol}...")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count_created} transactions!'))