# Daily Snapshot 實作總結

## 完成項目 ✓

### 1. Backend

#### ✓ DailySnapshot Model
- **檔案**: `backend/portfolio/models.py`
- **功能**: 
  - 儲存每日淨資產、現金、持倉快照
  - 支援多幣種（USD/HKD）
  - JSON 欄位儲存各持倉詳情
  - unique_together (user, date) 確保每天只有一個快照

#### ✓ Management Command
- **檔案**: `backend/portfolio/management/commands/daily_snapshot.py`
- **功能**:
  - 更新所有股票價格（yfinance）
  - 為每個用戶計算並儲存快照
  - 支援指定日期、指定用戶
  - 用法：`python manage.py daily_snapshot [--date=YYYY-MM-DD] [--user=username]`

#### ✓ API Endpoints
- **檔案**: `backend/portfolio/views.py`, `backend/portfolio/urls.py`
- **Endpoints**:
  - `GET /api/daily-snapshot/?date=today` - 獲取單日快照
  - `GET /api/daily-snapshot/history/?limit=30` - 獲取歷史快照列表
- **權限**: IsAuthenticated，只返回當前用戶的數據

#### ✓ Migration
- **檔案**: `backend/portfolio/migrations/0007_*.py`
- **狀態**: 已生成，待執行 `python manage.py migrate`

### 2. Frontend

#### ✓ HomeView 修改
- **檔案**: `frontend/src/views/HomeView.vue`
- **改動**:
  - 優先使用後端 daily snapshot API
  - Fallback 到 localStorage（向後兼容）
  - 用本地日期 (en-CA) 避免 UTC 時區問題
  - 淨資產今日 = 持倉今日加總 + 現金變動（數字一致）

### 3. Cron Job 設定

#### ✓ 自動化腳本
- **檔案**: `backend/setup_cron.sh`
- **功能**:
  - 互動式設定 cron job
  - 自動建立 logs 目錄
  - 檢查是否已存在避免重複
  - 預設香港時間 05:00（可改 09:00）

#### ✓ 測試腳本
- **檔案**: `backend/test_daily_snapshot.sh`
- **功能**:
  - 執行 daily_snapshot command
  - 檢查 database 是否有快照
  - 顯示最近 7 天快照
  - 驗證功能正常

### 4. 文件

#### ✓ 完整說明文件
- **檔案**: `DAILY_SNAPSHOT.md`
- **內容**:
  - 架構說明（Backend/Frontend/Cron）
  - 使用方法（手動執行、API、測試）
  - 未來擴充（歷史圖表、回報率分析）
  - 常見問題 FAQ
  - 維護指南

#### ✓ 實作總結
- **檔案**: `IMPLEMENTATION_SUMMARY.md`（本檔案）

#### ✓ Logs 目錄
- **路徑**: `logs/`
- **配置**: `.gitignore` 設定（忽略 *.log，保留目錄）

## 下一步操作

### 1. 執行 Migration（必須）

```bash
cd backend
source ../.venv/bin/activate
python manage.py migrate portfolio
```

### 2. 測試功能

```bash
cd backend
bash test_daily_snapshot.sh
```

應該會看到：
- ✓ 所有用戶的快照已建立
- 淨資產、現金、持倉數據正確
- 最近 7 天的快照列表

### 3. 設定 Cron Job

```bash
cd backend
bash setup_cron.sh
```

選擇：
- 執行時間：05:00（推薦）或 09:00
- 確認路徑正確
- 輸入 `y` 新增到 crontab

### 4. 驗證前端

1. 開啟瀏覽器到 HomeView
2. 檢查 DevTools Console 是否有 `/api/daily-snapshot/?date=today` 呼叫
3. 檢查「今日變動」是否顯示
4. 點擊「更新股價」，確認「今日變動」**不會**改變（基準固定）

### 5. 監控 Log（首次執行後）

```bash
# 等到明天 05:00 cron job 執行後
tail -f logs/daily_snapshot.log
```

應該會看到：
```
開始建立快照：2025-01-30
正在更新股票價格...
  已更新 X/Y 個股票價格
✓ tom
完成！成功建立 1/1 個快照
```

## 技術細節

### 時區處理

- **問題**: 之前用 UTC 日期 (`toISOString()`)，香港時間會跳日期
- **解決**: 改用本地日期 (`toLocaleDateString('en-CA')`)
- **結果**: 「今日」跟用戶日曆一致，不會在 UTC 午夜跳

### 數字一致性

- **問題**: 淨資產今日 ≠ 持倉今日加總（後端四捨五入差異）
- **解決**: 淨資產今日 = Σ(持倉今日) + 現金變動（公式統一）
- **結果**: 大數永遠等於各持倉加總，不會「唔對」

### Snapshot 來源優先順序

