<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Plus, Upload, TrendingUp, TrendingDown, DollarSign, Package, Wallet, PiggyBank } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'

const { t, locale } = useI18n()

// 使用 composable 的貨幣狀態
const { currentCurrency } = injectCurrency()

// 狀態管理
const portfolio = ref([])
const summary = ref({
  total_invested: 0,
  current_cash: 0,
  total_market_value: 0,
  total_assets: 0,
  net_profit: 0,
  roi_percentage: 0,
  usd_to_hkd_rate: 7.8  // 預設匯率
})
const isLoading = ref(false)
const lastUpdated = ref(null)

// API 連線設定
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

// 抓取後端 FIFO 計算後的數據
const fetchData = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`${API_BASE}/dashboard/`)
    portfolio.value = response.data.positions || []
    summary.value = {
      total_invested: response.data.summary?.total_invested || 0,
      current_cash: response.data.summary?.current_cash || 0,
      total_market_value: response.data.summary?.total_market_value || 0,
      total_assets: response.data.summary?.total_assets || 0,
      net_profit: response.data.summary?.net_profit || 0,
      roi_percentage: response.data.summary?.roi_percentage || 0,
      usd_to_hkd_rate: response.data.summary?.usd_to_hkd_rate || 7.8
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
    await axios.post(`${API_BASE}/update-prices/`)
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

// 貨幣格式化函數（完整數字，不縮寫）
const formatCurrencyFull = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  
  // 如果當前貨幣是 HKD，將 USD 金額轉換為 HKD
  let displayAmount = numAmount
  if (currentCurrency.value === 'HKD') {
    displayAmount = numAmount * (summary.value.usd_to_hkd_rate || 7.8)
  }
  
  const currencySymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  return `${currencySymbol}${displayAmount.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

// 貨幣格式化函數（支持大數字縮寫）
const formatCurrency = (amount, useAbbreviation = true) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  
  // 如果當前貨幣是 HKD，將 USD 金額轉換為 HKD
  let displayAmount = numAmount
  if (currentCurrency.value === 'HKD') {
    displayAmount = numAmount * (summary.value.usd_to_hkd_rate || 7.8)
  }
  
  const currencySymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  
  // 如果金額很大，使用縮寫
  if (useAbbreviation && Math.abs(displayAmount) >= 1000000000) {
    // 十億以上用 B
    return `${currencySymbol}${(displayAmount / 1000000000).toFixed(2)}B`
  } else if (useAbbreviation && Math.abs(displayAmount) >= 1000000) {
    // 百萬以上用 M
    return `${currencySymbol}${(displayAmount / 1000000).toFixed(2)}M`
  } else if (useAbbreviation && Math.abs(displayAmount) >= 1000) {
    // 千以上用 K
    return `${currencySymbol}${(displayAmount / 1000).toFixed(2)}K`
  } else {
    // 小於一千，正常顯示
    return `${currencySymbol}${displayAmount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
  }
}


const showAddModal = ref(false)
const showDepositModal = ref(false)
const showWithdrawModal = ref(false)
const showImportModal = ref(false)
const newTrade = ref({
  symbol: '',
  action: 'BUY',
  date: new Date().toISOString().split('T')[0],
  price: 0,
  quantity: 0,
  fees: 0
})
const newCashFlow = ref({
  amount: 0,
  type: 'DEPOSIT',
  date: new Date().toISOString().split('T')[0],
  notes: ''
})

