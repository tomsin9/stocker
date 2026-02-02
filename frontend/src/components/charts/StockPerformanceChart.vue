<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js'
import { useI18n } from 'vue-i18n'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import api from '@/api'
import { generateChartColors } from '@/lib/chartColors'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend)

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
  marketFilter: {
    type: String,
    default: 'all' // 'all', 'US', 'HK'
  }
})

const { t } = useI18n()

const isLoading = ref(false)
const period = ref('1y')
const interval = ref('1d')
const selectedStocks = ref([])
const stockHistoryData = ref({})
const showSP500 = ref(false)
const showHSI = ref(false)
const isMobile = ref(false)

// 指數符號
const INDEX_SYMBOLS = {
  SP500: '^GSPC',
  HSI: '^HSI'
}

const periods = [
  { value: '1mo', label: '1M' },
  { value: '3mo', label: '3M' },
  { value: '6mo', label: '6M' },
  { value: '1y', label: '1Y' },
  { value: '2y', label: '2Y' },
  { value: '5y', label: '5Y' },
  { value: 'max', label: 'Max' }
]

// 獲取股票歷史數據
const fetchStockHistory = async (symbol) => {
  try {
    // 這裡我們需要一個新的 API 端點來獲取單個股票的歷史數據
    // 暫時使用 yfinance 在前端獲取（如果可能）或通過後端
    // 為了簡化，我們可以創建一個新的 API 端點
    const response = await api.get('/stock-history/', {
      params: {
        symbol: symbol,
        period: period.value,
        interval: interval.value
      }
    })
    return response.data
  } catch (error) {
    console.error(`Failed to fetch history for ${symbol}`, error)
    return null
  }
}

// 獲取所有選中股票的歷史數據
const fetchAllStockHistory = async () => {
  const symbolsToFetch = [...selectedStocks.value]
  
  // 如果選擇了指數，添加到獲取列表
  if (showSP500.value) {
    symbolsToFetch.push(INDEX_SYMBOLS.SP500)
  }
  if (showHSI.value) {
    symbolsToFetch.push(INDEX_SYMBOLS.HSI)
  }

  if (symbolsToFetch.length === 0) {
    stockHistoryData.value = {}
    return
  }

  isLoading.value = true
  const data = {}
  
  for (const symbol of symbolsToFetch) {
    const history = await fetchStockHistory(symbol)
    if (history && history.dates && history.prices) {
      data[symbol] = {
        dates: history.dates,
        prices: history.prices
      }
    }
  }

  stockHistoryData.value = data
  isLoading.value = false
}

// 切換股票選擇
const toggleStock = (symbol) => {
  const index = selectedStocks.value.indexOf(symbol)
  if (index > -1) {
    selectedStocks.value.splice(index, 1)
  } else {
    selectedStocks.value.push(symbol)
  }
  fetchAllStockHistory()
}

// 切換時間範圍
const changePeriod = (newPeriod) => {
  period.value = newPeriod
  if (newPeriod === '1mo' || newPeriod === '3mo') {
    interval.value = '1d'
  } else if (newPeriod === '6mo' || newPeriod === '1y') {
    interval.value = '1d'
  } else {
    interval.value = '1wk'
  }
  fetchAllStockHistory()
}

// 切換指數顯示
const toggleIndex = (indexType) => {
  if (indexType === 'SP500') {
    showSP500.value = !showSP500.value
  } else if (indexType === 'HSI') {
    showHSI.value = !showHSI.value
  }
  fetchAllStockHistory()
}

