#!/bin/bash
# Daily Snapshot Cron Job 設定腳本
# 
# 用途：每日自動抓取股價並建立投資組合快照
# 
# 建議執行時間：
# - 選項 1：香港時間 05:00（美股收市後、港股開市前）
# - 選項 2：香港時間 09:00（港股開市前）
#
# 使用方法：
# 1. 修改下方的 PROJECT_PATH 為你的專案路徑
# 2. 修改 VENV_PATH 為你的虛擬環境路徑
# 3. 選擇執行時間（05:00 或 09:00）
# 4. 執行此腳本：bash setup_cron.sh

# ==================== 設定區 ====================
# 請修改以下路徑為你的實際路徑
PROJECT_PATH="/Users/user/Desktop/personal/Tom/tom_stocker"
VENV_PATH="$PROJECT_PATH/.venv"
BACKEND_PATH="$PROJECT_PATH/backend"

# 選擇執行時間（取消註釋其中一個）
CRON_TIME="0 5 * * *"   # 每日 05:00
# CRON_TIME="0 9 * * *"   # 每日 09:00

# ==================== Cron Job 命令 ====================
CRON_CMD="cd $BACKEND_PATH && source $VENV_PATH/bin/activate && python manage.py daily_snapshot >> $PROJECT_PATH/logs/daily_snapshot.log 2>&1"

# ==================== 建立 logs 目錄 ====================
mkdir -p "$PROJECT_PATH/logs"

# ==================== 顯示 Cron Job ====================
echo "================================================"
echo "Daily Snapshot Cron Job"
echo "================================================"
echo ""
echo "執行時間: $CRON_TIME (香港時間)"
echo "專案路徑: $PROJECT_PATH"
echo "虛擬環境: $VENV_PATH"
echo "Log 檔案: $PROJECT_PATH/logs/daily_snapshot.log"
echo ""
echo "Cron Job 命令："
echo "$CRON_TIME $CRON_CMD"
echo ""
echo "================================================"
echo ""

# ==================== 新增到 Crontab ====================
read -p "是否要新增此 Cron Job 到 crontab？(y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # 檢查是否已存在
    if crontab -l 2>/dev/null | grep -q "daily_snapshot"; then
        echo "⚠️  Cron Job 已存在，跳過新增"
    else
        # 新增到 crontab
        (crontab -l 2>/dev/null; echo "$CRON_TIME $CRON_CMD") | crontab -
        echo "✓ Cron Job 已新增"
    fi
    
    echo ""
    echo "目前的 crontab："
    crontab -l | grep "daily_snapshot"
    echo ""
    echo "================================================"
    echo "設定完成！"
    echo ""
    echo "查看 log："
    echo "  tail -f $PROJECT_PATH/logs/daily_snapshot.log"
    echo ""
    echo "手動測試："
    echo "  cd $BACKEND_PATH && source $VENV_PATH/bin/activate && python manage.py daily_snapshot"
    echo ""
else
    echo ""
    echo "未新增 Cron Job。"
    echo ""
    echo "如果你想手動新增，請執行："
    echo "  crontab -e"
    echo ""
    echo "然後新增以下行："
    echo "  $CRON_TIME $CRON_CMD"
    echo ""
fi
