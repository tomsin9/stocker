from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Asset
from .services import calculate_position
from .serializers import PortfolioSummarySerializer

class PortfolioDashboardView(APIView):
    def get(self, request):
        assets = Asset.objects.all()
        data = []
        
        for asset in assets:
            # 呼叫我們的 FIFO 計算邏輯
            stats = calculate_position(asset)
            
            # 只回傳目前還有持倉，或者曾經有賺賠紀錄的
            if stats['quantity'] > 0 or stats['realized_pl'] != 0:
                data.append(stats)
        
        # 序列化並回傳
        serializer = PortfolioSummarySerializer(data, many=True)
        return Response(serializer.data)