1. **後端 API** (`/api/daily-snapshot/?date=today`)
   - 有 cron job 時：所有用戶看到一致的基準（最好）
   - 沒有時：返回 null，fallback 到下一個

2. **localStorage**（本地日期 key）
   - 用戶首次載入時寫入
   - 作為後端沒有 snapshot 時的備用

3. **當前數據**（最後手段）
   - localStorage 也讀不到時
   - 今日變動顯示 $0.00 (0.00%)

### 未來移除 localStorage

當每天都有後端 snapshot 後（cron job 穩定運作）：
1. 前端可以移除 localStorage fallback 邏輯
2. 完全依賴後端 API
3. 簡化程式碼

## 資料夾結構

```
tom_stocker/
├── backend/
│   ├── portfolio/
│   │   ├── models.py                    # ✓ 加入 DailySnapshot
│   │   ├── views.py                     # ✓ 加入 API endpoints
│   │   ├── urls.py                      # ✓ 加入 routes
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── daily_snapshot.py    # ✓ 新增
│   │   └── migrations/
│   │       └── 0007_*.py                # ✓ 生成
│   ├── setup_cron.sh                    # ✓ 新增
│   └── test_daily_snapshot.sh           # ✓ 新增
├── frontend/
│   └── src/
│       └── views/
│           └── HomeView.vue             # ✓ 修改（用後端 snapshot）
├── logs/
│   ├── .gitkeep                         # ✓ 新增
│   └── .gitignore                       # ✓ 新增
├── DAILY_SNAPSHOT.md                    # ✓ 新增
└── IMPLEMENTATION_SUMMARY.md            # ✓ 新增（本檔案）
```

## 未來擴充計劃

### 1. 歷史淨資產走勢圖（優先）

**前端**:
```javascript
// 在 HomeView 加 Chart 組件
const response = await api.get('/daily-snapshot/history/?limit=30')
const chartData = {
  labels: response.data.snapshots.map(s => s.date),
  datasets: [{
    label: '淨資產',
    data: response.data.snapshots.map(s => s.net_liquidity)
  }]
}
```

**建議工具**: Chart.js 或 ECharts

### 2. 每日回報率分析

**計算**:
```python
# Backend 可加 computed field
daily_return = (today.net_liquidity - yesterday.net_liquidity) / yesterday.net_liquidity * 100
```

**顯示**: 表格或圖表，紅綠顯示漲跌

### 3. 月度/年度統計

**API**:
```python
GET /api/daily-snapshot/stats/?year=2025&month=1

Response:
{
  "monthly_return": 5.23,  # %
  "best_day": { "date": "2025-01-15", "return": 2.1 },
  "worst_day": { "date": "2025-01-08", "return": -1.5 },
  ...
}
```

### 4. 持倉歷史走勢

**用途**: 查看單一股票的歷史市值變化

**實作**: 從 `snapshot.positions[symbol]` 抓歷史數據

### 5. 清理舊 Snapshot

**Management Command**:
```bash
python manage.py cleanup_snapshots --days=365
```

**功能**: 只保留最近一年，刪除更早的

## 疑難排解

### Migration 錯誤

```bash
# 如果 migration 有問題，重新生成
python manage.py makemigrations portfolio --empty
# 手動編輯 migration 檔案
python manage.py migrate portfolio
```

### Cron Job 不執行

1. **檢查 crontab**:
   ```bash
   crontab -l | grep daily_snapshot
   ```

2. **檢查路徑**:
   ```bash
   # 在 cron 命令中加 echo 測試
   0 5 * * * echo "Cron running" >> /path/to/test.log
   ```

3. **檢查權限**:
   ```bash
   ls -la backend/manage.py  # 應該有執行權限
   ```

4. **手動測試**:
   ```bash
   cd backend
   source ../.venv/bin/activate
   python manage.py daily_snapshot
   ```

### API 返回 null

**原因**: 今天還沒有 snapshot

**解決**:
1. 手動執行一次: `python manage.py daily_snapshot`
2. 或等 cron job 自動執行
3. 前端會 fallback 到 localStorage，不影響使用

### 前端顯示 $0.00

**原因**: 沒有基準（後端無 snapshot，localStorage 也無）

**解決**: 重新整理頁面，首次載入會寫入基準

## 總結

✓ **完成**:
- DailySnapshot model + migration
- Management command (daily_snapshot)
- API endpoints (2 個)
- Frontend 整合（優先用後端，fallback localStorage）
- Cron job 設定腳本
- 測試腳本
- 完整文件

✓ **優點**:
- 真正的「今日」基準（不靠首次載入）
- 所有用戶看到一致的數據
- 歷史數據保存，未來可做分析
- 向後兼容（localStorage fallback）
- 時區問題已解決（本地日期）
- 數字一致（淨資產 = 持倉加總 + 現金變動）

🎯 **下一步**: 執行 migration → 測試 → 設定 cron → 驗證前端
