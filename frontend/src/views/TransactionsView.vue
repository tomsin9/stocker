<script setup>
import { ref, onMounted, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, Filter, ArrowDownCircle, ArrowUpCircle, TrendingUp, TrendingDown, Pencil, Trash2 } from 'lucide-vue-next'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'
import AddTransactionSheet from '@/components/AddTransactionSheet.vue'
import CashFlowEditSheet from '@/components/CashFlowEditSheet.vue'
import api from '@/api'
import { cn } from '@/lib/utils'

const { t } = useI18n()
const router = useRouter()
const { currentCurrency } = injectCurrency()

// 獲取匯率（從 summary 或使用默認值）
const exchangeRate = ref(7.8)

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

// 獲取交易幣種
const getTransactionCurrency = (tx) => {
  return tx.currency || tx.asset?.currency || 'USD'
}

// 獲取匯率（從 dashboard 或使用默認值）
const fetchExchangeRate = async () => {
  try {
    const response = await api.get('/dashboard/')
    if (response.data?.summary?.exchange_rate) {
      exchangeRate.value = response.data.summary.exchange_rate
    } else if (response.data?.summary?.usd_to_hkd_rate) {
      exchangeRate.value = response.data.summary.usd_to_hkd_rate
    }
  } catch (error) {
    console.error('Failed to fetch exchange rate', error)
  }
}

const goBack = () => {
  router.back()
}

const transactions = ref([])
const isLoading = ref(false)

// Edit/Delete 狀態
const showEditTransactionSheet = ref(false)
const editingTransaction = ref(null)
const showEditCashFlowSheet = ref(false)
const editingCashFlow = ref(null)
const deletingId = ref(null)

// Filter 狀態
const selectedAction = ref('all')  // all, BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW
const selectedDateRange = ref('7d')  // 7d, 30d, 90d, all, custom
const customStartDate = ref('')
const customEndDate = ref('')

function getDefaultCustomRange () {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10)
  }
}

const fetchTransactions = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (selectedDateRange.value === 'custom' && customStartDate.value && customEndDate.value) {
      params.start_date = customStartDate.value
      params.end_date = customEndDate.value
    } else {
      params.date_range = selectedDateRange.value
    }
    if (selectedAction.value !== 'all') {
      params.action = selectedAction.value
    }
    const response = await api.get('/transactions/', { params })
    transactions.value = response.data || []
    
    // 調試信息：檢查是否有 cashflow 記錄
    // const cashflowCount = transactions.value.filter(tx => tx.record_type === 'cashflow').length
    // if (cashflowCount > 0) {
    //   console.log(`Found ${cashflowCount} cashflow records`)
    // } else if (selectedAction.value === 'DEPOSIT' || selectedAction.value === 'WITHDRAW') {
    //   console.log('No cashflow records found for selected filter. Try changing date range to "All Time"')
    // }
  } catch (error) {
    console.error('Failed to fetch transactions', error)
  } finally {
    isLoading.value = false
  }
}

// 當 filter 改變時重新獲取數據
const handleFilterChange = () => {
  if (selectedDateRange.value === 'custom') {
    if (!customStartDate.value || !customEndDate.value) {
      const { start, end } = getDefaultCustomRange()
      customStartDate.value = start
      customEndDate.value = end
    }
    fetchTransactions()
  } else {
    fetchTransactions()
  }
}

const applyCustomDateRange = () => {
  if (customStartDate.value && customEndDate.value) {
    if (customStartDate.value > customEndDate.value) {
      const swap = customStartDate.value
      customStartDate.value = customEndDate.value
      customEndDate.value = swap
    }
    fetchTransactions()
  }
}

// 打開編輯交易表單
const openEditTransaction = async (transaction) => {
  editingTransaction.value = transaction
  await nextTick()
  showEditTransactionSheet.value = true
}

// 處理編輯交易成功
const handleEditTransactionSuccess = async () => {
  showEditTransactionSheet.value = false
  editingTransaction.value = null
  await fetchTransactions()
}

