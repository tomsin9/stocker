<script setup>
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft, Filter } from 'lucide-vue-next'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'
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

// Filter 狀態
const selectedAction = ref('all')  // all, BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAW
const selectedDateRange = ref('7d')  // 7d, 30d, 90d, all

const fetchTransactions = async () => {
  isLoading.value = true
  try {
    const params = {
      date_range: selectedDateRange.value
    }
    if (selectedAction.value !== 'all') {
      params.action = selectedAction.value
    }
    const response = await api.get('/transactions/', { params })
    transactions.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch transactions', error)
  } finally {
    isLoading.value = false
  }
}

// 當 filter 改變時重新獲取數據
const handleFilterChange = () => {
  fetchTransactions()
}

const formatCurrency = (amount, originalCurrency = null) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const sourceCurrency = originalCurrency || 'USD'
  
  // 如果原始幣種與當前顯示幣種不同，需要轉換
  let displayAmount = numAmount
  if (sourceCurrency !== currentCurrency.value) {
    if (sourceCurrency === 'USD' && currentCurrency.value === 'HKD') {
      displayAmount = numAmount * exchangeRate.value
    } else if (sourceCurrency === 'HKD' && currentCurrency.value === 'USD') {
      displayAmount = numAmount / exchangeRate.value
    }
  }
  
  const currencySymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  return `${currencySymbol}${Math.abs(displayAmount).toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

// 獲取原始幣種顯示（不轉換）
const formatCurrencyOriginal = (amount, currency) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currency === 'HKD' ? 'HK$0.00' : '$0.00'
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
            class="min-h-[44px] min-w-[44px] active:scale-95"
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
            </select>
          </div>
        </div>
      </div>

      <!-- Transactions List -->
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="transactions.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('transactions.noTransactions') }}
      </div>
      <div v-else class="space-y-3">
        <Card 
          v-for="tx in transactions" 
          :key="`${tx.record_type}-${tx.id}`"
          class="active:scale-[0.98] transition-transform"
        >
          <CardContent class="p-4">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1 flex-wrap">
                  <!-- 股票代號（僅 Transaction 顯示） -->
                  <span v-if="tx.record_type === 'transaction' && tx.symbol" class="font-semibold text-lg">
                    {{ tx.symbol }}
                  </span>
                  <!-- 現金流標題（CashFlow 顯示） -->
                  <span v-else-if="tx.record_type === 'cashflow'" class="font-semibold text-lg">
                    {{ tx.action === 'DEPOSIT' ? t('cashflow.depositTitle') : t('cashflow.withdrawTitle') }}
                  </span>
                  <!-- 市場標籤（僅 Transaction 且有 symbol 時顯示） -->
                  <span 
                    v-if="tx.record_type === 'transaction' && tx.symbol"
                    :class="cn(
                      'px-1.5 py-0.5 rounded text-[10px] font-medium border',
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
                  <div class="text-xs text-muted-foreground">
                    {{ formatCurrencyOriginal(tx.price * tx.quantity, getTransactionCurrency(tx)) }}
                    <span class="ml-1 text-[10px]">({{ getTransactionCurrency(tx) }})</span>
                  </div>
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
                  <div class="text-xs text-muted-foreground">
                    {{ formatCurrencyOriginal(tx.amount, tx.currency) }}
                    <span class="ml-1 text-[10px]">({{ tx.currency }})</span>
                  </div>
                </template>
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
