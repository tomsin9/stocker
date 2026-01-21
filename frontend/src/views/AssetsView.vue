<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowLeft, RefreshCw, TrendingUp, TrendingDown, Eye } from 'lucide-vue-next'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'
import TransactionsDialog from '@/components/TransactionsDialog.vue'
import AssetAllocationChart from '@/components/charts/AssetAllocationChart.vue'
import StockPerformanceChart from '@/components/charts/StockPerformanceChart.vue'
import api from '@/api'
import { cn } from '@/lib/utils'

const { t } = useI18n()
const router = useRouter()
const { currentCurrency } = injectCurrency()

const portfolio = ref([])
const marketFilter = ref('all') // 'all', 'US', 'HK'
const isLoading = ref(false)
const summary = ref({
  exchange_rate: 7.8,
  usd_to_hkd_rate: 7.8
})
const showTransactionsModal = ref(false)
const selectedSymbol = ref('')
const activeChartTab = ref('allocation') // 'allocation', 'performance'
const loadedCharts = ref(new Set(['allocation'])) // 追蹤已載入的圖表

const fetchAssets = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/dashboard/')
    portfolio.value = response.data.positions || []
    summary.value = {
      exchange_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8,
      usd_to_hkd_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8,
      current_cash: response.data.summary?.current_cash || response.data.summary?.current_cash_total || 0
    }
  } catch (error) {
    console.error('Failed to fetch assets', error)
  } finally {
    isLoading.value = false
  }
}

