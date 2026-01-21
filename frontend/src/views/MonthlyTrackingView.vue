<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { ArrowLeft, ChevronDown, ChevronUp, TrendingUp, TrendingDown } from 'lucide-vue-next'
import BottomNavigation from '@/components/BottomNavigation.vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import { getCSSVariable } from '@/lib/chartColors'
import api from '@/api'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const { t } = useI18n()
const router = useRouter()

const goBack = () => {
  router.back()
}

// 獲取翻譯後的月份名稱
const getMonthName = (month) => {
  if (!month || month === 'AVG.') {
    return month || t('monthlyTracking.avg')
  }
  // 如果是數字，使用翻譯
  const monthNum = typeof month === 'number' ? month : parseInt(month)
  if (monthNum >= 1 && monthNum <= 12) {
    return t(`monthlyTracking.months.${monthNum}`)
  }
  // 如果不是有效月份，返回原值
  return month
}

// 切換月份卡片展開/摺疊
const toggleMonthExpanded = (month) => {
  if (expandedMonths.value.has(month)) {
    expandedMonths.value.delete(month)
  } else {
    expandedMonths.value.add(month)
  }
}

// 切換平均行展開/摺疊
const toggleAvgExpanded = () => {
  isAvgExpanded.value = !isAvgExpanded.value
}

const monthlyData = ref(null)
const isLoading = ref(false)
const selectedYear = ref(new Date().getFullYear())
const availableYears = ref([])
const expandedMonths = ref(new Set()) // 追蹤哪些月份卡片是展開的
const isAvgExpanded = ref(false) // 追蹤平均行是否展開

// 獲取可用年份列表（用戶有交易或現金流記錄的年份）
const fetchAvailableYears = async () => {
  try {
    const response = await api.get('/monthly-tracking-years/')
    if (response.data?.years && response.data.years.length > 0) {
      availableYears.value = response.data.years
      // 如果當前選中的年份不在列表中，選擇第一個（最新的年份）
      if (!availableYears.value.includes(selectedYear.value)) {
        selectedYear.value = availableYears.value[0]
      }
    } else {
      // 如果沒有數據，使用當前年份作為默認值
      availableYears.value = [new Date().getFullYear()]
    }
  } catch (error) {
    console.error('Failed to fetch available years', error)
    // 如果獲取失敗，使用當前年份作為默認值
    availableYears.value = [new Date().getFullYear()]
  }
}

const fetchMonthlyTracking = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/monthly-tracking/', {
      params: { year: selectedYear.value }
    })
    monthlyData.value = response.data
  } catch (error) {
    console.error('Failed to fetch monthly tracking data', error)
    monthlyData.value = null
  } finally {
    isLoading.value = false
  }
}

// 監聽年份變化
watch(selectedYear, () => {
  fetchMonthlyTracking()
})

// 格式化百分比
const formatPercent = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0.00%'
  }
  return `${parseFloat(value).toFixed(2)}%`
}

// 格式化貨幣
const formatCurrency = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return 'US$0.00'
  }
  const numAmount = parseFloat(amount)
  return `US$${Math.abs(numAmount).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`
}

// 格式化金額和百分比
const formatCurrencyWithPercent = (amount, percent) => {
  const currency = formatCurrency(amount)
  const percentStr = formatPercent(percent)
  return `${currency} (${percentStr})`
}

// 格式化天數
const formatDays = (days) => {
  if (days === null || days === undefined || isNaN(days)) {
    return '-'
  }
  return Math.round(days).toString()
}

// 計算圖表數據（每個月的 gain 和 loss）
const chartData = computed(() => {
  if (!monthlyData.value || !monthlyData.value.months) {
    return {
      labels: [],
      datasets: []
    }
  }
  
  const months = monthlyData.value.months.filter(m => m.total_trades > 0)
  if (months.length === 0) {
    return {
      labels: [],
      datasets: []
    }
  }
  
  // 按月份排序
  const sortedMonths = [...months].sort((a, b) => a.month - b.month)
  
  const labels = sortedMonths.map(m => getMonthName(m.month))
  const gains = sortedMonths.map(m => m.profit > 0 ? m.profit : 0)
  const losses = sortedMonths.map(m => m.profit < 0 ? Math.abs(m.profit) : 0)
  
  // 使用標準的綠色和紅色，確保在明暗主題下都能正確顯示
  const gainColor = '#22c55e' // green-500
  const lossColor = '#ef4444' // red-500
  
  return {
    labels,
    datasets: [
      {
        label: t('monthlyTracking.gain'),
        data: gains,
        backgroundColor: gainColor,
        borderColor: gainColor,
        borderWidth: 1,
        maxBarThickness: 40,
        barPercentage: 0.6,
        categoryPercentage: 0.8
      },
      {
        label: t('monthlyTracking.loss'),
        data: losses,
        backgroundColor: lossColor,
        borderColor: lossColor,
        borderWidth: 1,
        maxBarThickness: 40,
        barPercentage: 0.6,
        categoryPercentage: 0.8
      }
    ]
  }
})

