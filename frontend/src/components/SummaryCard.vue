<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent } from '@/components/ui/card'
import { injectCurrency } from '@/composables/useCurrency'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  exchangeRate: {
    type: Number,
    default: 7.8
  }
})

const { t } = useI18n()
const { currentCurrency } = injectCurrency()

// 格式化貨幣（使用 Intl.NumberFormat，保留兩位小數）
const formatCurrency = (amount, originalCurrency = null) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const exchangeRate = props.exchangeRate
  
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

// 計算 Net Liquidity 的折算幣值
const netLiquidityConverted = computed(() => {
  const netLiquidity = props.summary.net_liquidity || 0
  if (currentCurrency.value === 'USD') {
    return netLiquidity * props.exchangeRate
  } else {
    return netLiquidity / props.exchangeRate
  }
})

// 計算 Cash Pools 顯示
const cashPools = computed(() => {
  const balances = props.summary.cash_balances || { USD: 0, HKD: 0 }
  return [
    { currency: 'USD', amount: balances.USD || 0 },
    { currency: 'HKD', amount: balances.HKD || 0 }
  ]
})

// Daily P&L (使用 net_profit)
const dailyPL = computed(() => {
  return props.summary.net_profit || 0
})
</script>

<template>
  <Card>
    <CardContent class="p-6">
      <div class="flex flex-col md:flex-row justify-between gap-6">
        <!-- 左側：Net Liquidity -->
        <div class="flex-1">
          <div class="text-sm text-muted-foreground mb-2">
            {{ t('dashboard.netLiquidity') }}
          </div>
          <div class="text-3xl md:text-4xl font-bold mb-1">
            {{ formatCurrency(summary.net_liquidity || 0) }}
          </div>
          <div class="text-sm text-muted-foreground">
            <span v-if="currentCurrency === 'USD'">
              ≈ HK${{ new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(netLiquidityConverted) }}
            </span>
            <span v-else>
              ≈ ${{ new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(netLiquidityConverted) }}
            </span>
          </div>
        </div>

        <!-- 右側：3 欄網格 -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 flex-1 md:flex-none md:w-auto">
          <!-- Cash Pools -->
          <div>
            <div class="text-sm text-muted-foreground mb-2">
              {{ t('dashboard.availableCash') }}
            </div>
            <div class="space-y-1">
              <div 
                v-for="pool in cashPools" 
                :key="pool.currency"
                class="flex items-center gap-2"
              >
                <span class="text-lg font-semibold">
                  {{ formatCurrency(pool.amount, pool.currency) }}
                </span>
                <span class="text-xs text-muted-foreground font-medium">
                  {{ pool.currency }}
                </span>
              </div>
            </div>
          </div>

          <!-- Gross Position -->
          <div>
            <div class="text-sm text-muted-foreground mb-2">
              {{ t('dashboard.grossPosition') }}
            </div>
            <div class="text-lg font-semibold">
              {{ formatCurrency(summary.gross_position || 0) }}
            </div>
          </div>

          <!-- Daily P&L -->
          <div>
            <div class="text-sm text-muted-foreground mb-2">
              {{ t('dashboard.netProfit') }}
            </div>
            <div 
              :class="[
                'text-lg font-semibold',
                dailyPL >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
              ]"
            >
              {{ dailyPL >= 0 ? '+' : '-' }}{{ formatCurrency(Math.abs(dailyPL)) }}
            </div>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>
