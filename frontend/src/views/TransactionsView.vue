<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ArrowLeft } from 'lucide-vue-next'
import { injectCurrency } from '@/composables/useCurrency'
import BottomNavigation from '@/components/BottomNavigation.vue'

const { t } = useI18n()
const router = useRouter()
const { currentCurrency } = injectCurrency()

const goBack = () => {
  router.back()
}

const transactions = ref([])
const isLoading = ref(false)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

const fetchTransactions = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`${API_BASE}/transactions/`)
    transactions.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch transactions', error)
  } finally {
    isLoading.value = false
  }
}

const formatCurrency = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return currentCurrency.value === 'HKD' ? 'HK$0.00' : '$0.00'
  }
  const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount
  const currencySymbol = currentCurrency.value === 'HKD' ? 'HK$' : '$'
  return `${currencySymbol}${Math.abs(numAmount).toLocaleString('en-US', { 
    minimumFractionDigits: 2, 
    maximumFractionDigits: 2 
  })}`
}

onMounted(() => {
  fetchTransactions()
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 mb-4">
        <div class="flex items-center gap-3 mb-2">
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
          :key="tx.id"
          class="active:scale-[0.98] transition-transform"
        >
          <CardContent class="p-4">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="flex items-center gap-2 mb-1">
                  <span class="font-semibold text-lg">{{ tx.asset?.symbol || tx.symbol || 'N/A' }}</span>
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
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ new Date(tx.date).toLocaleDateString() }}
                </div>
              </div>
              <div class="text-right">
                <div class="font-semibold">{{ formatCurrency(tx.price * tx.quantity) }}</div>
                <div class="text-sm text-muted-foreground">
                  {{ tx.quantity }} @ {{ formatCurrency(tx.price) }}
                </div>
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
  padding-bottom: calc(env(safe-area-inset-bottom) + 4rem);
}

@media (min-width: 768px) {
  .safe-area-bottom {
    padding-bottom: 0;
  }
}
</style>