// 打開編輯現金流表單
const openEditCashFlow = async (cashflow) => {
  editingCashFlow.value = cashflow
  await nextTick()
  showEditCashFlowSheet.value = true
}

// 處理編輯現金流成功
const handleEditCashFlowSuccess = async () => {
  showEditCashFlowSheet.value = false
  editingCashFlow.value = null
  await fetchTransactions()
}

// 刪除交易
const deleteTransaction = async (transactionId) => {
  if (deletingId.value === transactionId) {
    return
  }
  
  if (!confirm(t('transaction.confirmDelete'))) {
    return
  }
  
  deletingId.value = transactionId
  try {
    await api.delete(`/transactions/${transactionId}/`)
    await fetchTransactions()
  } catch (error) {
    console.error('Failed to delete transaction', error)
    const errorMessage = error.response?.data?.detail || 
                        error.response?.data?.error || 
                        error.response?.data?.message ||
                        error.message || 
                        t('messages.deleteError')
    alert(`${t('messages.deleteError')}: ${errorMessage}`)
  } finally {
    deletingId.value = null
  }
}

// 刪除現金流
const deleteCashFlow = async (cashflowId) => {
  if (deletingId.value === cashflowId) {
    return
  }
  
  if (!confirm(t('transaction.confirmDelete'))) {
    return
  }
  
  deletingId.value = cashflowId
  try {
    await api.delete(`/cashflow/${cashflowId}/`)
    await fetchTransactions()
  } catch (error) {
    console.error('Failed to delete cashflow', error)
    const errorMessage = error.response?.data?.detail || 
                        error.response?.data?.error || 
                        error.response?.data?.message ||
                        error.message || 
                        t('messages.deleteError')
    alert(`${t('messages.deleteError')}: ${errorMessage}`)
  } finally {
    deletingId.value = null
  }
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

// 獲取原始幣種顯示（不轉換，用於顯示原始值）
const formatCurrencyOriginal = (amount, currency) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
    return currencySymbol + '0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const currencySymbol = currency === 'HKD' ? 'HK$' : '$'
  return `${currencySymbol}${Math.abs(numAmount).toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

onMounted(() => {
  fetchExchangeRate()
  fetchTransactions()
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 mb-4">
        <div class="flex items-center gap-3 mb-8">
          <Button 
            variant="ghost" 
            size="icon"
            @click="goBack"
            class="min-h-[44px] min-w-[44px] active:scale-95 md:hidden"
          >
            <ArrowLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold tracking-tight">{{ t('transactions.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">{{ t('transactions.description') }}</p>
          </div>
        </div>
        
        <!-- Filters -->
        <div class="flex flex-col sm:flex-row justify-between gap-3">
          <div class="flex items-center gap-2">
            <Filter class="h-4 w-4 text-muted-foreground flex-shrink-0" />
            <label class="text-sm font-medium whitespace-nowrap">{{ t('transactions.filter.type') }}:</label>
            <select 
              v-model="selectedAction" 
              @change="handleFilterChange"
              class="min-h-[36px] px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-1"
            >
              <option value="all">{{ t('transactions.filter.all') }}</option>
              <option value="BUY">{{ t('transaction.buy') }}</option>
              <option value="SELL">{{ t('transaction.sell') }}</option>
              <option value="DIVIDEND">{{ t('transaction.dividend') }}</option>
              <option value="DEPOSIT">{{ t('cashflow.deposit') }}</option>
              <option value="WITHDRAW">{{ t('cashflow.withdraw') }}</option>
            </select>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div class="flex items-center gap-2">
              <label class="text-sm font-medium whitespace-nowrap">{{ t('transactions.filter.dateRange') }}:</label>
              <select 
                v-model="selectedDateRange" 
                @change="handleFilterChange"
                class="min-h-[36px] px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-1"
              >
                <option value="7d">{{ t('transactions.filter.last7Days') }}</option>
                <option value="30d">{{ t('transactions.filter.last30Days') }}</option>
                <option value="90d">{{ t('transactions.filter.last90Days') }}</option>
                <option value="all">{{ t('transactions.filter.allTime') }}</option>
                <option value="custom">{{ t('transactions.filter.customRange') }}</option>
              </select>
            </div>
            <!-- Custom date range: calendar inputs -->
            <div 
              v-if="selectedDateRange === 'custom'" 
              class="flex flex-wrap items-center gap-2 rounded-md border border-input bg-muted/30 px-3 py-2"
            >
              <label class="text-xs font-medium text-muted-foreground">{{ t('transactions.filter.from') }}</label>
              <input 
                v-model="customStartDate" 
                type="date" 
                class="min-h-[36px] flex-1 min-w-[120px] rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring text-foreground"
              />
              <label class="text-xs font-medium text-muted-foreground">{{ t('transactions.filter.to') }}</label>
              <input 
                v-model="customEndDate" 
                type="date" 
                class="min-h-[36px] flex-1 min-w-[120px] rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-ring text-foreground"
              />
              <Button 
                size="sm" 
                @click="applyCustomDateRange"
                class="min-h-[36px]"
              >
                {{ t('transactions.filter.apply') }}
              </Button>
            </div>
          </div>
        </div>
      </div>

      <!-- Transactions List -->
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="transactions.length === 0" class="text-center py-8 text-muted-foreground">
        <p>{{ t('transactions.noTransactions') }}</p>
        <p v-if="selectedAction === 'DEPOSIT' || selectedAction === 'WITHDRAW'" class="text-xs mt-2 text-muted-foreground">
          {{ t('transactions.tryAllTime') }}
        </p>
      </div>
      <div v-else class="space-y-3">
        <!-- 統計信息（僅在開發環境或調試時顯示） -->
        <div v-if="transactions.some(tx => tx.record_type === 'cashflow')" class="mb-2 text-xs text-muted-foreground">
          {{ transactions.filter(tx => tx.record_type === 'transaction').length }} {{ t('transactions.transactions') }}, 
          {{ transactions.filter(tx => tx.record_type === 'cashflow').length }} {{ t('transactions.cashflows') }}
        </div>
        <Card 
          v-for="tx in transactions" 
          :key="`${tx.record_type}-${tx.id}`"
          class="active:scale-[0.98] transition-transform"
        >
          <CardContent class="p-4">
            <div class="flex justify-between items-start gap-3">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <!-- 股票代號（僅 Transaction 顯示） -->
                  <span v-if="tx.record_type === 'transaction' && tx.symbol" class="font-semibold text-lg">
                    {{ tx.symbol }}
                  </span>
                  <!-- 現金流標題（CashFlow 顯示） -->
                  <div v-else-if="tx.record_type === 'cashflow'" class="flex items-center gap-2">
                    <ArrowDownCircle v-if="tx.action === 'DEPOSIT'" class="h-5 w-5 text-green-600" />
                    <ArrowUpCircle v-else-if="tx.action === 'WITHDRAW'" class="h-5 w-5 text-red-600" />
                    <span class="font-semibold text-lg">
                      {{ tx.action === 'DEPOSIT' ? t('cashflow.depositTitle') : t('cashflow.withdrawTitle') }}
                    </span>
                  </div>
                  <!-- 市場標籤（僅 Transaction 且有 symbol 時顯示） -->
                  <span 
                    v-if="tx.record_type === 'transaction' && tx.symbol"
                    :class="cn(
                      'px-1 py-0 rounded text-[10px] font-medium border',
                      getMarketColor(tx.symbol)
                    )"
                  >
                    {{ getMarketType(tx.symbol) === 'HK' ? 'HK' : 'US' }}
                  </span>
                  <!-- 交易類型標籤 -->
                  <span 
                    :class="[
                      'px-2 py-0.5 rounded text-xs font-medium',
                      tx.action === 'BUY' || tx.action === 'DEPOSIT' 
                        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300' :
                      tx.action === 'SELL' || tx.action === 'WITHDRAW' 
                        ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300' :
                      tx.action === 'DIVIDEND'
                        ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300' :
                      'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                    ]"
                  >
                    {{ tx.action === 'DEPOSIT' ? t('cashflow.deposit') : 
                       tx.action === 'WITHDRAW' ? t('cashflow.withdraw') : 
                       tx.action === 'DIVIDEND' ? t('transaction.dividend') : 
                       tx.action }}
                  </span>
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ new Date(tx.date).toLocaleDateString() }}
                </div>
                <!-- 備註（如果有） -->
                <div v-if="tx.notes" class="text-xs text-muted-foreground mt-1">
                  {{ tx.notes }}
                </div>
              </div>
              <div class="text-right">
                <!-- Transaction 顯示 -->
                <template v-if="tx.record_type === 'transaction'">
                  <div class="font-semibold">
                    <template v-if="tx.action === 'DIVIDEND'">
                      <!-- 股息：顯示總金額 -->
                      {{ formatCurrency(tx.price * tx.quantity, getTransactionCurrency(tx)) }}
                    </template>
                    <template v-else>
                      <!-- 買賣：顯示總金額 -->
                      {{ formatCurrency(tx.price * tx.quantity, getTransactionCurrency(tx)) }}
                    </template>
                  </div>
                  <div class="text-xs text-muted-foreground font-medium">{{ getTransactionCurrency(tx) }}</div>
                  <div v-if="tx.action !== 'DIVIDEND'" class="text-sm text-muted-foreground mt-0.5">
                    {{ parseFloat(tx.quantity || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }} @ {{ formatCurrency(tx.price, getTransactionCurrency(tx)) }}
                  </div>
                  <div v-if="tx.action === 'DIVIDEND'" class="text-sm text-muted-foreground mt-0.5">
                    {{ t('transaction.dividend') }}: {{ parseFloat(tx.quantity || 0).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',') }} @ {{ formatCurrency(tx.price, getTransactionCurrency(tx)) }}
                  </div>
                  <div v-if="tx.fees > 0" class="text-xs text-muted-foreground mt-0.5">
                    {{ t('transaction.fees') }}: {{ formatCurrency(tx.fees, getTransactionCurrency(tx)) }}
                  </div>
                </template>
                <!-- CashFlow 顯示 -->
                <template v-else-if="tx.record_type === 'cashflow'">
                  <div class="font-semibold">
                    {{ formatCurrency(tx.amount, tx.currency) }}
                  </div>
                  <div class="text-xs text-muted-foreground font-medium">{{ tx.currency }}</div>
                </template>
              </div>
              <!-- Edit/Delete 按鈕 -->
              <div class="flex flex-col gap-1 flex-shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  @click="tx.record_type === 'transaction' ? openEditTransaction(tx) : openEditCashFlow(tx)"
                  class="min-h-[32px] min-w-[32px] p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950"
                  :title="t('common.edit')"
                >
                  <Pencil class="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  @click="tx.record_type === 'transaction' ? deleteTransaction(tx.id) : deleteCashFlow(tx.id)"
                  :disabled="deletingId === tx.id"
                  class="min-h-[32px] min-w-[32px] p-0 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50"
                  :title="t('common.delete')"
                >
                  <Trash2 class="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />

    <!-- Edit Transaction Sheet -->
    <AddTransactionSheet 
      v-model:open="showEditTransactionSheet"
      mode="edit"
      :transaction="editingTransaction"
      @success="handleEditTransactionSuccess"
    />

    <!-- Edit CashFlow Sheet -->
    <CashFlowEditSheet 
      v-model:open="showEditCashFlowSheet"
      :cashflow="editingCashFlow"
      @success="handleEditCashFlowSuccess"
    />
  </div>
</template>

<style scoped>
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}

@media (min-width: 768px) {
  .safe-area-bottom {
    padding-bottom: 0;
  }
}
</style>
