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

const portfolio = ref([])
const isLoading = ref(false)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

const fetchAssets = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`${API_BASE}/dashboard/`)
    portfolio.value = response.data.positions || []
  } catch (error) {
    console.error('Failed to fetch assets', error)
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

const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchAssets()
})
</script>

<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom">
    <div class="container mx-auto p-4 md:p-6 lg:p-8">
      <!-- Sticky Header -->
      <div class="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b pb-4 mb-4 -mx-4 md:-mx-6 lg:-mx-8 px-4 md:px-6 lg:px-8">
        <div class="flex items-center gap-3 mb-2">
          <Button 
            variant="ghost" 
            size="icon"
            @click="goBack"
            class="md:hidden min-h-[44px] min-w-[44px] active:scale-95"
          >
            <ArrowLeft class="h-5 w-5" />
          </Button>
          <div class="flex-1">
            <h1 class="text-2xl font-bold tracking-tight">{{ t('assets.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">{{ t('assets.description') }}</p>
          </div>
        </div>
      </div>

      <!-- Assets List -->
      <div v-if="isLoading" class="text-center py-8 text-muted-foreground">
        {{ t('common.loading') }}
      </div>
      <div v-else-if="portfolio.length === 0" class="text-center py-8 text-muted-foreground">
        {{ t('assets.noAssets') }}
      </div>
      <div v-else class="space-y-3">
        <Card 
          v-for="item in portfolio" 
          :key="item.symbol"
          class="active:scale-[0.98] transition-transform"
        >
          <CardContent class="p-4">
            <div class="flex justify-between items-start">
              <div class="flex-1">
                <div class="font-semibold text-lg mb-1">{{ item.symbol }}</div>
                <div class="text-sm text-muted-foreground">
                  {{ t('dashboard.quantity') }}: {{ item.quantity?.toLocaleString() || 0 }}
                </div>
                <div class="text-sm text-muted-foreground">
                  {{ t('dashboard.avgCost') }}: {{ formatCurrency(item.avg_cost || 0) }}
                </div>
              </div>
              <div class="text-right">
                <div class="font-semibold text-lg">
                  {{ formatCurrency(item.current_market_value || 0) }}
                </div>
                <div 
                  :class="[
                    'text-sm font-medium mt-1',
                    item.unrealized_pl >= 0 ? 'text-green-600' : 'text-red-600'
                  ]"
                >
                  {{ item.unrealized_pl >= 0 ? '+' : '' }}{{ formatCurrency(Math.abs(item.unrealized_pl || 0)) }}
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
