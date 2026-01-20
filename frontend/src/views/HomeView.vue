<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { RefreshCw, Plus, Upload, TrendingUp, TrendingDown, DollarSign, Package, Wallet, PiggyBank, ArrowDownCircle, ArrowUpCircle, Trash2, Eye, Flag } from 'lucide-vue-next'
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

// 貨幣格式化函數（完整數字，不縮寫）
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
  return `${currencySymbol}${displayAmount.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

// 貨幣格式化函數（支持大數字縮寫）
const formatCurrency = (amount, originalCurrency = null, useAbbreviation = true) => {
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
    main: `${mainSymbol}${mainAmount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`,
    sub: `${subSymbol}${subAmount.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
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


const showAddModal = ref(false)
const showDepositModal = ref(false)
const showWithdrawModal = ref(false)
const showImportModal = ref(false)
const showTransactionsModal = ref(false)
const selectedSymbol = ref('')
const symbolTransactions = ref([])
const isLoadingTransactions = ref(false)
const newTrade = ref({
  symbol: '',
  action: 'BUY',
  date: new Date().toISOString().split('T')[0],
  price: 0,
  quantity: 0,
  fees: 0
})
// Auto-complete 相關狀態
const stockSuggestions = ref([])
const showSuggestions = ref(false)
const isSearchingStocks = ref(false)
const selectedStockIndex = ref(-1)
const tradeErrors = ref({
  symbol: '',
  quantity: '',
  price: '',
  date: '',
  fees: ''
})
const newCashFlow = ref({
  amount: 0,
  type: 'DEPOSIT',
  date: new Date().toISOString().split('T')[0],
  notes: ''
})

// 清除特定欄位的錯誤
const clearFieldError = (field) => {
  if (tradeErrors.value[field]) {
    tradeErrors.value[field] = ''
  }
}

// 驗證交易表單
const validateTrade = () => {
  // 重置錯誤
  tradeErrors.value = {
    symbol: '',
    quantity: '',
    price: '',
    date: '',
    fees: ''
  }
  
  let isValid = true
  
  // 驗證股票代號
  if (!newTrade.value.symbol || newTrade.value.symbol.trim() === '') {
    tradeErrors.value.symbol = t('transaction.errors.symbolRequired')
    isValid = false
  }
  
  // 驗證股數
  if (!newTrade.value.quantity || newTrade.value.quantity === 0) {
    tradeErrors.value.quantity = t('transaction.errors.quantityRequired')
    isValid = false
  } else if (newTrade.value.quantity < 0) {
    tradeErrors.value.quantity = t('transaction.errors.quantityInvalid')
    isValid = false
  }
  
  // 驗證價格
  if (!newTrade.value.price || newTrade.value.price === 0) {
    tradeErrors.value.price = t('transaction.errors.priceRequired')
    isValid = false
  } else if (newTrade.value.price < 0) {
    tradeErrors.value.price = t('transaction.errors.priceInvalid')
    isValid = false
  }
  
  // 驗證日期
  if (!newTrade.value.date || newTrade.value.date.trim() === '') {
    tradeErrors.value.date = t('transaction.errors.dateRequired')
    isValid = false
  }
  
  // 驗證手續費（可選，但不能為負數）
  if (newTrade.value.fees < 0) {
    tradeErrors.value.fees = t('transaction.errors.feesInvalid')
    isValid = false
  }
  
  return isValid
}

const submitTrade = async () => {
  // 先進行表單驗證
  if (!validateTrade()) {
    return
  }
  
  try {
    await api.post('/add-transaction/', newTrade.value)
    showAddModal.value = false
    // 重置表單和錯誤
    newTrade.value = {
      symbol: '',
      action: 'BUY',
      date: new Date().toISOString().split('T')[0],
      price: 0,
      quantity: 0,
      fees: 0
    }
    tradeErrors.value = {
      symbol: '',
      quantity: '',
      price: '',
      date: '',
      fees: ''
    }
    // 新增交易成功後自動刷新股價
    await refreshPrices()
  } catch (e) { 
    console.error('Save transaction error:', e)
    
    // 處理字段級別的錯誤（Django REST Framework 格式）
    if (e.response?.status === 400 && e.response?.data) {
      const errorData = e.response.data
      
      // 檢查是否有字段級別的錯誤（例如：{ "symbol": ["錯誤訊息"] }）
      if (typeof errorData === 'object' && !errorData.detail && !errorData.error && !errorData.message) {
        // 處理字段錯誤
        Object.keys(tradeErrors.value).forEach(field => {
          if (errorData[field]) {
            // Django REST Framework 返回的是數組，取第一個錯誤訊息
            const fieldError = Array.isArray(errorData[field]) 
              ? errorData[field][0] 
              : errorData[field]
            tradeErrors.value[field] = fieldError
          }
        })
        
        // 如果有任何字段錯誤，不顯示 alert，讓表單錯誤訊息顯示
        const hasFieldErrors = Object.keys(tradeErrors.value).some(
          field => tradeErrors.value[field]
        )
        if (hasFieldErrors) {
          return // 不顯示 alert，讓表單錯誤訊息顯示
        }
      }
      
      // 處理一般錯誤訊息
      const errorMessage = errorData.detail || 
                          errorData.error || 
                          errorData.message ||
                          (typeof errorData === 'string' ? errorData : null) ||
                          t('messages.saveError')
      
      // 如果錯誤訊息是關於 symbol 的，顯示在表單中
      if (errorMessage && errorMessage.toLowerCase().includes('股票') || 
          errorMessage.toLowerCase().includes('symbol') ||
          errorMessage.toLowerCase().includes('stock')) {
        tradeErrors.value.symbol = errorMessage
        return
      }
      
      alert(`${t('messages.saveError')}: ${errorMessage}`)
    } else {
      // 其他類型的錯誤
      const errorMessage = e.response?.data?.detail || 
                          e.response?.data?.error || 
                          e.response?.data?.message ||
                          e.message || 
                          t('messages.saveError')
      alert(`${t('messages.saveError')}: ${errorMessage}`)
    }
  }
}

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
    await api.post('/cashflow/', data)
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

// 獲取特定股票的交易列表
const fetchSymbolTransactions = async (symbol) => {
  isLoadingTransactions.value = true
  try {
    const response = await api.get('/transactions/', {
      params: { symbol }
    })
    symbolTransactions.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch transactions', error)
    alert(t('messages.fetchError'))
  } finally {
    isLoadingTransactions.value = false
  }
}

// 打開交易列表 modal
const openTransactionsModal = async (symbol) => {
  selectedSymbol.value = symbol
  showTransactionsModal.value = true
  await fetchSymbolTransactions(symbol)
}

// 刪除交易
const deleteTransaction = async (transactionId) => {
  if (!confirm(t('transaction.confirmDelete'))) {
    return
  }
  
  try {
    await api.delete(`/transactions/${transactionId}/`)
    // 重新獲取交易列表
    await fetchSymbolTransactions(selectedSymbol.value)
    // 刷新持倉數據
    await fetchData()
    // 刷新股價
    await refreshPrices()
  } catch (error) {
    console.error('Failed to delete transaction', error)
    const errorMessage = error.response?.data?.detail || 
                        error.response?.data?.error || 
                        error.response?.data?.message ||
                        error.message || 
                        t('messages.deleteError')
    alert(`${t('messages.deleteError')}: ${errorMessage}`)
  }
}

// 監聽貨幣切換，觸發重新渲染（Vue 會自動響應式更新，這裡只是確保）
watch(currentCurrency, () => {
  // 貨幣切換時，Vue 的響應式系統會自動更新所有使用 currentCurrency 的計算屬性
  // 這裡可以添加額外的邏輯，如果需要
})

// 監聽 modal 關閉，清除錯誤訊息
watch(showAddModal, (isOpen) => {
  if (!isOpen) {
    // Modal 關閉時清除所有錯誤
    tradeErrors.value = {
      symbol: '',
      quantity: '',
      price: '',
      date: '',
      fees: ''
    }
  }
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

      <!-- Stats Cards - Horizontal Scroll on Mobile -->
      <div class="overflow-x-auto -mx-4 md:mx-0 px-4 md:px-0">
        <div class="flex md:grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-4 min-w-max md:min-w-0">
          <Card 
            class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink cursor-pointer hover:bg-muted/50 transition-colors active:scale-[0.98]"
            @click="showDepositModal = true"
          >
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
              <p class="text-xs text-primary mt-1 font-medium">{{ t('dashboard.depositFunds') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.availableCash') }}</CardTitle>
              <Wallet class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <!-- 主幣種大字顯示 -->
              <div class="text-xl sm:text-2xl font-bold break-words leading-tight">
                {{ formatCurrency(summary.current_cash || 0) }}
              </div>
              <!-- 副幣種小字顯示 -->
              <div class="text-xs text-muted-foreground mt-1">
                <span v-if="currentCurrency === 'USD'">
                  ≈ HK${{ ((summary.current_cash || 0) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
                <span v-else>
                  ≈ ${{ ((summary.current_cash || 0) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </div>
              <!-- 分開顯示 USD 和 HKD 現金 -->
              <div class="text-xs text-muted-foreground mt-2 space-y-1 pt-2 border-t">
                <div class="flex justify-between items-center">
                  <span class="font-medium">USD:</span>
                  <span class="font-semibold">${{ (summary.current_cash_usd || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="font-medium">HKD:</span>
                  <span class="font-semibold">HK${{ (summary.current_cash_hkd || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.totalMarketValue') }}</CardTitle>
              <DollarSign class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <!-- 主幣種大字顯示 -->
              <div class="text-xl sm:text-2xl font-bold break-words leading-tight">
                {{ formatCurrency(summary.total_market_value || 0) }}
              </div>
              <!-- 副幣種小字顯示 -->
              <div class="text-xs text-muted-foreground mt-1">
                <span v-if="currentCurrency === 'USD'">
                  ≈ HK${{ ((summary.total_market_value || 0) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
                <span v-else>
                  ≈ ${{ ((summary.total_market_value || 0) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.netLiquidity') }}</CardTitle>
              <Package class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <!-- 主幣種大字顯示 -->
              <div class="text-xl sm:text-2xl font-bold break-words leading-tight">
                {{ formatCurrency(summary.net_liquidity || 0) }}
              </div>
              <!-- 副幣種小字顯示 -->
              <div class="text-xs text-muted-foreground mt-1">
                <span v-if="currentCurrency === 'USD'">
                  ≈ HK${{ ((summary.net_liquidity || 0) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
                <span v-else>
                  ≈ ${{ ((summary.net_liquidity || 0) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.netLiquidityDescription') }}</p>
            </CardContent>
          </Card>

          <Card class="min-w-[280px] md:min-w-0 flex-shrink-0 md:flex-shrink">
            <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle class="text-sm font-medium truncate pr-2">{{ t('dashboard.grossPosition') }}</CardTitle>
              <TrendingUp class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            </CardHeader>
            <CardContent>
              <!-- 主幣種大字顯示 -->
              <div class="text-xl sm:text-2xl font-bold break-words leading-tight">
                {{ formatCurrency(summary.gross_position || 0) }}
              </div>
              <!-- 副幣種小字顯示 -->
              <div class="text-xs text-muted-foreground mt-1">
                <span v-if="currentCurrency === 'USD'">
                  ≈ HK${{ ((summary.gross_position || 0) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
                <span v-else>
                  ≈ ${{ ((summary.gross_position || 0) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </div>
              <p class="text-xs text-muted-foreground mt-1">{{ t('dashboard.grossPositionDescription') }}</p>
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
              <!-- 主幣種大字顯示 -->
              <div 
                :class="cn(
                  'text-xl sm:text-2xl font-bold break-words leading-tight',
                  (summary.net_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                )"
              >
                {{ (summary.net_profit || 0) >= 0 ? '+' : '' }}{{ formatCurrency(Math.abs(summary.net_profit || 0)) }}
              </div>
              <!-- 副幣種小字顯示 -->
              <div 
                :class="cn(
                  'text-xs mt-1',
                  (summary.net_profit || 0) >= 0 ? 'text-green-600/70' : 'text-red-600/70'
                )"
              >
                <span v-if="currentCurrency === 'USD'">
                  ≈ {{ (summary.net_profit || 0) >= 0 ? '+' : '' }}HK${{ (Math.abs(summary.net_profit || 0) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
                <span v-else>
                  ≈ {{ (summary.net_profit || 0) >= 0 ? '+' : '' }}${{ (Math.abs(summary.net_profit || 0) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </div>
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
                  <TableHead class="text-right">{{ t('dashboard.totalCost') }}</TableHead>
                  <TableHead class="text-right">{{ t('dashboard.totalMarketValue') }}</TableHead>
                  <TableHead class="text-right">{{ t('dashboard.unrealizedPLShort') }}</TableHead>
                  <TableHead class="text-right">{{ t('dashboard.returnRate') }}</TableHead>
                  <TableHead class="text-center w-[100px]">{{ t('common.actions') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow 
                  v-for="item in portfolio" 
                  :key="item.symbol"
                  class="hover:bg-muted/50"
                >
                  <TableCell class="font-medium">
                    <div class="flex items-center gap-2">
                      <span class="font-semibold">{{ item.symbol }}</span>
                      <span 
                        :class="cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-medium border',
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
                    <div class="text-xs text-muted-foreground mt-0.5">{{ t('dashboard.fifoInventory') }}</div>
                  </TableCell>
                  <TableCell 
                    :class="[
                      'text-right font-medium',
                      item.quantity < 0 ? 'text-purple-600 dark:text-purple-400' : ''
                    ]"
                  >
                    {{ parseFloat(item.quantity || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }}
                  </TableCell>
                  <TableCell class="text-right">
                    {{ formatCurrency(item.avg_cost || 0, item.currency) }}
                  </TableCell>
                  <TableCell class="text-right font-semibold">
                    {{ item.quantity !== 0 ? formatCurrency((item.current_market_value || 0) / Math.abs(item.quantity), item.currency) : formatCurrency(0, item.currency) }}
                  </TableCell>
                  <TableCell class="text-right">
                    {{ formatCurrency((item.avg_cost || 0) * (item.quantity || 0), item.currency) }}
                  </TableCell>
                  <TableCell 
                    :class="[
                      'text-right font-semibold',
                      item.quantity < 0 ? 'text-purple-600 dark:text-purple-400' : ''
                    ]"
                  >
                    {{ formatCurrency(item.current_market_value || 0, item.currency) }}
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      :class="cn(
                        'font-semibold',
                        item.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
                      )"
                    >
                      {{ item.unrealized_pl >= 0 ? '+' : '' }}{{ formatCurrency(Math.abs(item.unrealized_pl || 0), item.currency) }}
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
                <TableRow v-if="portfolio.length === 0">
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
                  <div class="flex items-center gap-2">
                    <span class="font-semibold text-lg">{{ item.symbol }}</span>
                    <span 
                      :class="cn(
                        'px-1.5 py-0.5 rounded text-[10px] font-medium border',
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
                  <!-- Top Right: Current Price -->
                  <div class="text-right">
                    <div class="font-semibold">
                      {{ item.quantity !== 0 ? formatCurrency((item.current_market_value || 0) / Math.abs(item.quantity), item.currency) : formatCurrency(0, item.currency) }}
                    </div>
                    <div class="text-xs text-muted-foreground">
                      <span v-if="currentCurrency === 'USD'">
                        ≈ HK${{ (((item.current_market_value || 0) / (Math.abs(item.quantity) || 1)) * getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                      </span>
                      <span v-else>
                        ≈ ${{ (((item.current_market_value || 0) / (Math.abs(item.quantity) || 1)) / getExchangeRate()).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                      </span>
                    </div>
                  </div>
                  <!-- Bottom Left: Quantity -->
                  <div 
                    :class="[
                      'text-sm',
                      item.quantity < 0 ? 'text-purple-600 dark:text-purple-400 font-medium' : 'text-muted-foreground'
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
            <div v-if="portfolio.length === 0" class="text-center py-8 text-muted-foreground">
              {{ t('dashboard.noHoldings') }}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />

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
          <div class="grid gap-2 relative">
            <label class="text-sm font-medium">{{ t('transaction.symbol') }}</label>
            <div class="relative">
              <Input 
                v-model="newTrade.symbol" 
                :placeholder="t('transaction.symbolPlaceholder')"
                :class="cn('min-h-[44px]', tradeErrors.symbol && 'border-red-500 focus-visible:ring-red-500')"
                @input="handleSymbolInput"
                @keydown="handleSymbolKeydown"
                @focus="searchStocks(newTrade.symbol)"
                @blur="setTimeout(() => { showSuggestions = false }, 200)"
                autocomplete="off"
              />
              <!-- Auto-complete 建議列表 -->
              <div 
                v-if="showSuggestions && stockSuggestions.length > 0"
                class="absolute z-50 w-full mt-1 bg-popover border rounded-md shadow-lg max-h-[200px] overflow-y-auto"
              >
                <div
                  v-for="(stock, index) in stockSuggestions"
                  :key="stock.symbol"
                  @click="selectStock(stock)"
                  :class="cn(
                    'px-3 py-2 cursor-pointer hover:bg-accent transition-colors',
                    index === selectedStockIndex && 'bg-accent'
                  )"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <div class="font-medium text-sm">{{ stock.symbol }}</div>
                      <div class="text-xs text-muted-foreground">{{ stock.name }}</div>
                    </div>
                    <span class="text-xs text-muted-foreground">{{ stock.currency }}</span>
                  </div>
                </div>
              </div>
              <!-- 加載指示器 -->
              <div 
                v-if="isSearchingStocks"
                class="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <RefreshCw class="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            </div>
            <p v-if="tradeErrors.symbol" class="text-sm text-red-500">{{ tradeErrors.symbol }}</p>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.type') }}</label>
            <Select v-model="newTrade.action" class="min-h-[44px]">
              <option value="BUY">{{ t('transaction.buy') }}</option>
              <option value="SELL">{{ t('transaction.sell') }}</option>
            </Select>
            <p v-if="newTrade.action === 'SELL'" class="text-xs text-muted-foreground mt-1">
              {{ t('transaction.shortSellingNote') }}
            </p>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="grid gap-2">
              <label class="text-sm font-medium">{{ t('transaction.price') }}</label>
              <Input 
                v-model.number="newTrade.price" 
                type="number" 
                step="0.01"
                :placeholder="t('transaction.pricePlaceholder')"
                :class="cn('min-h-[44px]', tradeErrors.price && 'border-red-500 focus-visible:ring-red-500')"
                @input="clearFieldError('price')"
              />
              <p v-if="tradeErrors.price" class="text-sm text-red-500">{{ tradeErrors.price }}</p>
            </div>
            <div class="grid gap-2">
              <label class="text-sm font-medium">{{ t('transaction.quantity') }}</label>
              <Input 
                v-model.number="newTrade.quantity" 
                type="number"
                :placeholder="t('transaction.quantityPlaceholder')"
                :class="cn('min-h-[44px]', tradeErrors.quantity && 'border-red-500 focus-visible:ring-red-500')"
                @input="clearFieldError('quantity')"
              />
              <p v-if="tradeErrors.quantity" class="text-sm text-red-500">{{ tradeErrors.quantity }}</p>
            </div>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.date') }}</label>
            <Input 
              v-model="newTrade.date" 
              type="date"
              :class="cn('min-h-[44px]', tradeErrors.date && 'border-red-500 focus-visible:ring-red-500')"
              @input="clearFieldError('date')"
            />
            <p v-if="tradeErrors.date" class="text-sm text-red-500">{{ tradeErrors.date }}</p>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-medium">{{ t('transaction.fees') }}</label>
            <Input 
              v-model.number="newTrade.fees" 
              type="number"
              step="0.01"
              :placeholder="t('transaction.feesPlaceholder')"
              :class="cn('min-h-[44px]', tradeErrors.fees && 'border-red-500 focus-visible:ring-red-500')"
              @input="clearFieldError('fees')"
            />
            <p v-if="tradeErrors.fees" class="text-sm text-red-500">{{ tradeErrors.fees }}</p>
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

    <!-- Transactions Dialog -->
    <Dialog v-model:open="showTransactionsModal">
      <DialogContent class="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{{ t('transaction.viewTransactions') }} - {{ selectedSymbol }}</DialogTitle>
          <DialogDescription>
            {{ t('transaction.description') }}
          </DialogDescription>
        </DialogHeader>
        <div v-if="isLoadingTransactions" class="text-center py-8 text-muted-foreground">
          {{ t('common.loading') }}
        </div>
        <div v-else-if="symbolTransactions.length === 0" class="text-center py-8 text-muted-foreground">
          {{ t('transaction.noTransactionsForSymbol') }}
        </div>
        <div v-else class="space-y-3">
          <div class="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{{ t('transaction.date') }}</TableHead>
                  <TableHead>{{ t('transaction.type') }}</TableHead>
                  <TableHead class="text-right">{{ t('transaction.quantity') }}</TableHead>
                  <TableHead class="text-right">{{ t('transaction.price') }}</TableHead>
                  <TableHead class="text-right">{{ t('transaction.fees') }}</TableHead>
                  <TableHead class="text-center w-[100px]">{{ t('common.actions') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="tx in symbolTransactions" :key="tx.id">
                  <TableCell>{{ new Date(tx.date).toLocaleDateString() }}</TableCell>
                  <TableCell>
                    <div class="flex items-center gap-2">
                      <span 
                        :class="[
                          'px-2 py-0.5 rounded text-xs font-medium',
                          tx.action === 'BUY' ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                          tx.action === 'SELL' ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                          'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                        ]"
                      >
                        {{ tx.action }}
                      </span>
                      <!-- 市場標籤 -->
                      <span 
                        :class="cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-medium border',
                          getMarketColor(tx.symbol || selectedSymbol)
                        )"
                      >
                        {{ getMarketType(tx.symbol || selectedSymbol) === 'HK' ? 'HK' : 'US' }}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell class="text-right">{{ tx.quantity?.toLocaleString() || 0 }}</TableCell>
                  <TableCell class="text-right">
                    <div>{{ formatCurrency(tx.price || 0, tx.currency) }}</div>
                    <div class="text-xs text-muted-foreground">
                      {{ tx.currency || 'USD' }}
                    </div>
                  </TableCell>
                  <TableCell class="text-right">
                    <div>{{ formatCurrency(tx.fees || 0, tx.currency) }}</div>
                    <div class="text-xs text-muted-foreground">
                      {{ tx.currency || 'USD' }}
                    </div>
                  </TableCell>
                  <TableCell class="text-center">
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="deleteTransaction(tx.id)"
                      class="min-h-[32px] min-w-[32px] p-0 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                    >
                      <Trash2 class="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </div>
      </DialogContent>
    </Dialog>

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
