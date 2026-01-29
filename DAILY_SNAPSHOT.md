# Daily Snapshot 每日快照功能

## 概述

每日投資組合快照功能，用於：
1. 作為「今日變動」的基準（取代 localStorage）
2. 儲存歷史數據，未來可做：
   - 歷史淨資產走勢圖
   - 每日回報率分析
   - 月度/年度表現統計

## 架構

### 1. Backend

#### DailySnapshot Model
```python
# backend/portfolio/models.py
class DailySnapshot(models.Model):
    user = ForeignKey(User)
    date = DateField()  # 快照日期
    net_liquidity = Decimal  # 淨資產
    current_cash = Decimal  # 現金
    total_market_value = Decimal  # 總市值
    positions = JSONField  # { symbol: { quantity, mv, ... } }
    ...
```

#### Management Command
```bash
# 手動執行
python manage.py daily_snapshot

# 只為特定用戶建立
python manage.py daily_snapshot --user=tom

# 指定日期
python manage.py daily_snapshot --date=2025-01-29
```

功能：
1. 更新所有持倉的股票價格（yfinance）
2. 為每個用戶計算淨資產、持倉、現金
3. 儲存到 DailySnapshot

#### API Endpoints

**獲取單日快照**
```
GET /api/daily-snapshot/?date=today
GET /api/daily-snapshot/?date=2025-01-29

Response:
{
  "snapshot": {
    "date": "2025-01-29",
    "net_liquidity": 100000.00,
    "current_cash": 10000.00,
    "positions": {
      "AAPL": { "quantity": 100, "current_market_value": 18500 },
      ...
    }
  }
}
```

**獲取歷史快照列表**
```
GET /api/daily-snapshot/history/?limit=30
GET /api/daily-snapshot/history/?start_date=2025-01-01&end_date=2025-01-31

Response:
{
  "snapshots": [
    { "date": "2025-01-29", "net_liquidity": 100000, ... },
    { "date": "2025-01-28", "net_liquidity": 98500, ... },
    ...
  ]
}
```

### 2. Frontend

#### HomeView 修改

```javascript
// 優先使用後端 snapshot，fallback 到 localStorage
const snapshotResponse = await api.get('/daily-snapshot/?date=today')
if (snapshotResponse.data.snapshot) {
  // 使用後端 snapshot
  netLiquidityStartOfDay.value = snapshot.net_liquidity
  positionSodMap.value = snapshot.positions
} else {
  // fallback 到 localStorage（舊邏輯）
  ...
}
```

優點：
- 後端有 snapshot：所有用戶看到一致的「今日」基準
- 後端沒有 snapshot：還能用 localStorage，不會壞掉
- 未來可移除 localStorage 邏輯，完全用後端

### 3. Cron Job

#### 執行時間建議

**選項 1：香港時間 05:00（推薦）**
- 美股收市後（04:00 夏令 / 05:00 冬令）
- 港股開市前
- 抓到「昨日收市價」

**選項 2：香港時間 09:00**
- 美股已收、港股未開
- 適合「今日開始」基準

#### 設定方法

**方法 1：使用 setup_cron.sh（推薦）**
```bash
cd backend
bash setup_cron.sh
```

腳本會：
1. 檢查並建立 logs 目錄
2. 顯示 Cron Job 資訊
3. 詢問是否新增到 crontab
4. 自動設定

**方法 2：手動設定**
```bash
# 編輯 crontab
crontab -e

# 新增以下行（香港時間 05:00）
0 5 * * * cd /path/to/backend && source /path/to/.venv/bin/activate && python manage.py daily_snapshot >> /path/to/logs/daily_snapshot.log 2>&1
```

## 測試

### 1. 測試 Management Command

```bash
cd backend
source ../.venv/bin/activate

# 為所有用戶建立今日快照
python manage.py daily_snapshot

# 只為特定用戶
python manage.py daily_snapshot --user=tom

# 指定日期（用於補建歷史）
python manage.py daily_snapshot --date=2025-01-28
```

### 2. 測試 API

```bash
# 獲取今日快照
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/daily-snapshot/?date=today

# 獲取歷史快照
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/daily-snapshot/history/?limit=7
```

### 3. 測試前端

1. 開啟 HomeView
2. 檢查「今日變動」是否正確
3. 更新股價，檢查「今日變動」是否維持一致（不會跳）
4. 檢查 Console 是否有 snapshot API 呼叫

## Migration

```bash
cd backend
source ../.venv/bin/activate

# 生成 migration
python manage.py makemigrations portfolio

# 執行 migration
python manage.py migrate portfolio
```

## 未來擴充

### 1. 歷史走勢圖
```javascript
// 未來可在 frontend 加入
const response = await api.get('/daily-snapshot/history/?limit=30')
const data = response.data.snapshots.map(s => ({
  date: s.date,
  value: s.net_liquidity
}))
// 用 Chart.js 或 ECharts 畫圖
```

### 2. 每日回報率
```javascript
// 計算每日變動百分比
const dailyReturns = snapshots.map((snap, i) => {
  if (i === 0) return null
  const prev = snapshots[i - 1]
  return ((snap.net_liquidity - prev.net_liquidity) / prev.net_liquidity) * 100
})
```

### 3. 月度/年度統計
```javascript
// 用 daily snapshots 計算月度回報
const monthlyReturn = (endOfMonth.net_liquidity - startOfMonth.net_liquidity) 
                      / startOfMonth.net_liquidity * 100
```

## 常見問題

### Q: 為什麼選擇 05:00 而不是 12:00？

A: 
- 中午兩個市場都開著，價格一直變
- 05:00 美股已收、港股未開，抓到「昨日收市價」作為今日基準更合理

### Q: 如果錯過了某天的 snapshot 怎麼辦？

A: 可以手動補建：
```bash
python manage.py daily_snapshot --date=2025-01-28
```

### Q: Cron Job 沒執行怎麼辦？

A: 
1. 檢查 crontab 是否正確：`crontab -l | grep daily_snapshot`
2. 檢查 log：`tail -f logs/daily_snapshot.log`
3. 手動執行測試：`python manage.py daily_snapshot`
4. 檢查虛擬環境路徑是否正確

### Q: 前端還會用 localStorage 嗎？

A: 
- 現在：後端沒有 snapshot 時會 fallback 到 localStorage
- 未來：當每天都有 snapshot 後，可以移除 localStorage 邏輯

### Q: 如何清理舊的 snapshot？

A: 可以寫個 management command：
```bash
python manage.py cleanup_snapshots --days=365  # 只保留一年
```

## 維護

### 查看 Log
```bash
tail -f logs/daily_snapshot.log
```

### 查看 Crontab
```bash
crontab -l
```

### 停止 Cron Job
```bash
crontab -e
# 註釋或刪除 daily_snapshot 那行
```

### 資料庫查詢
```python
from portfolio.models import DailySnapshot
from django.contrib.auth.models import User

user = User.objects.get(username='tom')

# 最近 7 天
snapshots = DailySnapshot.objects.filter(user=user).order_by('-date')[:7]

# 特定日期
snapshot = DailySnapshot.objects.get(user=user, date='2025-01-29')
```