// 圖表選項
const chartOptions = computed(() => {
  // 根據屏幕寬度決定刻度數量
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const maxTicks = isMobile ? 4 : 6
  
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          padding: 10,
          usePointStyle: true,
          font: {
            size: 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            return `${label}: ${formatCurrency(value)}`
          }
        }
      }
    },
    scales: {
      x: {
        stacked: false,
        grid: {
          display: false
        }
      },
      y: {
        stacked: false,
        beginAtZero: true,
        ticks: {
          maxTicksLimit: maxTicks,
          callback: function(value) {
            return formatCurrency(value)
          }
        }
      }
    }
  }
})

// 計算本月趨勢（與上個月比較）
const monthlyTrend = computed(() => {
  if (!monthlyData.value || !monthlyData.value.months) {
    return null
  }
  
  const months = monthlyData.value.months.filter(m => m.total_trades > 0)
  if (months.length < 2) {
    return null
  }
  
  // 按月份排序
  const sortedMonths = [...months].sort((a, b) => a.month - b.month)
  const currentMonth = sortedMonths[sortedMonths.length - 1]
  const previousMonth = sortedMonths[sortedMonths.length - 2]
  
  if (!currentMonth || !previousMonth) {
    return null
  }
  
  const currentProfit = currentMonth.profit || 0
  const previousProfit = previousMonth.profit || 0
  
  // 如果上個月沒有利潤，無法計算百分比變化
  if (previousProfit === 0) {
    if (currentProfit > 0) {
      const percent = '100.00'
      return { type: 'up', percent: 100, message: t('monthlyTracking.trendingUp').replace('{percent}', percent) }
    } else if (currentProfit < 0) {
      const percent = '100.00'
      return { type: 'down', percent: 100, message: t('monthlyTracking.trendingDown').replace('{percent}', percent) }
    } else {
      return { type: 'neutral', percent: 0, message: t('monthlyTracking.noChange') }
    }
  }
  
  const percentChange = ((currentProfit - previousProfit) / Math.abs(previousProfit)) * 100
  
  if (percentChange > 0) {
    const percent = Math.abs(percentChange).toFixed(2)
    return { 
      type: 'up', 
      percent: Math.abs(percentChange), 
      message: t('monthlyTracking.trendingUp').replace('{percent}', percent)
    }
  } else if (percentChange < 0) {
    const percent = Math.abs(percentChange).toFixed(2)
    return { 
      type: 'down', 
      percent: Math.abs(percentChange), 
      message: t('monthlyTracking.trendingDown').replace('{percent}', percent)
    }
  } else {
    return { type: 'neutral', percent: 0, message: t('monthlyTracking.noChange') }
  }
})

