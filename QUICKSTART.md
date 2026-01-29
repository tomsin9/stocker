# Daily Snapshot 快速開始指南

## 5 分鐘設定完成 ⚡

### 步驟 1: 執行 Migration（必須）

```bash
cd backend
source ../.venv/bin/activate
python manage.py migrate portfolio
```

預期輸出：
```
Running migrations:
  Applying portfolio.0007_...OK
```

---

### 步驟 2: 測試功能

```bash
cd backend
bash test_daily_snapshot.sh
```

預期輸出：
```
✓ tom:
  淨資產：$100,000.00
  現金：$10,000.00
  總市值：$90,000.00
  持倉數：5
```

---

### 步驟 3: 設定 Cron Job

```bash
cd backend
bash setup_cron.sh
```

選擇：
- 執行時間：`05:00`（推薦）
- 輸入 `y` 新增到 crontab

---

### 步驟 4: 驗證前端

1. 開啟瀏覽器到 `http://localhost:5173`（或你的前端地址）
2. 登入並進入 Dashboard
3. 檢查「今日變動」是否顯示
4. 點擊「更新股價」，確認「今日變動」基準固定（不會跳）

---

### 步驟 5: 監控（明天檢查）

```bash
# 第二天 05:00 後查看 log
tail -f logs/daily_snapshot.log
```

---

## 完成！🎉

**你現在有了**:
- ✓ 每日自動更新股價
- ✓ 每日投資組合快照
- ✓ 固定的「今日變動」基準
- ✓ 歷史數據（未來可做圖表）

**檢查點**:
- [ ] Migration 執行成功
- [ ] 測試看到快照數據
- [ ] Cron job 已新增到 crontab
- [ ] 前端顯示「今日變動」
- [ ] 更新股價後數字不會跳

---

## 常用指令

```bash
# 手動建立今日快照
python manage.py daily_snapshot

# 查看 crontab
crontab -l | grep daily_snapshot

# 查看 log
tail -f logs/daily_snapshot.log

# 補建昨天的快照
python manage.py daily_snapshot --date=2025-01-28

# 測試 API
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/daily-snapshot/?date=today
```

---

## 需要幫助？

詳細文件: `DAILY_SNAPSHOT.md`  
實作總結: `IMPLEMENTATION_SUMMARY.md`