// 觸發後端 yfinance 更新股價
const refreshPrices = async () => {
  if (portfolio.value.length === 0) {
    return
  }
  
  isLoading.value = true
  try {
    await api.post('/update-prices/')
    await fetchAssets()
  } catch (error) {
    alert(t('messages.updateError'))
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

// 過濾持倉列表
const filteredPortfolio = computed(() => {
  if (marketFilter.value === 'all') {
    return portfolio.value
  }
  return portfolio.value.filter(item => {
    const market = getMarketType(item.symbol)
    return market === marketFilter.value
  })
})

// 打開交易列表 modal
const openTransactionsModal = (symbol) => {
  selectedSymbol.value = symbol
  showTransactionsModal.value = true
}

// 切換圖表 tab
const switchChartTab = (tab) => {
  activeChartTab.value = tab
  loadedCharts.value.add(tab) // 標記為已載入
}

// 處理交易成功事件
const handleTransactionsSuccess = async () => {
  await fetchAssets()
  await refreshPrices()
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
    <div class="container mx-auto p-4 md:p-6 lg:p-8 space-y-6">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 -mx-4 md:-mx-6 lg:-mx-8 px-4 md:px-6 lg:px-8">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div class="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="icon"
              @click="goBack"
              class="md:hidden min-h-[44px] min-w-[44px] active:scale-95"
            >
              <ArrowLeft class="h-5 w-5" />
            </Button>
            <div>
              <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">{{ t('assets.title') }}</h1>
              <p class="text-sm text-muted-foreground mt-1">{{ t('assets.description') }}</p>
            </div>
          </div>
          <div class="flex gap-2">
            <Button 
              @click="refreshPrices" 
              :disabled="isLoading"
              variant="outline"
              size="default"
              class="min-h-[44px] active:scale-95"
            >
              <RefreshCw :class="cn('h-4 w-4', isLoading && 'animate-spin')" />
              <span class="hidden sm:inline">{{ isLoading ? t('dashboard.refreshing') : t('dashboard.refreshPrices') }}</span>
            </Button>
          </div>
        </div>
      </div>

      <!-- Charts Section with Tabs -->
      <Card>
        <CardHeader>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>{{ t('assets.charts') }}</CardTitle>
              <CardDescription>{{ t('assets.chartsDescription') }}</CardDescription>
            </div>
            <!-- Chart Tabs -->
            <div class="inline-flex items-center gap-1 bg-muted p-1 rounded-lg">
              <button
                @click="switchChartTab('allocation')"
                :class="cn(
                  'px-4 py-2 text-sm font-medium rounded-md transition-all',
                  activeChartTab === 'allocation'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                )"
              >
                {{ t('assets.allocationTab') }}
              </button>
              <button
                @click="switchChartTab('performance')"
                :class="cn(
                  'px-4 py-2 text-sm font-medium rounded-md transition-all',
                  activeChartTab === 'performance'
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground hover:bg-background/50'
                )"
              >
                {{ t('assets.performanceTab') }}
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <!-- Asset Allocation Chart -->
          <div v-if="activeChartTab === 'allocation'">
            <AssetAllocationChart 
              v-if="loadedCharts.has('allocation')"
              :portfolio="filteredPortfolio"
              :exchange-rate="getExchangeRate()"
              :cash="summary.current_cash || 0"
            />
          </div>

          <!-- Stock Performance Chart -->
          <div v-if="activeChartTab === 'performance'">
            <StockPerformanceChart 
              v-if="loadedCharts.has('performance')"
              :key="`performance-${marketFilter}-${filteredPortfolio.length}`"
              :portfolio="filteredPortfolio"
              :exchange-rate="getExchangeRate()"
              :market-filter="marketFilter"
            />
          </div>
        </CardContent>
      </Card>

      <!-- Portfolio Holdings -->
      <Card>
        <CardHeader>
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>{{ t('dashboard.holdings') }}</CardTitle>
              <CardDescription>{{ t('dashboard.holdingsDescription') }}</CardDescription>
            </div>
            <!-- Market Filter -->
            <div class="flex items-center gap-2">
              <Button
                :variant="marketFilter === 'all' ? 'default' : 'outline'"
                size="sm"
                @click="marketFilter = 'all'"
                class="min-w-[60px]"
              >
                {{ t('dashboard.filterAll') }}
              </Button>
              <Button
                :variant="marketFilter === 'US' ? 'default' : 'outline'"
                size="sm"
                @click="marketFilter = 'US'"
                class="min-w-[60px]"
              >
                {{ t('dashboard.filterUS') }}
              </Button>
              <Button
                :variant="marketFilter === 'HK' ? 'default' : 'outline'"
                size="sm"
                @click="marketFilter = 'HK'"
                class="min-w-[60px]"
              >
                {{ t('dashboard.filterHK') }}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <!-- Loading State -->
          <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
            {{ t('common.loading') }}
          </div>
          <!-- Empty State -->
          <div v-else-if="filteredPortfolio.length === 0" class="text-center py-8 text-muted-foreground">
            {{ t('dashboard.noHoldings') }}
          </div>
          <!-- Desktop Table View and Mobile Card List View -->
          <template v-else>
            <!-- Desktop Table View -->
            <div class="hidden sm:block rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead class="w-[200px]">{{ t('dashboard.symbol') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.quantity') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.avgCost') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.currentPrice') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.totalCost') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.totalMarketValue') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.unrealizedPLShort') }}</TableHead>
                    <TableHead class="text-right">{{ t('dashboard.returnRate') }}</TableHead>
                    <TableHead class="text-center w-[100px]">{{ t('common.actions') }}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow 
                    v-for="item in filteredPortfolio" 
                    :key="item.symbol"
                    class="hover:bg-muted/50"
                  >
                    <TableCell class="font-medium">
                      <div class="flex items-center gap-2">
                        <span 
                          :class="[
                            'font-semibold',
                            item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                          ]"
                        >
                          {{ item.symbol }}
                        </span>
                        <span 
                          :class="cn(
                            'px-1 py-0 rounded text-[10px] font-medium border',
                            getMarketColor(item.symbol)
                          )"
                        >
                          {{ getMarketType(item.symbol) === 'HK' ? 'HK' : 'US' }}
                        </span>
                        <!-- SHORT Badge -->
                        <span 
                          v-if="item.quantity < 0"
                          class="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 border border-purple-300 dark:border-purple-700"
                        >
                          {{ t('dashboard.short') }}
                        </span>
                      </div>
                      <div v-if="item.name" class="text-xs text-muted-foreground mt-0.5">
                        {{ item.name }}
                      </div>
                    </TableCell>
                    <TableCell 
                      :class="[
                        'text-right font-medium',
                        item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                      ]"
                    >
                      {{ parseFloat(item.quantity || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }}
                    </TableCell>
                    <TableCell class="text-right">
                      <div>{{ formatCurrency(convertFromUsd(item.avg_cost || 0, item.currency), item.currency) }}</div>
                      <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                    </TableCell>
                    <TableCell class="text-right font-semibold">
                      <div>{{ item.quantity !== 0 ? formatCurrency(convertFromUsd((item.current_market_value || 0) / Math.abs(item.quantity), item.currency), item.currency) : formatCurrency(0, item.currency) }}</div>
                      <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                    </TableCell>
                    <TableCell class="text-right">
                      <div>{{ formatCurrency(convertFromUsd((item.avg_cost || 0) * (item.quantity || 0), item.currency), item.currency) }}</div>
                      <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                    </TableCell>
                    <TableCell 
                      :class="[
                        'text-right font-semibold',
                        item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                      ]"
                    >
                      <div>{{ formatCurrency(convertFromUsd(item.current_market_value || 0, item.currency), item.currency) }}</div>
                      <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                    </TableCell>
                    <TableCell class="text-right">
                      <div 
                        :class="cn(
                          'font-semibold',
                          item.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
                        )"
                      >
                        {{ item.unrealized_pl >= 0 ? '+' : '' }}{{ formatCurrency(convertFromUsd(Math.abs(item.unrealized_pl || 0), item.currency), item.currency) }}
                      </div>
                      <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                    </TableCell>
                    <TableCell class="text-right">
                      <div 
                        :class="cn(
                          'inline-flex items-center gap-1 px-2 py-1 rounded-md text-sm font-semibold',
                          item.unrealized_pl >= 0 
                            ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400' 
                            : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400'
                        )"
                      >
                        <TrendingUp v-if="item.unrealized_pl >= 0" class="h-3 w-3" />
                        <TrendingDown v-else class="h-3 w-3" />
                        {{ item.quantity !== 0 && item.avg_cost > 0 
                          ? ((item.unrealized_pl / (item.avg_cost * Math.abs(item.quantity))) * 100).toFixed(2) 
                          : '0.00' }}%
                      </div>
                    </TableCell>
                    <TableCell class="text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        @click="openTransactionsModal(item.symbol)"
                        class="min-h-[32px] min-w-[32px] p-0"
                      >
                        <Eye class="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>

            <!-- Mobile Card List View -->
            <div class="sm:hidden space-y-3">
            <Card 
              v-for="item in filteredPortfolio" 
              :key="item.symbol"
              class="active:scale-[0.98] transition-transform"
            >
              <CardContent class="p-4">
                <div class="grid grid-cols-2 gap-2">
                  <!-- Top Left: Ticker -->
                  <div class="flex flex-col gap-1">
                    <div class="flex items-center gap-2">
                      <span 
                        :class="[
                          'font-semibold text-lg',
                          item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                        ]"
                      >
                        {{ item.symbol }}
                      </span>
                      <span 
                        :class="cn(
                          'px-1 py-0 rounded text-[10px] font-medium border',
                          getMarketColor(item.symbol)
                        )"
                      >
                        {{ getMarketType(item.symbol) === 'HK' ? 'HK' : 'US' }}
                      </span>
                      <!-- SHORT Badge -->
                      <span 
                        v-if="item.quantity < 0"
                        class="px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 border border-purple-300 dark:border-purple-700"
                      >
                        {{ t('dashboard.short') }}
                      </span>
                    </div>
                    <div v-if="item.name" class="text-xs text-muted-foreground">
                      {{ item.name }}
                    </div>
                  </div>
                  <!-- Top Right: Current Price -->
                  <div class="text-right">
                    <div 
                      :class="[
                        'font-semibold',
                        item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                      ]"
                    >
                      {{ item.quantity !== 0 ? formatCurrency(convertFromUsd((item.current_market_value || 0) / Math.abs(item.quantity), item.currency), item.currency) : formatCurrency(0, item.currency) }}
                    </div>
                    <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                  </div>
                  <!-- Bottom Left: Quantity -->
                  <div 
                    :class="[
                      'text-sm',
                      item.quantity < 0 ? 'text-purple-500 dark:text-purple-400 font-medium' : 'text-muted-foreground'
                    ]"
                  >
                    {{ t('dashboard.quantity') }}: {{ parseFloat(item.quantity || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }}
                  </div>
                  <!-- Bottom Right: Return % with background -->
                  <div class="text-right">
                    <div 
                      :class="cn(
                        'inline-flex items-center gap-1 px-2 py-1 rounded-md text-sm font-semibold',
                        item.unrealized_pl >= 0 
                          ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-400' 
                          : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-400'
                      )"
                    >
                      <TrendingUp v-if="item.unrealized_pl >= 0" class="h-3 w-3" />
                      <TrendingDown v-else class="h-3 w-3" />
                      {{ item.quantity !== 0 && item.avg_cost > 0 
                        ? ((item.unrealized_pl / (item.avg_cost * Math.abs(item.quantity))) * 100).toFixed(2) 
                        : '0.00' }}%
                    </div>
                  </div>
                </div>
                <!-- Market Value Row (Mobile) -->
                <div class="mt-3 pt-3 border-t grid grid-cols-2 gap-2">
                  <div class="text-sm text-muted-foreground">
                    {{ t('dashboard.totalMarketValue') }}:
                  </div>
                  <div class="text-right">
                    <div 
                      :class="[
                        'text-sm font-semibold',
                        item.quantity < 0 ? 'text-purple-500 dark:text-purple-400' : ''
                      ]"
                    >
                      {{ formatCurrency(convertFromUsd(item.current_market_value || 0, item.currency), item.currency) }}
                    </div>
                    <div class="text-xs text-muted-foreground font-medium">{{ item.currency || 'USD' }}</div>
                  </div>
                </div>
                <div class="mt-3 pt-3 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    @click="openTransactionsModal(item.symbol)"
                    class="w-full min-h-[36px]"
                  >
                    <Eye class="h-4 w-4 mr-2" />
                    {{ t('transaction.viewTransactions') }}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
          </template>
        </CardContent>
      </Card>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />

    <!-- Transactions Dialog -->
    <TransactionsDialog 
      v-model:open="showTransactionsModal"
      :symbol="selectedSymbol"
      :exchange-rate="getExchangeRate()"
      @success="handleTransactionsSuccess"
    />
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
