<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { Doughnut } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { generateChartColors, getCSSVariable } from '@/lib/chartColors'

ChartJS.register(ArcElement, Tooltip, Legend)

const isMobile = ref(false)

// 檢測是否為移動設備
const checkMobile = () => {
  if (typeof window !== 'undefined') {
    isMobile.value = window.innerWidth < 768
  }
}

const props = defineProps({
  portfolio: {
    type: Array,
    required: true,
    default: () => []
  },
  exchangeRate: {
    type: Number,
    default: 7.8
  },
  cash: {
    type: Number,
    default: 0
  }
})

const { t } = useI18n()

// 計算資產分配數據
const chartData = computed(() => {
  // 計算總市值（只計算正數持倉，做空不計入分配）
  const stockValue = (props.portfolio || []).reduce((sum, item) => {
    const value = parseFloat(item.current_market_value || 0)
    return sum + (value > 0 ? value : 0)
  }, 0)

  // 包含現金的總價值
  const cashValue = parseFloat(props.cash || 0)
  const totalValue = stockValue + cashValue

  if (totalValue === 0) {
    return {
      labels: [],
      datasets: [{
        data: [],
        backgroundColor: []
      }]
    }
  }

  // 使用共享的顏色生成函數
  const colors = generateChartColors(35)

  // 過濾出正數持倉並計算佔比
  const stockAllocations = (props.portfolio || [])
    .filter(item => parseFloat(item.current_market_value || 0) > 0)
    .map((item, index) => {
      const value = parseFloat(item.current_market_value || 0)
      const percentage = (value / totalValue) * 100
      return {
        symbol: item.symbol,
        value: value,
        percentage: percentage,
        color: colors[index % colors.length] || 'hsl(12, 76%, 61%)' // 確保不為 null
      }
    })

  // 添加現金（如果有），使用動態顏色
  const allocations = [...stockAllocations]
  if (cashValue > 0) {
    // 現金使用下一個可用的顏色索引
    const cashColorIndex = stockAllocations.length % colors.length
    allocations.push({
      symbol: t('assets.cashValue'),
      value: cashValue,
      percentage: (cashValue / totalValue) * 100,
      color: colors[cashColorIndex] || 'hsl(12, 76%, 61%)' // 動態顏色，確保不為 null
    })
  }

  // 按市值排序
  allocations.sort((a, b) => b.value - a.value)

  // 格式化貨幣值
  const formatCurrency = (value) => {
    return `$${value.toLocaleString('en-US', { 
      minimumFractionDigits: 2, 
      maximumFractionDigits: 2 
    })}`
  }

  return {
    labels: allocations.map(item => {
      return `${item.symbol}: ${formatCurrency(item.value)} (${item.percentage.toFixed(1)}%)`
    }),
    datasets: [{
      data: allocations.map(item => item.value),
      backgroundColor: allocations.map(item => item.color),
      borderWidth: 2,
      borderColor: getCSSVariable('--background') || '#ffffff'
    }]
  }
})

const chartOptions = computed(() => {
  const mobile = isMobile.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: mobile ? 'bottom' : 'right',
        labels: {
          padding: mobile ? 10 : 15,
          usePointStyle: true,
          font: {
            size: mobile ? 10 : 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.label || ''
            // label 格式已經是 "Symbol: $value (percentage%)"，直接返回
            return label
          }
        }
      }
    }
  }
})

onMounted(() => {
  checkMobile()
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', checkMobile)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', checkMobile)
  }
})
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ t('assets.allocationChart') }}</CardTitle>
      <CardDescription>{{ t('assets.allocationChartDescription') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="(!portfolio || portfolio.length === 0) && (!cash || cash === 0)" class="text-center py-8 text-muted-foreground">
        {{ t('assets.noAssets') }}
      </div>
      <div v-else class="h-[300px]">
        <Doughnut :data="chartData" :options="chartOptions" />
      </div>
    </CardContent>
  </Card>
</template>