const submitTrade = async () => {
  try {
    await axios.post(`${API_BASE}/add-transaction/`, newTrade.value)
    showAddModal.value = false
    // 重置表單
    newTrade.value = {
      symbol: '',
      action: 'BUY',
      date: new Date().toISOString().split('T')[0],
      price: 0,
      quantity: 0,
      fees: 0
    }
    await fetchData() // 刷新列表
  } catch (e) { 
    console.error('Save transaction error:', e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.saveError')
    alert(`${t('messages.saveError')}: ${errorMessage}`)
  }
}

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const formData = new FormData()
  formData.append('file', file)
  try {
    await axios.post(`${API_BASE}/import-csv/`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    showImportModal.value = false
    await fetchData()
    alert(t('messages.importSuccess'))
  } catch (e) { 
    console.error(e)
    alert(t('messages.uploadError'))
  }
}

const submitCashFlow = async (type) => {
  try {
    const data = {
      ...newCashFlow.value,
      type: type
    }
    await axios.post(`${API_BASE}/cashflow/`, data)
    if (type === 'DEPOSIT') {
      showDepositModal.value = false
    } else {
      showWithdrawModal.value = false
    }
    // 重置表單
    newCashFlow.value = {
      amount: 0,
      type: 'DEPOSIT',
      date: new Date().toISOString().split('T')[0],
      notes: ''
    }
    await fetchData() // 刷新數據
  } catch (e) {
    console.error('Save cashflow error:', e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.saveError')
    alert(`${t('messages.saveError')}: ${errorMessage}`)
  }
}

onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8 space-y-6">
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
            <!-- Desktop: Add Transaction and Import CSV buttons -->
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

      <!-- Stats Cards - Horizontal Scroll on Mobile -->
      <div class="overflow-x-auto -mx-4 md:mx-0 px-4 md:px-0">
        <div class="flex md:grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 min-w-max md:min-w-0">
          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.totalInvested') }}</CardTitle>
              <PiggyBank class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <div 
                class="text-xl sm:text-2xl font-bold break-words leading-tight cursor-help" 
                :title="formatCurrencyFull(summary.total_invested || 0)"
              >
                {{ formatCurrency(summary.total_invested || 0) }}
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.totalInvested') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.availableCash') }}</CardTitle>
              <Wallet class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <div 
                class="text-xl sm:text-2xl font-bold break-words leading-tight cursor-help" 
                :title="formatCurrencyFull(summary.current_cash || 0)"
              >
                {{ formatCurrency(summary.current_cash || 0) }}
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.availableCash') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.totalMarketValue') }}</CardTitle>
              <DollarSign class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <div 
                class="text-xl sm:text-2xl font-bold break-words leading-tight cursor-help" 
                :title="formatCurrencyFull(summary.total_market_value || 0)"
              >
                {{ formatCurrency(summary.total_market_value || 0) }}
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ currentCurrency === 'USD' ? 'USD' : 'HKD' }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.totalAssets') }}</CardTitle>
              <Package class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <div 
                class="text-xl sm:text-2xl font-bold break-words leading-tight cursor-help" 
                :title="formatCurrencyFull(summary.total_assets || 0)"
              >
                {{ formatCurrency(summary.total_assets || 0) }}
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.totalAssets') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.netProfit') }}</CardTitle>
              <TrendingUp 
                v-if="(summary.net_profit || 0) >= 0" 
                class="h-4 w-4 text-green-600 flex-shrink-0" 
              />
              <TrendingDown 
                v-else 
                class="h-4 w-4 text-red-600 flex-shrink-0" 
              />
            </CardHeader>
            <CardContent>
              <div 
                :class="cn(
                  'text-xl sm:text-2xl font-bold break-words leading-tight cursor-help',
                  (summary.net_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                )"
                :title="(summary.net_profit || 0) >= 0 ? '+' : '' + formatCurrencyFull(Math.abs(summary.net_profit || 0))"
              >
                {{ (summary.net_profit || 0) >= 0 ? '+' : '' }}{{ formatCurrency(Math.abs(summary.net_profit || 0)) }}
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.netProfit') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.totalReturnPercent') }}</CardTitle>
              <TrendingUp 
                v-if="totalReturnPercent >= 0" 
                class="h-4 w-4 text-green-600 flex-shrink-0" 
              />
              <TrendingDown 
                v-else 
                class="h-4 w-4 text-red-600 flex-shrink-0" 
              />
            </CardHeader>
            <CardContent>
              <div 
                :class="cn(
                  'text-xl sm:text-2xl font-bold break-words leading-tight',
                  totalReturnPercent >= 0 ? 'text-green-600' : 'text-red-600'
                )"
              >
                {{ totalReturnPercent >= 0 ? '+' : '' }}{{ totalReturnPercent.toFixed(2) }}%
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.totalReturn') }}</p>
            </CardContent>
          </Card>
        </div>
      </div>

      <!-- Portfolio Holdings -->
      <Card>
        <CardHeader>
          <CardTitle>{{ t('dashboard.holdings') }}</CardTitle>
          <CardDescription>{{ t('dashboard.holdingsDescription') }}</CardDescription>
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
                  <TableHead class="text-right">{{ t('dashboard.unrealizedPLShort') }}</TableHead>
                  <TableHead class="text-right">{{ t('dashboard.returnRate') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow 
                  v-for="item in portfolio" 
                  :key="item.symbol"
                  class="hover:bg-muted/50"
                >
                  <TableCell class="font-medium">
                    <div class="font-semibold">{{ item.symbol }}</div>
                    <div class="text-xs text-muted-foreground">{{ t('dashboard.fifoInventory') }}</div>
                  </TableCell>
                  <TableCell class="text-right font-medium">
                    {{ item.quantity?.toLocaleString() || 0 }}
                  </TableCell>
                  <TableCell class="text-right">
                    {{ formatCurrency(item.avg_cost || 0) }}
                  </TableCell>
                  <TableCell class="text-right font-semibold">
                    {{ item.quantity > 0 ? formatCurrency((item.current_market_value || 0) / item.quantity) : formatCurrency(0) }}
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      :class="cn(
                        'font-semibold',
                        item.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
                      )"
                    >
                      {{ item.unrealized_pl >= 0 ? '+' : '' }}{{ formatCurrency(Math.abs(item.unrealized_pl || 0)) }}
                    </div>
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
                      {{ item.quantity > 0 && item.avg_cost > 0 
                        ? ((item.unrealized_pl / (item.avg_cost * item.quantity)) * 100).toFixed(2) 
                        : '0.00' }}%
                    </div>
                  </TableCell>
                </TableRow>
                <TableRow v-if="portfolio.length === 0">
                  <TableCell colspan="6" class="h-24 text-center text-muted-foreground">
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
                  <div class="font-semibold text-lg">{{ item.symbol }}</div>
                  <!-- Top Right: Current Price -->
                  <div class="text-right font-semibold">
                    {{ item.quantity > 0 ? formatCurrency((item.current_market_value || 0) / item.quantity) : formatCurrency(0) }}
                  </div>
                  <!-- Bottom Left: Quantity -->
                  <div class="text-sm text-muted-foreground">
                    {{ t('dashboard.quantity') }}: {{ item.quantity?.toLocaleString() || 0 }}
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
                      {{ item.quantity > 0 && item.avg_cost > 0 
                        ? ((item.unrealized_pl / (item.avg_cost * item.quantity)) * 100).toFixed(2) 
                        : '0.00' }}%
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            <div v-if="portfolio.length === 0" class="text-center py-8 text-muted-foreground">
              {{ t('dashboard.noHoldings') }}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation :on-add-click="() => showAddModal = true" />

    <!-- Add Transaction Sheet -->
    <Sheet v-model:open="showAddModal">
      <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{{ t('transaction.title') }}</SheetTitle>
          <SheetDescription>
            {{ t('transaction.description') }}
          </SheetDescription>
        </SheetHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.symbol') }}</label>
            <Input 
              v-model="newTrade.symbol" 
              :placeholder="t('transaction.symbolPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.type') }}</label>
            <Select v-model="newTrade.action" class="min-h-[44px]">
              <option value="BUY">{{ t('transaction.buy') }}</option>
              <option value="SELL">{{ t('transaction.sell') }}</option>
            </Select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">{{ t('transaction.price') }}</label>
              <Input 
                v-model.number="newTrade.price" 
                type="number" 
                step="0.01"
                :placeholder="t('transaction.pricePlaceholder')"
                class="min-h-[44px]"
              />
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">{{ t('transaction.quantity') }}</label>
              <Input 
                v-model.number="newTrade.quantity" 
                type="number"
                :placeholder="t('transaction.quantityPlaceholder')"
                class="min-h-[44px]"
              />
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.date') }}</label>
            <Input 
              v-model="newTrade.date" 
              type="date"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.fees') }}</label>
            <Input 
              v-model.number="newTrade.fees" 
              type="number"
              step="0.01"
              :placeholder="t('transaction.feesPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
        </div>
        <SheetFooter>
          <Button variant="outline" @click="showAddModal = false" class="min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button>
          <Button @click="submitTrade" class="min-h-[44px] active:scale-95">{{ t('common.save') }}</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>

    <!-- CSV Import Sheet -->
    <Sheet v-model:open="showImportModal">
      <SheetContent side="bottom">
        <SheetHeader>
          <SheetTitle>{{ t('dashboard.importCSV') }}</SheetTitle>
          <SheetDescription>
            {{ t('dashboard.importCSVDescription') }}
          </SheetDescription>
        </SheetHeader>
        <div class="py-4">
          <label class="cursor-pointer block">
            <Button variant="outline" as="span" class="w-full min-h-[44px] active:scale-95">
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
      </SheetContent>
    </Sheet>

    <!-- Deposit Sheet -->
    <Sheet v-model:open="showDepositModal">
      <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{{ t('cashflow.depositTitle') }}</SheetTitle>
          <SheetDescription>
            {{ t('cashflow.depositDescription') }}
          </SheetDescription>
        </SheetHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.amount') }}</label>
            <Input 
              v-model.number="newCashFlow.amount" 
              type="number" 
              step="0.01"
              :placeholder="t('cashflow.amountPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.date') }}</label>
            <Input 
              v-model="newCashFlow.date" 
              type="date"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.notes') }}</label>
            <Input 
              v-model="newCashFlow.notes" 
              :placeholder="t('cashflow.notesPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
        </div>
        <SheetFooter>
          <Button variant="outline" @click="showDepositModal = false" class="min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button>
          <Button @click="submitCashFlow('DEPOSIT')" class="min-h-[44px] active:scale-95">{{ t('common.save') }}</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>

    <!-- Withdraw Sheet -->
    <Sheet v-model:open="showWithdrawModal">
      <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{{ t('cashflow.withdrawTitle') }}</SheetTitle>
          <SheetDescription>
            {{ t('cashflow.withdrawDescription') }}
          </SheetDescription>
        </SheetHeader>
        <div class="grid gap-4 py-4">
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.amount') }}</label>
            <Input 
              v-model.number="newCashFlow.amount" 
              type="number" 
              step="0.01"
              :placeholder="t('cashflow.amountPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.date') }}</label>
            <Input 
              v-model="newCashFlow.date" 
              type="date"
              class="min-h-[44px]"
            />
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('cashflow.notes') }}</label>
            <Input 
              v-model="newCashFlow.notes" 
              :placeholder="t('cashflow.notesPlaceholder')"
              class="min-h-[44px]"
            />
          </div>
        </div>
        <SheetFooter>
          <Button variant="outline" @click="showWithdrawModal = false" class="min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button>
          <Button @click="submitCashFlow('WITHDRAW')" class="min-h-[44px] active:scale-95">{{ t('common.save') }}</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  </div>
</template>

<style scoped>
.container {
  max-width: 1400px;
}

.safe-area-bottom {
  padding-bottom: calc(env(safe-area-inset-bottom) + 4rem);
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
