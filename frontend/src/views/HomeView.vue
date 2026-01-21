<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Plus, Upload, TrendingUp, TrendingDown, ArrowDownCircle, ArrowUpCircle, Eye } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'
import SummaryCard from '@/components/SummaryCard.vue'
import AddTransactionSheet from '@/components/AddTransactionSheet.vue'
import ImportCSVSheet from '@/components/ImportCSVSheet.vue'
import DepositSheet from '@/components/DepositSheet.vue'
import WithdrawSheet from '@/components/WithdrawSheet.vue'
import TransactionsDialog from '@/components/TransactionsDialog.vue'

const { t, locale } = useI18n()

// 使用 composable 的貨幣狀態
const { currentCurrency } = injectCurrency()

// 狀態管理
const portfolio = ref([])
const marketFilter = ref('all') // 'all', 'US', 'HK'
const summary = ref({
  total_invested: 0,
  current_cash: 0,
  current_cash_usd: 0,
  current_cash_hkd: 0,
  cash_balances: { USD: 0, HKD: 0 },
  total_market_value: 0,
  total_equity_hks: 0,
  total_assets: 0,
  net_liquidity: 0,  // 淨資產：總市值 + 總現金（真正擁有的錢）
  gross_position: 0,  // 總部位：做多市值 + 做空市值的絕對值（代表玩多大）
  net_profit: 0,
  roi_percentage: 0,
  exchange_rate: 7.8,
  usd_to_hkd_rate: 7.8  // 預設匯率（保持向後兼容）
})
const isLoading = ref(false)
const lastUpdated = ref(null)

// 抓取後端 FIFO 計算後的數據
const fetchData = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/dashboard/')
    portfolio.value = response.data.positions || []
    summary.value = {
      total_invested: response.data.summary?.total_invested || 0,
      current_cash: response.data.summary?.current_cash || 0,
      current_cash_usd: response.data.summary?.current_cash_usd || 0,
      current_cash_hkd: response.data.summary?.current_cash_hkd || 0,
      cash_balances: response.data.summary?.cash_balances || { USD: 0, HKD: 0 },
      total_market_value: response.data.summary?.total_market_value || 0,
      total_equity_hks: response.data.summary?.total_equity_hks || 0,
      total_assets: response.data.summary?.total_assets || 0,
      net_liquidity: response.data.summary?.net_liquidity || response.data.summary?.total_assets || 0,
      gross_position: response.data.summary?.gross_position || 0,
      net_profit: response.data.summary?.net_profit || 0,
      roi_percentage: response.data.summary?.roi_percentage || 0,
      exchange_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8,
      usd_to_hkd_rate: response.data.summary?.exchange_rate || response.data.summary?.usd_to_hkd_rate || 7.8
    }
    const localeString = locale.value === 'zh-HK' ? 'zh-HK' : 'en-US'
    lastUpdated.value = new Date().toLocaleTimeString(localeString, { hour: '2-digit', minute: '2-digit' })
  } catch (error) {
    console.error(t('messages.fetchError'), error)
  } finally {
    isLoading.value = false
  }
}

// 觸發後端 yfinance 更新股價
const refreshPrices = async () => {
  // 檢查是否有持倉
  if (portfolio.value.length === 0) {
    return
  }
  
  isLoading.value = true
  try {
    await api.post('/update-prices/')
    await fetchData() // 更新完價格後重新抓取數據
  } catch (error) {
    alert(t('messages.updateError'))
  } finally {
    isLoading.value = false
  }
}

// 計算頂部卡片數值
const totalMarketValue = computed(() => {
  return portfolio.value.reduce((sum, item) => sum + parseFloat(item.current_market_value || 0), 0)
})

const totalUnrealizedPL = computed(() => {
  return portfolio.value.reduce((sum, item) => sum + parseFloat(item.unrealized_pl || 0), 0)
})

const totalRealizedPL = computed(() => {
  return portfolio.value.reduce((sum, item) => sum + parseFloat(item.realized_pl || 0), 0)
})

const totalCost = computed(() => {
  return portfolio.value.reduce((sum, item) => sum + parseFloat((item.avg_cost || 0) * (item.quantity || 0)), 0)
})

const totalReturn = computed(() => {
  return totalUnrealizedPL.value + totalRealizedPL.value
})

const totalReturnPercent = computed(() => {
  // 使用後端計算的 ROI，如果有的話
  if (summary.value.roi_percentage !== undefined) {
    return summary.value.roi_percentage
  }
  // 否則使用舊的計算方式作為後備
  if (totalCost.value === 0) return 0
  return (totalReturn.value / totalCost.value) * 100
})

// 獲取匯率（優先使用 exchange_rate）
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