// 計算圖表數據
const chartData = computed(() => {
  // 構建所有要顯示的符號列表
  const symbolsToDisplay = [...selectedStocks.value]
  if (showSP500.value) {
    symbolsToDisplay.push(INDEX_SYMBOLS.SP500)
  }
  if (showHSI.value) {
    symbolsToDisplay.push(INDEX_SYMBOLS.HSI)
  }

  if (symbolsToDisplay.length === 0 || Object.keys(stockHistoryData.value).length === 0) {
    return {
      labels: [],
      datasets: []
    }
  }

  // 找到所有日期（取交集或並集）
  let allDates = []
  for (const symbol of symbolsToDisplay) {
    if (stockHistoryData.value[symbol] && stockHistoryData.value[symbol].dates) {
      allDates = [...new Set([...allDates, ...stockHistoryData.value[symbol].dates])]
    }
  }
  allDates.sort()

  // 使用共享的顏色生成函數（在 computed 中執行，確保 CSS 變量已注入）
  const colors = generateChartColors(35)

  // 為每個選中的股票和指數創建數據集
  const datasets = symbolsToDisplay.map((symbol, index) => {
    const stockData = stockHistoryData.value[symbol]
    if (!stockData || !stockData.prices) {
      return null
    }

    // 將價格數據對齊到統一的日期
    const prices = allDates.map(date => {
      const dateIndex = stockData.dates.indexOf(date)
      if (dateIndex >= 0) {
        return stockData.prices[dateIndex]
      }
      // 如果該日期沒有數據，使用前一個有效值
      return null
    })

    // 計算相對表現（以第一個價格為基準，顯示百分比變化）
    const firstPrice = prices.find(p => p !== null)
    const normalizedPrices = firstPrice ? prices.map(p => p !== null ? ((p / firstPrice) - 1) * 100 : null) : prices

    // 判斷是否為指數
    const isIndex = symbol === INDEX_SYMBOLS.SP500 || symbol === INDEX_SYMBOLS.HSI
    
    // 為指數和股票使用動態顏色
    let color
    if (symbol === INDEX_SYMBOLS.SP500) {
      // S&P 500 使用股票數量之後的第一個顏色索引
      const colorIndex = selectedStocks.value.length
      color = colors[colorIndex % colors.length] || 'hsl(12, 76%, 61%)'
    } else if (symbol === INDEX_SYMBOLS.HSI) {
      // HSI 使用股票數量之後的第二個顏色索引
      const colorIndex = selectedStocks.value.length + 1
      color = colors[colorIndex % colors.length] || 'hsl(12, 76%, 61%)'
    } else {
      // 股票使用循環顏色
      const stockIndex = selectedStocks.value.indexOf(symbol)
      color = colors[stockIndex % colors.length] || 'hsl(12, 76%, 61%)'
    }

    // 將 HSL 顏色轉換為 HSLA（添加透明度）
    const toHSLA = (hsl, alpha = 0.2) => {
      if (!hsl) return null
      if (hsl.startsWith('hsl(')) {
        return hsl.replace('hsl(', 'hsla(').replace(')', `, ${alpha})`)
      }
      // 如果是 hex 顏色，轉換為 rgba
      if (hsl.startsWith('#')) {
        const hex = hsl.replace('#', '')
        const r = parseInt(hex.substring(0, 2), 16)
        const g = parseInt(hex.substring(2, 4), 16)
        const b = parseInt(hex.substring(4, 6), 16)
        return `rgba(${r}, ${g}, ${b}, ${alpha})`
      }
      return null
    }

    // 獲取顯示標籤
    let label = symbol
    if (symbol === INDEX_SYMBOLS.SP500) {
      label = t('assets.sp500')
    } else if (symbol === INDEX_SYMBOLS.HSI) {
      label = t('assets.hsi')
    }
    
    return {
      label: label,
      data: normalizedPrices,
      borderColor: color,
      backgroundColor: toHSLA(color) || color + '20',
      tension: 0, 
      fill: false,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderDash: isIndex ? [5, 5] : [], // 指數使用虛線
      borderWidth: isIndex ? 2 : 1.5,
      spanGaps: true
    }
  }).filter(d => d !== null)

  return {
    labels: allDates,
    datasets: datasets
  }
})

