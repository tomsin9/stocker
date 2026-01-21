<script setup>
import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import api from '@/api'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  mode: {
    type: String,
    default: 'add', // 'add' or 'edit'
    validator: (value) => ['add', 'edit'].includes(value)
  },
  transaction: {
    type: Object,
    default: null // 編輯模式時傳入的交易數據
  }
})

const emit = defineEmits(['update:open', 'success'])

// 計算是否為編輯模式
const isEditMode = computed(() => props.mode === 'edit')

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
const isSubmitting = ref(false)

// 搜索股票
const searchStocks = async (query) => {
  if (!query || query.trim().length < 1) {
    stockSuggestions.value = []
    showSuggestions.value = false
    return
  }
  
  isSearchingStocks.value = true
  try {
    const response = await api.get('/search-stocks/', {
      params: { q: query.trim() }
    })
    stockSuggestions.value = response.data.stocks || []
    showSuggestions.value = stockSuggestions.value.length > 0
    selectedStockIndex.value = -1
  } catch (error) {
    console.error('Failed to search stocks', error)
    stockSuggestions.value = []
    showSuggestions.value = false
  } finally {
    isSearchingStocks.value = false
  }
}

// 處理符號輸入
const handleSymbolInput = (event) => {
  const value = event.target.value
  newTrade.value.symbol = value
  clearFieldError('symbol')
  if (value.trim().length >= 1) {
    searchStocks(value)
  } else {
    stockSuggestions.value = []
    showSuggestions.value = false
  }
}

// 處理鍵盤導航
const handleSymbolKeydown = (event) => {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (selectedStockIndex.value < stockSuggestions.value.length - 1) {
      selectedStockIndex.value++
    }
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (selectedStockIndex.value > 0) {
      selectedStockIndex.value--
    }
  } else if (event.key === 'Enter' && selectedStockIndex.value >= 0) {
    event.preventDefault()
    selectStock(stockSuggestions.value[selectedStockIndex.value])
  } else if (event.key === 'Escape') {
    showSuggestions.value = false
  }
}

// 選擇股票
const selectStock = (stock) => {
  newTrade.value.symbol = stock.symbol
  showSuggestions.value = false
  selectedStockIndex.value = -1
  clearFieldError('symbol')
}

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
  
  // 驗證股票代號（僅在添加模式下驗證）
  if (!isEditMode.value && (!newTrade.value.symbol || newTrade.value.symbol.trim() === '')) {
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
  // 防止重複提交
  if (isSubmitting.value) {
    return
  }
  
  // 先進行表單驗證
  if (!validateTrade()) {
    return
  }
  
  isSubmitting.value = true
  try {
    if (isEditMode.value && props.transaction) {
      // 編輯模式：使用 PUT 更新
      await api.put(`/transactions/${props.transaction.id}/`, newTrade.value)
    } else {
      // 添加模式：使用 POST 創建
      await api.post('/add-transaction/', newTrade.value)
    }
    
    emit('update:open', false)
    // 重置表單和錯誤
    resetForm()
    emit('success')
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
      if (errorMessage && (errorMessage.toLowerCase().includes('股票') || 
          errorMessage.toLowerCase().includes('symbol') ||
          errorMessage.toLowerCase().includes('stock'))) {
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
  } finally {
    isSubmitting.value = false
  }
}

// 重置表單
const resetForm = () => {
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
  stockSuggestions.value = []
  showSuggestions.value = false
  selectedStockIndex.value = -1
}

// 初始化編輯表單
const initEditForm = () => {
  if (!props.transaction) {
    return
  }
  
  // 處理日期格式
  let dateStr = props.transaction.date
  if (dateStr instanceof Date) {
    dateStr = dateStr.toISOString().split('T')[0]
  } else if (typeof dateStr === 'string') {
    dateStr = dateStr.split('T')[0]
  }
  
  // 確保 symbol 字段正確設置
  // 優先順序：transaction.symbol > transaction.asset.symbol
  let symbol = props.transaction.symbol || ''
  if (!symbol && props.transaction.asset) {
    symbol = props.transaction.asset.symbol || ''
  }
  
  newTrade.value = {
    symbol: symbol,
    action: props.transaction.action || 'BUY',
    date: dateStr,
    price: parseFloat(props.transaction.price || 0),
    quantity: parseFloat(props.transaction.quantity || 0),
    fees: parseFloat(props.transaction.fees || 0)
  }
}

// 監聽 modal 打開/關閉
watch(() => props.open, async (isOpen) => {
  if (!isOpen) {
    // Modal 關閉時清除所有錯誤和建議
    resetForm()
  } else {
    // Modal 打開時初始化表單
    // 使用 nextTick 確保 transaction prop 已經更新
    await nextTick()
    if (isEditMode.value && props.transaction) {
      initEditForm()
    } else {
      resetForm()
    }
  }
})

// 監聽 transaction prop 變化（編輯模式下）
watch(() => props.transaction, () => {
  if (props.open && isEditMode.value && props.transaction) {
    initEditForm()
  }
}, { deep: true, immediate: true })
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>{{ isEditMode ? t('transaction.editTransaction') : t('transaction.title') }}</SheetTitle>
        <SheetDescription>
          {{ isEditMode ? (t('transaction.editDescription') || t('transaction.description')) : t('transaction.description') }}
        </SheetDescription>
      </SheetHeader>
      <div class="grid gap-4 py-4">
        <div class="grid gap-2 relative">
          <label class="text-sm font-medium">{{ t('transaction.symbol') }}</label>
          <div class="relative">
            <Input 
              v-if="isEditMode"
              :value="newTrade.symbol"
              disabled
              class="min-h-[44px] bg-muted"
            />
            <Input 
              v-else
              v-model="newTrade.symbol" 
              :placeholder="t('transaction.symbolPlaceholder')"
              :class="cn('min-h-[44px]', tradeErrors.symbol && 'border-red-500 focus-visible:ring-red-500')"
              @input="handleSymbolInput"
              @keydown="handleSymbolKeydown"
              @focus="searchStocks(newTrade.symbol)"
              @blur="setTimeout(() => { showSuggestions = false }, 200)"
              autocomplete="off"
            />
            <!-- Auto-complete 建議列表（僅在添加模式下顯示） -->
            <div 
              v-if="!isEditMode && showSuggestions && stockSuggestions.length > 0"
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
            <!-- 加載指示器（僅在添加模式下顯示） -->
            <div 
              v-if="!isEditMode && isSearchingStocks"
              class="absolute right-3 top-1/2 -translate-y-1/2"
            >
              <RefreshCw class="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          </div>
          <p v-if="!isEditMode && tradeErrors.symbol" class="text-sm text-red-500">{{ tradeErrors.symbol }}</p>
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
        <Button variant="outline" @click="emit('update:open', false)" :disabled="isSubmitting" class="min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button>
        <Button @click="submitTrade" :disabled="isSubmitting" class="min-h-[44px] active:scale-95">{{ isSubmitting ? t('common.saving') || t('common.save') : t('common.save') }}</Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
