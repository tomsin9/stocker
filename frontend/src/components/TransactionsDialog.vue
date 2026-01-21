<script setup>
import { ref, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Trash2, Pencil } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { injectCurrency } from '@/composables/useCurrency'
import api from '@/api'
import AddTransactionSheet from '@/components/AddTransactionSheet.vue'

const { t } = useI18n()
const { currentCurrency } = injectCurrency()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  },
  symbol: {
    type: String,
    default: ''
  },
  exchangeRate: {
    type: Number,
    default: 7.8
  }
})

const emit = defineEmits(['update:open', 'success'])

const symbolTransactions = ref([])
const isLoadingTransactions = ref(false)
const deletingTransactionId = ref(null)
const showEditSheet = ref(false)
const editingTransaction = ref(null)

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
  
  return `${currencySymbol}${numAmount.toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

// 獲取特定股票的交易列表
const fetchSymbolTransactions = async (symbol) => {
  if (!symbol) return
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

// 打開編輯表單
const openEditForm = async (transaction) => {
  // 確保 transaction 有 symbol 字段
  // 如果 transaction 沒有 symbol，使用 dialog 的 symbol prop
  if (transaction && !transaction.symbol && props.symbol) {
    transaction = { ...transaction, symbol: props.symbol }
  }
  editingTransaction.value = transaction
  // 等待下一個 tick 確保 transaction 已經設置
  await nextTick()
  showEditSheet.value = true
}

// 處理編輯成功
const handleEditSuccess = async () => {
  showEditSheet.value = false
  editingTransaction.value = null
  // 重新獲取交易列表
  await fetchSymbolTransactions(props.symbol)
  emit('success')
}

// 刪除交易
const deleteTransaction = async (transactionId) => {
  // 防止重複提交
  if (deletingTransactionId.value === transactionId) {
    return
  }
  
  if (!confirm(t('transaction.confirmDelete'))) {
    return
  }
  
  deletingTransactionId.value = transactionId
  try {
    await api.delete(`/transactions/${transactionId}/`)
    // 重新獲取交易列表
    await fetchSymbolTransactions(props.symbol)
    emit('success')
  } catch (error) {
    console.error('Failed to delete transaction', error)
    const errorMessage = error.response?.data?.detail || 
                        error.response?.data?.error || 
                        error.response?.data?.message ||
                        error.message || 
                        t('messages.deleteError')
    alert(`${t('messages.deleteError')}: ${errorMessage}`)
  } finally {
    deletingTransactionId.value = null
  }
}

// 監聽 dialog 打開，獲取交易列表
watch(() => props.open, (isOpen) => {
  if (isOpen && props.symbol) {
    fetchSymbolTransactions(props.symbol)
  }
})

// 監聽 symbol 變化
watch(() => props.symbol, (newSymbol) => {
  if (props.open && newSymbol) {
    fetchSymbolTransactions(newSymbol)
  }
})
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent class="max-w-4xl max-h-[90vh] sm:max-h-[90vh] h-[100vh] sm:h-auto overflow-y-auto p-4 sm:p-6 m-0 sm:m-4 rounded-none sm:rounded-lg">
      <DialogHeader>
        <DialogTitle class="text-lg sm:text-xl">{{ t('transaction.viewTransactions') }} - {{ symbol }}</DialogTitle>
        <DialogDescription class="text-xs sm:text-sm">
          {{ t('transaction.description') }}
        </DialogDescription>
      </DialogHeader>
      <div v-if="isLoadingTransactions" class="text-center py-8 text-muted-foreground text-sm">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="symbolTransactions.length === 0" class="text-center py-8 text-muted-foreground text-sm">
        {{ t('transaction.noTransactionsForSymbol') }}
      </div>
      <div v-else>
        <!-- Desktop Table View -->
        <div class="hidden sm:block rounded-md border">
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
                        'px-1 py-0 rounded text-[10px] font-medium border',
                        getMarketColor(tx.symbol || symbol)
                      )"
                    >
                      {{ getMarketType(tx.symbol || symbol) === 'HK' ? 'HK' : 'US' }}
                    </span>
                  </div>
                </TableCell>
                <TableCell class="text-right">{{ tx.quantity?.toLocaleString() || 0 }}</TableCell>
                <TableCell class="text-right">
                  <div>{{ formatCurrency(tx.price || 0, tx.currency) }}</div>
                  <div class="text-xs text-muted-foreground font-medium">{{ tx.currency || 'USD' }}</div>
                </TableCell>
                <TableCell class="text-right">
                  <div>{{ formatCurrency(tx.fees || 0, tx.currency) }}</div>
                  <div class="text-xs text-muted-foreground font-medium">{{ tx.currency || 'USD' }}</div>
                </TableCell>
                <TableCell class="text-center">
                  <div class="flex items-center justify-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="openEditForm(tx)"
                      class="min-h-[32px] min-w-[32px] p-0 text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950"
                      :title="t('common.edit')"
                    >
                      <Pencil class="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      @click="deleteTransaction(tx.id)"
                      :disabled="deletingTransactionId === tx.id"
                      class="min-h-[32px] min-w-[32px] p-0 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50"
                      :title="t('common.delete')"
                    >
                      <Trash2 class="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <!-- Mobile Card List View -->
        <div class="sm:hidden space-y-3">
          <div 
            v-for="tx in symbolTransactions" 
            :key="tx.id"
            class="rounded-lg border p-4 space-y-3 active:scale-[0.98] transition-transform"
          >
            <!-- Header: Date and Action -->
            <div class="flex items-center justify-between pb-2 border-b">
              <div class="text-sm font-medium">
                {{ new Date(tx.date).toLocaleDateString() }}
              </div>
              <div class="flex items-center gap-2">
                <span 
                  :class="[
                    'px-2 py-1 rounded text-xs font-medium',
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
                    'px-1 py-0 rounded text-[10px] font-medium border',
                    getMarketColor(tx.symbol || symbol)
                  )"
                >
                  {{ getMarketType(tx.symbol || symbol) === 'HK' ? 'HK' : 'US' }}
                </span>
              </div>
            </div>

            <!-- Transaction Details Grid -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <p class="text-xs text-muted-foreground mb-1">{{ t('transaction.quantity') }}</p>
                <p class="text-sm font-semibold">{{ tx.quantity?.toLocaleString() || 0 }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground mb-1">{{ t('transaction.price') }}</p>
                <div>
                  <p class="text-sm font-semibold">{{ formatCurrency(tx.price || 0, tx.currency) }}</p>
                  <p class="text-xs text-muted-foreground font-medium">{{ tx.currency || 'USD' }}</p>
                </div>
              </div>
              <div>
                <p class="text-xs text-muted-foreground mb-1">{{ t('transaction.fees') }}</p>
                <div>
                  <p class="text-sm font-semibold">{{ formatCurrency(tx.fees || 0, tx.currency) }}</p>
                  <p class="text-xs text-muted-foreground font-medium">{{ tx.currency || 'USD' }}</p>
                </div>
              </div>
              <div>
                <p class="text-xs text-muted-foreground mb-1">Total</p>
                <div>
                  <p class="text-sm font-semibold">
                    {{ formatCurrency((tx.price || 0) * (tx.quantity || 0) + (tx.fees || 0), tx.currency) }}
                  </p>
                  <p class="text-xs text-muted-foreground font-medium">{{ tx.currency || 'USD' }}</p>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-2 pt-2 border-t">
              <Button
                variant="outline"
                size="sm"
                @click="openEditForm(tx)"
                class="flex-1 min-h-[44px] text-blue-600 hover:text-blue-700 hover:bg-blue-50 dark:hover:bg-blue-950"
              >
                <Pencil class="h-4 w-4 mr-2" />
                {{ t('common.edit') }}
              </Button>
              <Button
                variant="outline"
                size="sm"
                @click="deleteTransaction(tx.id)"
                :disabled="deletingTransactionId === tx.id"
                class="flex-1 min-h-[44px] text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950 disabled:opacity-50"
              >
                <Trash2 class="h-4 w-4 mr-2" />
                {{ t('common.delete') }}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>

  <!-- Edit Transaction Sheet (使用共用的 AddTransactionSheet 組件) -->
  <AddTransactionSheet 
    v-model:open="showEditSheet"
    mode="edit"
    :transaction="editingTransaction"
    @success="handleEditSuccess"
  />
</template>