// 貨幣格式化函數（完整數字，不縮寫，使用 Intl.NumberFormat）
const formatCurrencyFull = (amount, originalCurrency = null) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const exchangeRate = getExchangeRate()
  
  // 如果指定了原始幣種，且與當前顯示幣種不同，需要轉換
  let displayAmount = numAmount
  if (originalCurrency && originalCurrency !== currentCurrency.value) {
    if (originalCurrency === 'USD' && currentCurrency.value === 'HKD') {
      displayAmount = numAmount * exchangeRate
    } else if (originalCurrency === 'HKD' && currentCurrency.value === 'USD') {
      displayAmount = numAmount / exchangeRate
    }
  } else if (!originalCurrency) {
    // 沒有指定原始幣種，假設是 USD，根據當前顯示幣種轉換
    if (currentCurrency.value === 'HKD') {
      displayAmount = numAmount * exchangeRate
    }
  }
  
  const currencySymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(displayAmount)
  return `${currencySymbol}${formatted}`
}

// 貨幣格式化函數（顯示原始幣種，不包含幣種標記）
const formatCurrency = (amount, originalCurrency = null, useAbbreviation = true) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    const currency = originalCurrency || 'USD'
    const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
    return currencySymbol + '0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const currency = originalCurrency || 'USD'
  const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
  
  // 如果金額很大，使用縮寫
  if (useAbbreviation && Math.abs(numAmount) >= 1000000000) {
    // 十億以上用 B
    return `${currencySymbol}${(numAmount / 1000000000).toFixed(2)}B`
  } else if (useAbbreviation && Math.abs(numAmount) >= 1000000) {
    // 百萬以上用 M
    return `${currencySymbol}${(numAmount / 1000000).toFixed(2)}M`
  } else if (useAbbreviation && Math.abs(numAmount) >= 1000) {
    // 千以上用 K
    return `${currencySymbol}${(numAmount / 1000).toFixed(2)}K`
  } else {
    // 小於一千，正常顯示
    return `${currencySymbol}${numAmount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
  }
}

// 格式化貨幣（主幣種大字，副幣種小字）
const formatCurrencyDual = (amount, originalCurrency = null) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return { main: currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00', sub: '' }
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const exchangeRate = getExchangeRate()
  
  // 確定原始幣種
  const sourceCurrency = originalCurrency || 'USD'
  
  // 計算主幣種（當前選擇的幣種）
  let mainAmount = numAmount
  if (sourceCurrency !== currentCurrency.value) {
    if (sourceCurrency === 'USD' && currentCurrency.value === 'HKD') {
      mainAmount = numAmount * exchangeRate
    } else if (sourceCurrency === 'HKD' && currentCurrency.value === 'USD') {
      mainAmount = numAmount / exchangeRate
    }
  }
  
  // 計算副幣種（另一個幣種）
  let subAmount = numAmount
  const subCurrency = currentCurrency.value === 'USD' ? 'HKD' : 'USD'
  if (sourceCurrency === currentCurrency.value) {
    if (currentCurrency.value === 'USD') {
      subAmount = numAmount * exchangeRate
    } else {
      subAmount = numAmount / exchangeRate
    }
  } else {
    subAmount = numAmount
  }
  
  const mainSymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  const subSymbol = subCurrency === 'HKD' ? 'HK$' : '$'
  
  return {
    main: `${mainSymbol}${new Intl.NumberFormat('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    }).format(mainAmount)}`,
    sub: `${subSymbol}${new Intl.NumberFormat('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    }).format(subAmount)}`
  }
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

const showAddModal = ref(false)
const showDepositModal = ref(false)
const showWithdrawModal = ref(false)
const showImportModal = ref(false)
const showTransactionsModal = ref(false)
const selectedSymbol = ref('')

// 處理組件成功事件
const handleTransactionSuccess = async () => {
  await refreshPrices()
}

const handleCashFlowSuccess = async () => {
  await fetchData()
}

const handleImportSuccess = async () => {
  await fetchData()
}

const handleTransactionsSuccess = async () => {
  await fetchData()
  await refreshPrices()
}

// 監聽來自 AddOptionsModal 的事件
const handleOpenAddTransaction = () => {
  showAddModal.value = true
}

const handleOpenDeposit = () => {
  showDepositModal.value = true
}

const handleOpenWithdraw = () => {
  showWithdrawModal.value = true
}

const handleOpenImport = () => {
  showImportModal.value = true
}

// 桌面版直接上傳 CSV（不使用 modal）
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post('/import-csv/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    await fetchData()
    alert(t('messages.importSuccess'))
  } catch (e) { 
    console.error(e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.uploadError')
    alert(`${t('messages.uploadError')}: ${errorMessage}`)
  }
}

const handleImportCSV = async (event) => {
  const file = event.detail?.file
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post('/import-csv/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    await fetchData()
    alert(t('messages.importSuccess'))
  } catch (e) { 
    console.error(e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.uploadError')
    alert(`${t('messages.uploadError')}: ${errorMessage}`)
  }
}

// 打開交易列表 modal
const openTransactionsModal = (symbol) => {
  selectedSymbol.value = symbol
  showTransactionsModal.value = true
}

// 監聽貨幣切換，觸發重新渲染（Vue 會自動響應式更新，這裡只是確保）
watch(currentCurrency, () => {
  // 貨幣切換時，Vue 的響應式系統會自動更新所有使用 currentCurrency 的計算屬性
  // 這裡可以添加額外的邏輯，如果需要
})


onMounted(() => {
  fetchData()
  
  // 監聽自定義事件
  window.addEventListener('openAddTransaction', handleOpenAddTransaction)
  window.addEventListener('openDeposit', handleOpenDeposit)
  window.addEventListener('openWithdraw', handleOpenWithdraw)
  window.addEventListener('openImport', handleOpenImport)
})

onUnmounted(() => {
  // 清理事件監聽器
  window.removeEventListener('openAddTransaction', handleOpenAddTransaction)
  window.removeEventListener('openDeposit', handleOpenDeposit)
  window.removeEventListener('openWithdraw', handleOpenWithdraw)
  window.removeEventListener('openImport', handleOpenImport)
  window.removeEventListener('importCSV', handleImportCSV)
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8 space-y-6 transition-all duration-300 ease-in-out">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 -mx-4 md:-mx-6 lg:-mx-8 px-4 md:px-6 lg:px-8">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 class="text-2xl sm:text-3xl font-bold tracking-tight">{{ t('dashboard.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">
              {{ t('dashboard.lastUpdated') }}: {{ lastUpdated || t('dashboard.notUpdated') }}
            </p>
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
            <!-- Desktop: Add Transaction, Deposit, Withdraw and Import CSV buttons -->
            <div class="hidden md:flex gap-2">
              <Button 
                @click="showAddModal = true"
                variant="default"
                size="default"
                class="min-h-[44px] active:scale-95"
              >
                <Plus class="h-4 w-4 mr-2" />
                {{ t('dashboard.addTransaction') }}
              </Button>
              <Button 
                @click="showDepositModal = true"
                variant="outline"
                size="default"
                class="min-h-[44px] active:scale-95"
              >
                <ArrowDownCircle class="h-4 w-4 mr-2" />
                {{ t('dashboard.depositFunds') }}
              </Button>
              <Button 
                @click="showWithdrawModal = true"
                variant="outline"
                size="default"
                class="min-h-[44px] active:scale-95"
              >
                <ArrowUpCircle class="h-4 w-4 mr-2" />
                {{ t('dashboard.withdrawFunds') }}
              </Button>
              <label class="cursor-pointer">
                <Button 
                  variant="outline" 
                  as="span"
                  size="default"
                  class="min-h-[44px] active:scale-95"
                >
                  <Upload class="h-4 w-4 mr-2" />
                  {{ t('dashboard.importCSV') }}
                </Button>
                <input 
                  type="file" 
                  class="hidden" 
                  @change="handleFileUpload" 
                  accept=".csv"
                />
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Dashboard Summary Card -->
      <SummaryCard 
        :summary="summary" 
        :exchange-rate="getExchangeRate()"
      />

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
                    <!-- 市值顯示原始幣種 -->
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
                <TableRow v-if="filteredPortfolio.length === 0">
                  <TableCell colspan="9" class="h-24 text-center text-muted-foreground">
                    {{ t('dashboard.noHoldings') }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>

          <!-- Mobile Card List View -->
          <div class="sm:hidden space-y-3">
            <Card 
              v-for="item in portfolio" 
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
            <div v-if="filteredPortfolio.length === 0" class="text-center py-8 text-muted-foreground">
              {{ t('dashboard.noHoldings') }}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />

    <!-- Add Transaction Sheet -->
    <AddTransactionSheet 
      v-model:open="showAddModal"
      @success="handleTransactionSuccess"
    />

    <!-- CSV Import Sheet -->
    <ImportCSVSheet 
      v-model:open="showImportModal"
      @success="handleImportSuccess"
    />

    <!-- Deposit Sheet -->
    <DepositSheet 
      v-model:open="showDepositModal"
      @success="handleCashFlowSuccess"
    />

    <!-- Withdraw Sheet -->
    <WithdrawSheet 
      v-model:open="showWithdrawModal"
      @success="handleCashFlowSuccess"
    />

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
.container {
  max-width: 1400px;
}

.safe-area-bottom {
  padding-bottom: calc(env(safe-area-inset-bottom) + 0.5rem);
}

@media (min-width: 768px) {
  .safe-area-bottom {
    padding-bottom: 0;
  }
}

/* Hide scrollbar for horizontal scroll on mobile */
.overflow-x-auto {
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.overflow-x-auto::-webkit-scrollbar {
  display: none;
}
</style>