// 計算平均值行
const averageRow = computed(() => {
  if (!monthlyData.value || !monthlyData.value.months) {
    return null
  }
  
  const months = monthlyData.value.months.filter(m => m.total_trades > 0)
  if (months.length === 0) {
    return null
  }
  
  const totalTrades = months.reduce((sum, m) => sum + m.total_trades, 0)
  const profitableMonths = months.filter(m => m.profit > 0)
  const losingMonths = months.filter(m => m.profit <= 0)
  
  const avgProfit = profitableMonths.length > 0
    ? profitableMonths.reduce((sum, m) => {
        const profitableTrades = months.filter(month => month.month === m.month && month.profit > 0)
        // 估算：使用該月的平均獲利
        return sum + (m.avg_profit || 0)
      }, 0) / profitableMonths.length
    : 0
  
  const avgProfitPercent = profitableMonths.length > 0
    ? profitableMonths.reduce((sum, m) => sum + (m.avg_profit_percent || 0), 0) / profitableMonths.length
    : 0
  
  const avgLoss = losingMonths.length > 0
    ? losingMonths.reduce((sum, m) => sum + (m.avg_loss || 0), 0) / losingMonths.length
    : 0
  
  const avgLossPercent = losingMonths.length > 0
    ? losingMonths.reduce((sum, m) => sum + (m.avg_loss_percent || 0), 0) / losingMonths.length
    : 0
  
  const winCount = months.filter(m => m.profit > 0).length
  const winRate = months.length > 0 ? (winCount / months.length) * 100 : 0
  
  // 最大獲利：從所有月份中找最大值
  const maxProfit = Math.max(...months.map(m => m.max_profit || 0), 0)
  
  // 最大虧損：只從有虧損交易的月份中找最小值（最大的虧損）
  const monthsWithMaxLosses = months.filter(m => m.max_loss < 0)
  const maxLoss = monthsWithMaxLosses.length > 0 
    ? Math.min(...monthsWithMaxLosses.map(m => m.max_loss || 0))
    : 0
  
  // 找到最大獲利和最大虧損對應的百分比
  const maxProfitMonth = months.find(m => m.max_profit === maxProfit)
  const maxLossMonth = monthsWithMaxLosses.find(m => m.max_loss === maxLoss)
  const maxProfitPercent = maxProfitMonth?.max_profit_percent || 0
  const maxLossPercent = maxLossMonth?.max_loss_percent || 0
  
  return {
    month_name: t('monthlyTracking.avg'), // 保持向後兼容，但前端會使用 getMonthName 來翻譯
    avg_profit: avgProfit,
    avg_profit_percent: avgProfitPercent,
    avg_loss: avgLoss,
    avg_loss_percent: avgLossPercent,
    win_rate: winRate,
    total_trades: totalTrades,
    max_profit: maxProfit,
    max_profit_percent: maxProfitPercent,
    max_loss: maxLoss,
    max_loss_percent: maxLossPercent,
    avg_holding_days_success: null,
    avg_holding_days_fail: null,
    profit: months.reduce((sum, m) => sum + m.profit, 0)
  }
})