// 檢測是否為移動設備
const checkMobile = () => {
  if (typeof window !== 'undefined') {
    isMobile.value = window.innerWidth < 768
  }
}

// 格式化日期根據時間範圍
const formatDate = (dateString) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  
  // 根據 period 決定格式
  const shortPeriods = ['1mo', '3mo', '6mo']
  const isShortPeriod = shortPeriods.includes(period.value)
  
  if (isShortPeriod) {
    // 1M/3M/6M: DD/MM
    const day = String(date.getDate()).padStart(2, '0')
    const month = String(date.getMonth() + 1).padStart(2, '0')
    return `${day}/${month}`
  } else {
    // 1Y/2Y/5Y/Max: MM/YYYY
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const year = date.getFullYear()
    return `${month}/${year}`
  }
}

const chartOptions = computed(() => {
  const mobile = isMobile.value
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: {
      legend: {
        position: 'top',
        display: !mobile, // 在手機上隱藏 legend
        labels: {
          usePointStyle: true,
          padding: mobile ? 10 : 15,
          font: {
            size: mobile ? 10 : 12
          }
        }
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            return `${label}: ${value !== null ? value.toFixed(2) + '%' : 'N/A'}`
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: !mobile, // 在手機上隱藏標題
          text: t('assets.date')
        },
        ticks: {
          maxTicksLimit: mobile ? 4 : 6,
          callback: function(value, index) {
            const label = this.getLabelForValue(value)
            return formatDate(label)
          },
          font: {
            size: mobile ? 10 : 12
          }
        }
      },
      y: {
        display: true,
        title: {
          display: !mobile, // 在手機上隱藏標題
          text: t('assets.performancePercentage')
        },
        ticks: {
          maxTicksLimit: mobile ? 4 : 6,
          callback: function(value) {
            return value.toFixed(1) + '%'
          },
          font: {
            size: mobile ? 10 : 12
          }
        }
      }
    }
  }
})

// 初始化選中的股票
const initializeSelectedStocks = () => {
  if (props.portfolio && props.portfolio.length > 0) {
    // 獲取當前 portfolio 中的 symbol 列表
    const availableSymbols = props.portfolio.map(item => item.symbol)
    
    // 過濾出仍然存在的股票
    const validStocks = selectedStocks.value.filter(symbol => 
      availableSymbols.includes(symbol)
    )
    
    // 如果沒有有效的股票，或者需要補充到5個，則更新
    if (validStocks.length === 0 || validStocks.length < Math.min(5, availableSymbols.length)) {
      // 保留仍然存在的股票，然後添加新的股票直到5個
      const newStocks = [...validStocks]
      for (const symbol of availableSymbols) {
        if (!newStocks.includes(symbol) && newStocks.length < 5) {
          newStocks.push(symbol)
        }
      }
      selectedStocks.value = newStocks
    } else {
      // 如果所有選中的股票都仍然存在，保持不變
      selectedStocks.value = validStocks
    }
    
    // 重新獲取歷史數據
    fetchAllStockHistory()
  } else {
    // 如果 portfolio 為空，清空選中的股票和數據
    selectedStocks.value = []
    stockHistoryData.value = {}
  }
}

// 初始化：選擇前5個股票
onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  initializeSelectedStocks()
})

// 清理事件監聽器
onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', checkMobile)
  }
})

// 監聽 portfolio 變化（當 filter 改變時會觸發）
watch(() => props.portfolio, (newPortfolio, oldPortfolio) => {
  // 檢查 portfolio 是否真的改變了（比較 symbol 列表）
  const newSymbols = (newPortfolio || []).map(item => item.symbol).sort().join(',')
  const oldSymbols = (oldPortfolio || []).map(item => item.symbol).sort().join(',')
  
  if (newSymbols !== oldSymbols) {
    initializeSelectedStocks()
  }
}, { deep: true })

