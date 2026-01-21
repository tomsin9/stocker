<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-vue-next'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'
import api from '@/api'
import { cn } from '@/lib/utils'

const { t } = useI18n()
const router = useRouter()
const { currentCurrency } = injectCurrency()

const portfolio = ref([])
const isLoading = ref(false)
const summary = ref({
  exchange_rate: 7.8,
  usd_to_hkd_rate: 7.8
})

const fetchAssets = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/dashboard/')
    portfolio.value = response.data.positions || []
    summary.value = {
      exchange_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8,
      usd_to_hkd_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8
    }
  } catch (error) {
    console.error('Failed to fetch assets', error)
  } finally {
    isLoading.value = false
  }
}

// 獲取匯率
const getExchangeRate = () => {
  return summary.value.exchange_rate || summary.value.usd_to_hkd_rate || 7.8
}

// 將 USD 金額轉換為原始幣種（後端返回的 avg_cost 和 current_market_value 都是 USD）
const convertFromUsd = (usdAmount, targetCurrency) => {
  if (!targetCurrency || targetCurrency === 'USD') {
    return usdAmount
  }
  const exchangeRate = getExchangeRate()
  if (targetCurrency === 'HKD') {
    return usdAmount * exchangeRate
  }
  return usdAmount
}

// 貨幣格式化函數（顯示原始幣種，不包含幣種標記）
const formatCurrency = (amount, originalCurrency = null) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    const currency = originalCurrency || 'USD'
    const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
    return currencySymbol + '0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const currency = originalCurrency || 'USD'
  const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
  
  return `${currencySymbol}${Math.abs(numAmount).toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

// 判斷股票市場（港股或美股）
const getMarketType = (symbol) => {
  if (!symbol) return 'US'
  return symbol.includes('.HK') || /^\d{4}$/.test(symbol) ? 'HK' : 'US'
}

// 獲取市場顏色
const getMarketColor = (symbol) => {
  const market = getMarketType(symbol)
  return market === 'HK' 
    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 border-blue-300 dark:border-blue-700'
    : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700'
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchAssets()
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 mb-4 -mx-4 md:-mx-6 lg:-mx-8 px-4 md:px-6 lg:px-8">
        <div class="flex items-center gap-3 mb-2">
          <Button 
            variant="ghost" 
            size="icon"
            @click="goBack"
            class="md:hidden min-h-[44px] min-w-[44px] active:scale-95"
          >
            <ArrowLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold tracking-tight">{{ t('assets.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">{{ t('assets.description') }}</p>
          </div>
        </div>
      </div>

      <!-- Assets List -->
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="portfolio.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('assets.noAssets') }}
      </div>
      <div v-else class="space-y-3">
        <Card 
          v-for="item in portfolio" 
          :key="item.symbol"
          class="active:scale-[0.98] transition-transform"
        >
          <CardContent class="p-4">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-semibold text-lg">{{ item.symbol }}</span>
                  <!-- 市場標籤 -->
                  <span 
                    :class="cn(
                      'px-1 py-0 rounded text-[10px] font-medium border',
                      getMarketColor(item.symbol)
                    )"
                  >
                    {{ getMarketType(item.symbol) === 'HK' ? 'HK' : 'US' }}
                  </span>
                  <!-- 賣空標籤 -->
                  <span 
                    v-if="item.quantity < 0"
                    class="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 border border-purple-300 dark:border-purple-700"
                  >
                    SHORT
                  </span>
                </div>
                <div 
                  :class="[
                    'text-sm',
                    item.quantity < 0 ? 'text-purple-600 dark:text-purple-400 font-medium' : 'text-muted-foreground'
                  ]"
                >
                  {{ t('dashboard.quantity') }}: {{ parseFloat(item.quantity || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }}
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ t('dashboard.avgCost') }}: {{ formatCurrency(convertFromUsd(item.avg_cost || 0, item.currency), item.currency) }}
                  <span class="text-xs text-muted-foreground font-medium ml-1">{{ item.currency || 'USD' }}</span>
                </div>
              </div>
              <div class="text-right">
                <!-- 市值顯示原始幣種 -->
                <div 
                  :class="[
                    'font-semibold text-lg',
                    item.quantity < 0 ? 'text-purple-600 dark:text-purple-400' : ''
                  ]"
                >
                  {{ formatCurrency(convertFromUsd(item.current_market_value || 0, item.currency), item.currency) }}
                </div>
                <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                <div 
                  :class="[
                    'text-sm font-medium mt-1',
                    item.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
                  ]"
                >
                  {{ item.unrealized_pl >= 0 ? '+' : '' }}{{ formatCurrency(convertFromUsd(Math.abs(item.unrealized_pl || 0), item.currency), item.currency) }}
                </div>
                <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />
  </div>
</template>

<style scoped>
.safe-area-bottom {
  padding-bottom: calc(env(safe-area-inset-bottom) + 0.5rem);
}

@media (min-width: 768px) {
  .safe-area-bottom {
    padding-bottom: 0;
  }
}
</style>