onMounted(() => {
  fetchAvailableYears().then(() => {
    fetchMonthlyTracking()
  })
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 mb-4">
        <div class="flex items-center gap-3 mb-4">
          <Button 
            variant="ghost" 
            size="icon"
            @click="goBack"
            class="min-h-[44px] min-w-[44px] active:scale-95 md:hidden"
          >
            <ArrowLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold tracking-tight">{{ t('monthlyTracking.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">{{ t('monthlyTracking.description') }}</p>
          </div>
        </div>
        
        <!-- Year Selector -->
        <div class="grid md:flex items-center gap-2">
          <label class="text-xs sm:text-sm font-medium whitespace-nowrap">{{ t('monthlyTracking.year') }}:</label>
          <select 
            v-model="selectedYear" 
            class="min-h-[44px] sm:min-h-[36px] px-3 py-1.5 text-sm rounded-md border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring focus:ring-offset-1"
          >
            <option v-for="year in availableYears" :key="year" :value="year">
              {{ year }}
            </option>
          </select>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>

      <!-- Data Table -->
      <div v-else-if="monthlyData">

        <!-- Summary Card -->
        <Card class="mb-4">
          <CardContent class="p-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
              <div>
                <p class="text-xs sm:text-sm text-muted-foreground mb-1">{{ t('monthlyTracking.startingCapital') }}</p>
                <p class="text-base sm:text-lg font-semibold">{{ formatCurrency(monthlyData.summary.starting_capital) }}</p>
              </div>
              <div>
                <p class="text-xs sm:text-sm text-muted-foreground mb-1">{{ t('monthlyTracking.unrealizedProfit') }}</p>
                <p class="text-base sm:text-lg font-semibold" :class="(monthlyData.summary.unrealized_profit || 0) > 0 ? 'text-green-600 dark:text-green-400' : (monthlyData.summary.unrealized_profit || 0) < 0 ? 'text-red-600 dark:text-red-400' : ''">
                  {{ formatCurrency(monthlyData.summary.unrealized_profit || 0) }}
                </p>
                <p class="text-xs text-muted-foreground mt-0.5" :class="(monthlyData.summary.unrealized_profit_percent || 0) > 0 ? 'text-green-600 dark:text-green-400' : (monthlyData.summary.unrealized_profit_percent || 0) < 0 ? 'text-red-600 dark:text-red-400' : ''">
                  {{ formatPercent(monthlyData.summary.unrealized_profit_percent || 0) }}
                </p>
              </div>
              <div>
                <p class="text-xs sm:text-sm text-muted-foreground mb-1">{{ t('monthlyTracking.totalProfit') }}</p>
                <p class="text-base sm:text-lg font-semibold" :class="monthlyData.summary.total_profit > 0 ? 'text-green-600 dark:text-green-400' : monthlyData.summary.total_profit < 0 ? 'text-red-600 dark:text-red-400' : ''">
                  {{ formatCurrency(monthlyData.summary.total_profit) }}
                </p>
                <p class="text-xs text-muted-foreground mt-0.5" :class="monthlyData.summary.total_profit_percent > 0 ? 'text-green-600 dark:text-green-400' : monthlyData.summary.total_profit_percent < 0 ? 'text-red-600 dark:text-red-400' : ''">
                  {{ formatPercent(monthlyData.summary.total_profit_percent) }}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Desktop Table View -->
        <Card class="mb-4 hidden sm:block">
          <CardContent class="p-0">
            <div class="overflow-x-auto">
              <Table>
              <TableHeader>
                <TableRow class="h-[60px]">
                  <TableHead class="left-0 bg-background">{{ t('monthlyTracking.month') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.avgProfit') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.avgLoss') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.winRate') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.totalTrades') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.maxProfit') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.maxLoss') }}</TableHead>
                  <TableHead class="text-right max-w-[90px]">{{ t('monthlyTracking.avgHoldingDaysSuccess') }}</TableHead>
                  <TableHead class="text-right max-w-[90px]">{{ t('monthlyTracking.avgHoldingDaysFail') }}</TableHead>
                  <TableHead class="text-right">{{ t('monthlyTracking.profit') }}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <!-- Monthly Rows -->
                <TableRow v-for="month in monthlyData.months" :key="month.month">
                  <TableCell class="font-medium sticky left-0 bg-background">{{ getMonthName(month.month) }}</TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="month.total_trades > 0" 
                      :class="month.avg_profit > 0 ? 'text-green-600 dark:text-green-400' : month.avg_profit < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(month.avg_profit, month.avg_profit_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="month.total_trades > 0" 
                      :class="month.avg_loss > 0 ? 'text-green-600 dark:text-green-400' : month.avg_loss < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(month.avg_loss, month.avg_loss_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">{{ formatPercent(month.win_rate) }}</TableCell>
                  <TableCell class="text-right">{{ month.total_trades }}</TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="month.total_trades > 0" 
                      :class="month.max_profit > 0 ? 'text-green-600 dark:text-green-400' : month.max_profit < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(month.max_profit, month.max_profit_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="month.total_trades > 0" 
                      :class="month.max_loss > 0 ? 'text-green-600 dark:text-green-400' : month.max_loss < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(month.max_loss, month.max_loss_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">{{ formatDays(month.avg_holding_days_success) }}</TableCell>
                  <TableCell class="text-right">{{ formatDays(month.avg_holding_days_fail) }}</TableCell>
                  <TableCell class="text-right" :class="month.profit > 0 ? 'text-green-600 dark:text-green-400' : month.profit < 0 ? 'text-red-600 dark:text-red-400' : ''">
                    {{ formatCurrency(month.profit) }}
                  </TableCell>
                </TableRow>
                
                <!-- Average Row -->
                <TableRow v-if="averageRow" class="font-semibold bg-muted/50">
                  <TableCell class="font-bold sticky left-0 bg-muted/50 z-10">{{ averageRow.month_name }}</TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="averageRow.total_trades > 0" 
                      :class="averageRow.avg_profit > 0 ? 'text-green-600 dark:text-green-400' : averageRow.avg_profit < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(averageRow.avg_profit, averageRow.avg_profit_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="averageRow.total_trades > 0" 
                      :class="averageRow.avg_loss > 0 ? 'text-green-600 dark:text-green-400' : averageRow.avg_loss < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(averageRow.avg_loss, averageRow.avg_loss_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">{{ formatPercent(averageRow.win_rate) }}</TableCell>
                  <TableCell class="text-right">{{ averageRow.total_trades }}</TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="averageRow.total_trades > 0" 
                      :class="averageRow.max_profit > 0 ? 'text-green-600 dark:text-green-400' : averageRow.max_profit < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(averageRow.max_profit, averageRow.max_profit_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">
                    <div 
                      v-if="averageRow.total_trades > 0" 
                      :class="averageRow.max_loss > 0 ? 'text-green-600 dark:text-green-400' : averageRow.max_loss < 0 ? 'text-red-600 dark:text-red-400' : ''"
                    >
                      {{ formatCurrencyWithPercent(averageRow.max_loss, averageRow.max_loss_percent) }}
                    </div>
                    <div v-else>-</div>
                  </TableCell>
                  <TableCell class="text-right">-</TableCell>
                  <TableCell class="text-right">-</TableCell>
                  <TableCell class="text-right" :class="averageRow.profit > 0 ? 'text-green-600 dark:text-green-400' : averageRow.profit < 0 ? 'text-red-600 dark:text-red-400' : ''">
                    {{ formatCurrency(averageRow.profit) }}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
            </div>
          </CardContent>
        </Card>

        <!-- Mobile Card List View -->
        <div class="mb-4 block md:hidden space-y-3">
          <!-- Monthly Cards -->
          <Card 
            v-for="month in monthlyData.months" 
            :key="month.month"
            class="active:scale-[0.98] transition-transform"
          >
            <CardContent class="p-4">
              <!-- Header: Month and Profit -->
              <div class="flex items-center justify-between mb-3 pb-3 border-b">
                <h3 class="text-lg font-bold">{{ getMonthName(month.month) }}</h3>
                <div 
                  :class="[
                    'text-lg font-bold',
                    month.profit > 0 ? 'text-green-600 dark:text-green-400' : month.profit < 0 ? 'text-red-600 dark:text-red-400' : ''
                  ]"
                >
                  {{ formatCurrency(month.profit) }}
                </div>
              </div>

              <!-- Key Metrics Grid -->
              <div class="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <p class="text-xs text-muted-foreground mb-1">{{ t('monthlyTracking.winRate') }}</p>
                  <p class="text-sm font-semibold">{{ formatPercent(month.win_rate) }}</p>
                </div>
                <div>
                  <p class="text-xs text-muted-foreground mb-1">{{ t('monthlyTracking.totalTrades') }}</p>
                  <p class="text-sm font-semibold">{{ month.total_trades }}</p>
                </div>
              </div>

              <!-- Toggle Button -->
              <div v-if="month.total_trades > 0" class="pt-3 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  @click="toggleMonthExpanded(month.month)"
                  class="w-full min-h-[44px] justify-between text-sm font-medium hover:bg-muted"
                >
                  <span>{{ expandedMonths.has(month.month) ? t('monthlyTracking.hideDetails') : t('monthlyTracking.showDetails') }}</span>
                  <ChevronDown 
                    v-if="!expandedMonths.has(month.month)"
                    class="h-4 w-4 transition-transform"
                  />
                  <ChevronUp 
                    v-else
                    class="h-4 w-4 transition-transform"
                  />
                </Button>
              </div>

              <!-- Detailed Metrics (Collapsible) -->
              <div 
                v-if="month.total_trades > 0 && expandedMonths.has(month.month)" 
                class="space-y-2 pt-3 border-t"
              >
                <div class="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgProfit') }}:</span>
                    <span class="ml-1 font-medium">{{ formatCurrencyWithPercent(month.avg_profit, month.avg_profit_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgLoss') }}:</span>
                    <span class="ml-1 font-medium">{{ formatCurrencyWithPercent(month.avg_loss, month.avg_loss_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.maxProfit') }}:</span>
                    <span class="ml-1 font-medium text-green-600 dark:text-green-400">{{ formatCurrencyWithPercent(month.max_profit, month.max_profit_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.maxLoss') }}:</span>
                    <span class="ml-1 font-medium text-red-600 dark:text-red-400">{{ formatCurrencyWithPercent(month.max_loss, month.max_loss_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgHoldingDaysSuccess') }}:</span>
                    <span class="ml-1 font-medium">{{ formatDays(month.avg_holding_days_success) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgHoldingDaysFail') }}:</span>
                    <span class="ml-1 font-medium">{{ formatDays(month.avg_holding_days_fail) }}</span>
                  </div>
                </div>
              </div>
              <div v-else-if="month.total_trades === 0" class="pt-3 border-t text-xs text-muted-foreground text-center">
                -
              </div>
            </CardContent>
          </Card>

          <!-- Average Card -->
          <Card 
            v-if="averageRow"
            class="bg-muted/50 border-2 active:scale-[0.98] transition-transform"
          >
            <CardContent class="p-4">
              <!-- Header: AVG and Total Profit -->
              <div class="flex items-center justify-between mb-3 pb-3 border-b">
                <h3 class="text-lg font-bold">{{ getMonthName(averageRow.month_name) }}</h3>
                <div 
                  :class="[
                    'text-lg font-bold',
                    averageRow.profit > 0 ? 'text-green-600 dark:text-green-400' : averageRow.profit < 0 ? 'text-red-600 dark:text-red-400' : ''
                  ]"
                >
                  {{ formatCurrency(averageRow.profit) }}
                </div>
              </div>

              <!-- Key Metrics Grid -->
              <div class="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <p class="text-xs text-muted-foreground mb-1">{{ t('monthlyTracking.winRate') }}</p>
                  <p class="text-sm font-semibold">{{ formatPercent(averageRow.win_rate) }}</p>
                </div>
                <div>
                  <p class="text-xs text-muted-foreground mb-1">{{ t('monthlyTracking.totalTrades') }}</p>
                  <p class="text-sm font-semibold">{{ averageRow.total_trades }}</p>
                </div>
              </div>

              <!-- Toggle Button -->
              <div v-if="averageRow.total_trades > 0" class="pt-3 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  @click="toggleAvgExpanded"
                  class="w-full min-h-[44px] justify-between text-sm font-medium hover:bg-muted"
                >
                  <span>{{ isAvgExpanded ? t('monthlyTracking.hideDetails') : t('monthlyTracking.showDetails') }}</span>
                  <ChevronDown 
                    v-if="!isAvgExpanded"
                    class="h-4 w-4 transition-transform"
                  />
                  <ChevronUp 
                    v-else
                    class="h-4 w-4 transition-transform"
                  />
                </Button>
              </div>

              <!-- Detailed Metrics (Collapsible) -->
              <div 
                v-if="averageRow.total_trades > 0 && isAvgExpanded" 
                class="space-y-2 pt-3 border-t"
              >
                <div class="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgProfit') }}:</span>
                    <span class="ml-1 font-medium">{{ formatCurrencyWithPercent(averageRow.avg_profit, averageRow.avg_profit_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.avgLoss') }}:</span>
                    <span class="ml-1 font-medium">{{ formatCurrencyWithPercent(averageRow.avg_loss, averageRow.avg_loss_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.maxProfit') }}:</span>
                    <span class="ml-1 font-medium text-green-600 dark:text-green-400">{{ formatCurrencyWithPercent(averageRow.max_profit, averageRow.max_profit_percent) }}</span>
                  </div>
                  <div>
                    <span class="text-muted-foreground">{{ t('monthlyTracking.maxLoss') }}:</span>
                    <span class="ml-1 font-medium text-red-600 dark:text-red-400">{{ formatCurrencyWithPercent(averageRow.max_loss, averageRow.max_loss_percent) }}</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- Gain/Loss Chart -->
        <Card class="mt-4">
          <CardContent class="p-4 sm:p-6">
            <h2 class="text-lg font-semibold mb-4">{{ t('monthlyTracking.gainLossChart') }}</h2>
            <div v-if="chartData.labels.length === 0" class="text-center py-8 text-muted-foreground">
              {{ t('monthlyTracking.noData') }}
            </div>
            <div v-else class="h-[300px] md:h-[400px]">
              <Bar :data="chartData" :options="chartOptions" />
            </div>
            <!-- Trend Text -->
            <div v-if="monthlyTrend" class="mt-4 pt-4 border-t flex items-center gap-2">
              <TrendingUp 
                v-if="monthlyTrend.type === 'up'" 
                class="h-4 w-4 text-green-600 dark:text-green-400" 
              />
              <TrendingDown 
                v-else-if="monthlyTrend.type === 'down'" 
                class="h-4 w-4 text-red-600 dark:text-red-400" 
              />
              <span 
                :class="[
                  'text-sm font-medium',
                  monthlyTrend.type === 'up' ? 'text-green-600 dark:text-green-400' : 
                  monthlyTrend.type === 'down' ? 'text-red-600 dark:text-red-400' : 
                  'text-muted-foreground'
                ]"
              >
                {{ monthlyTrend.message }}
              </span>
            </div>
          </CardContent>
        </Card>

      </div>

      <!-- No Data State -->
      <div v-else class="text-center py-8 text-muted-foreground">
        <p>{{ t('monthlyTracking.noData') }}</p>
      </div>
    </div>

    <!-- Bottom Navigation (Mobile Only) -->
    <BottomNavigation />
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
