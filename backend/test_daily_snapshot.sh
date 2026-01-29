#!/bin/bash
# 測試 Daily Snapshot 功能
# 
# 用途：手動測試 daily snapshot 是否正常運作
# 
# 使用方法：
#   bash test_daily_snapshot.sh

PROJECT_PATH="/Users/user/Desktop/personal/Tom/tom_stocker"
VENV_PATH="$PROJECT_PATH/.venv"
BACKEND_PATH="$PROJECT_PATH/backend"

echo "================================================"
echo "Daily Snapshot 測試"
echo "================================================"
echo ""

# 啟動虛擬環境
cd "$BACKEND_PATH"
source "$VENV_PATH/bin/activate"

echo "1. 執行 daily_snapshot command..."
echo "================================================"
python manage.py daily_snapshot
echo ""

echo "2. 檢查 DailySnapshot 資料..."
echo "================================================"
python manage.py shell << 'EOF'
from portfolio.models import DailySnapshot
from django.contrib.auth.models import User
from django.utils import timezone

today = timezone.now().date()
users = User.objects.all()

print(f"今日：{today}")
print(f"用戶數：{users.count()}")
print("")

for user in users:
    try:
        snapshot = DailySnapshot.objects.get(user=user, date=today)
        print(f"✓ {user.username}:")
        print(f"  淨資產：${snapshot.net_liquidity:,.2f}")
        print(f"  現金：${snapshot.current_cash:,.2f}")
        print(f"  總市值：${snapshot.total_market_value:,.2f}")
        print(f"  持倉數：{len(snapshot.positions)}")
        print("")
    except DailySnapshot.DoesNotExist:
        print(f"✗ {user.username}: 沒有今日快照")
        print("")

EOF

echo "3. 顯示最近 7 天的快照..."
echo "================================================"
python manage.py shell << 'EOF'
from portfolio.models import DailySnapshot
from django.contrib.auth.models import User

users = User.objects.all()

for user in users:
    print(f"\n{user.username} 的最近快照：")
    print("-" * 60)
    snapshots = DailySnapshot.objects.filter(user=user).order_by('-date')[:7]
    
    if not snapshots:
        print("  （無快照）")
        continue
    
    print(f"{'日期':<12} {'淨資產':>15} {'現金':>15} {'回報率':>10}")
    print("-" * 60)
    for snap in snapshots:
        print(f"{snap.date} ${snap.net_liquidity:>13,.2f} ${snap.current_cash:>13,.2f} {snap.roi_percentage:>9.2f}%")

EOF

echo ""
echo "================================================"
echo "測試完成！"
echo ""
echo "如果看到上面有快照資料，表示功能正常。"
echo ""
echo "下一步："
echo "  1. 設定 cron job：bash setup_cron.sh"
echo "  2. 測試前端：開啟 HomeView 看「今日變動」"
echo "================================================"