// 監聽 marketFilter 變化，自動選擇對應的指數
watch(() => props.marketFilter, (newFilter) => {
  if (newFilter === 'US') {
    // US 市場：自動選中 S&P 500
    showSP500.value = true
    showHSI.value = false
  } else if (newFilter === 'HK') {
    // HK 市場：自動選中 HSI
    showSP500.value = false
    showHSI.value = true
  } else {
    // 'all' 市場：保持當前狀態（不清除指數選擇）
    // 用戶可以手動選擇指數
  }
  // 重新獲取數據
  fetchAllStockHistory()
}, { immediate: true })
</script>

<template>
  <Card>
    <CardHeader>
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
        <div>
          <CardTitle class="text-lg sm:text-xl">{{ t('assets.stockPerformanceChart') }}</CardTitle>
          <CardDescription class="text-xs sm:text-sm">{{ t('assets.stockPerformanceChartDescription') }}</CardDescription>
        </div>
        <div class="flex flex-wrap gap-1.5 sm:gap-2 overflow-x-auto pb-1">
          <Button
            v-for="p in periods"
            :key="p.value"
            :variant="period === p.value ? 'default' : 'outline'"
            size="sm"
            @click="changePeriod(p.value)"
            class="min-w-[60px] sm:min-w-[50px] min-h-[44px] sm:min-h-[36px] text-xs sm:text-sm whitespace-nowrap"
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
      <div v-else-if="selectedStocks.length === 0 && !showSP500 && !showHSI" class="text-center py-8 text-muted-foreground">
        {{ t('assets.selectStocksToCompare') }}
      </div>
      <div v-else-if="Object.keys(stockHistoryData).length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('assets.noHistoryData') }}
      </div>
      <div v-else class="h-[350px] sm:h-[300px] md:h-[400px] mb-3 sm:mb-4">
        <Line :data="chartData" :options="chartOptions" />
      </div>

      <!-- Stock Selection -->
      <div v-if="portfolio && portfolio.length > 0" class="mb-3 sm:mb-4 p-3 sm:p-4 bg-muted/50 rounded-lg">
        <div class="text-xs sm:text-sm font-medium mb-2">{{ t('assets.selectStocks') }}:</div>
        <div class="flex flex-wrap gap-2 sm:gap-3">
          <label
            v-for="item in portfolio"
            :key="item.symbol"
            class="flex items-center gap-2 cursor-pointer min-h-[44px] sm:min-h-auto"
          >
            <input
              type="checkbox"
              :checked="selectedStocks.includes(item.symbol)"
              @change="toggleStock(item.symbol)"
              class="w-5 h-5 sm:w-4 sm:h-4 rounded border-gray-300 flex-shrink-0"
            />
            <span class="text-xs sm:text-sm">{{ item.symbol }}</span>
          </label>
        </div>
      </div>

      <!-- Index Selection -->
      <div class="mb-3 sm:mb-4 p-3 sm:p-4 bg-muted/50 rounded-lg">
        <div class="text-xs sm:text-sm font-medium mb-2">{{ t('assets.selectIndices') }}:</div>
        <div class="flex flex-wrap gap-2 sm:gap-3">
          <label class="flex items-center gap-2 cursor-pointer min-h-[44px] sm:min-h-auto">
            <input
              type="checkbox"
              :checked="showSP500"
              @change="toggleIndex('SP500')"
              class="w-5 h-5 sm:w-4 sm:h-4 rounded border-gray-300 flex-shrink-0"
            />
            <span class="text-xs sm:text-sm">{{ t('assets.sp500') }}</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer min-h-[44px] sm:min-h-auto">
            <input
              type="checkbox"
              :checked="showHSI"
              @change="toggleIndex('HSI')"
              class="w-5 h-5 sm:w-4 sm:h-4 rounded border-gray-300 flex-shrink-0"
            />
            <span class="text-xs sm:text-sm">{{ t('assets.hsi') }}</span>
          </label>
        </div>
      </div>

    </CardContent>
  </Card>
</template>
