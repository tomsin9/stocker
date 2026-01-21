<script setup>
import { ref, onMounted, computed } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/api'
import { getCSSVariable } from '@/lib/chartColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

const props = defineProps({
  exchangeRate: {
    type: Number,
    default: 7.8
  }
})

const { t } = useI18n()

const isLoading = ref(false)
const period = ref('1y')
const interval = ref('1d')
const historyData = ref({
  dates: [],
  portfolio_values: [],
  cash_values: [],
  total_values: []
})

const periods = [
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '2y', label: '2Y' },
  { value: '5y', label: '5Y' },
  { value: 'max', label: 'Max' }
]

// 獲取歷史數據
const fetchHistory = async () => {
  isLoading.value = true
  try {
    const response = await api.get('/portfolio-history/', {
      params: {
        period: period.value,
        interval: interval.value
      }
    })
    historyData.value = response.data
  } catch (error) {
    console.error('Failed to fetch portfolio history', error)
    historyData.value = {
      dates: [],
      portfolio_values: [],
      cash_values: [],
      total_values: []
    }
  } finally {
    isLoading.value = false
  }
}

// 計算圖表數據
const chartData = computed(() => {
  if (!historyData.value.dates || historyData.value.dates.length === 0) {
    return {
      labels: [],
      datasets: []
    }
  }

  const chart1 = getCSSVariable('--chart-1')
  const chart2 = getCSSVariable('--chart-2')
  const chart3 = getCSSVariable('--chart-3')
  
  // 將 HSL 顏色轉換為 HSLA（添加透明度）
  const toHSLA = (hsl, alpha = 0.1) => {
    if (!hsl) return null
    if (hsl.startsWith('hsl(')) {
      return hsl.replace('hsl(', 'hsla(').replace(')', `, ${alpha})`)
    }
    return null
  }
  
  return {
    labels: historyData.value.dates,
    datasets: [
      {
        label: t('assets.portfolioValue'),
        data: historyData.value.portfolio_values,
        borderColor: chart1 || 'hsl(12, 76%, 61%)',
        backgroundColor: toHSLA(chart1) || 'hsla(12, 76%, 61%, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: t('assets.cashValue'),
        data: historyData.value.cash_values,
        borderColor: chart2 || 'hsl(173, 58%, 39%)',
        backgroundColor: toHSLA(chart2) || 'hsla(173, 58%, 39%, 0.1)',
        tension: 0.4,
        fill: true
      },
      {
        label: t('assets.totalValue'),
        data: historyData.value.total_values,
        borderColor: chart3 || 'hsl(197, 37%, 24%)',
        backgroundColor: toHSLA(chart3) || 'hsla(197, 37%, 24%, 0.1)',
        tension: 0.4,
        fill: false,
        borderWidth: 2
      }
    ]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false
  },
  plugins: {
    legend: {
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: 15,
        font: {
          size: 12
        }
      }
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          const label = context.dataset.label || ''
          const value = context.parsed.y || 0
          return `${label}: $${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        }
      }
    }
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: t('assets.date')
      },
      ticks: {
        maxTicksLimit: 10
      }
    },
    y: {
      display: true,
      title: {
        display: true,
        text: t('assets.value')
      },
      ticks: {
        callback: function(value) {
          return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
        }
      }
    }
  }
}

// 切換時間範圍
const changePeriod = (newPeriod) => {
  period.value = newPeriod
  // 根據時間範圍調整 interval
  if (newPeriod === '1mo' || newPeriod === '3mo') {
    interval.value = '1d'
  } else if (newPeriod === '6mo' || newPeriod === '1y') {
    interval.value = '1d'
  } else {
    interval.value = '1wk'
  }
  fetchHistory()
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <CardTitle>{{ t('assets.portfolioHistoryChart') }}</CardTitle>
          <CardDescription>{{ t('assets.portfolioHistoryChartDescription') }}</CardDescription>
        </div>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="p in periods"
            :key="p.value"
            :variant="period === p.value ? 'default' : 'outline'"
            size="sm"
            @click="changePeriod(p.value)"
            class="min-w-[50px]"
          >
            {{ p.label }}
          </Button>
        </div>
      </div>
    </CardHeader>
    <CardContent>
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="!historyData.dates || historyData.dates.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('assets.noHistoryData') }}
      </div>
      <div v-else class="h-[300px] md:h-[400px]">
        <Line :data="chartData" :options="chartOptions" />
      </div>
    </CardContent>
  </Card>
</template>
