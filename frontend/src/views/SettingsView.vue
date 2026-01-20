<script setup>
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Globe, Moon, Sun, DollarSign, ArrowLeft } from 'lucide-vue-next'
import { provideCurrency } from '@/composables/useCurrency'
import { useTheme } from '@/composables/useTheme'
import BottomNavigation from '@/components/BottomNavigation.vue'

const { locale, t } = useI18n()
const router = useRouter()
const { currentCurrency, switchCurrency } = provideCurrency()
const { theme, toggleTheme } = useTheme()

const toggleLocale = () => {
  const newLocale = locale.value === 'zh-HK' ? 'en' : 'zh-HK'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="min-h-screen bg-background pb-20 safe-area-bottom">
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
            <h1 class="text-2xl font-bold tracking-tight">{{ t('settings.title') }}</h1>
            <p class="text-sm text-muted-foreground mt-1">{{ t('settings.description') }}</p>
          </div>
        </div>
      </div>

      <!-- Settings Cards -->
      <div class="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>{{ t('settings.appearance') }}</CardTitle>
            <CardDescription>{{ t('settings.appearanceDescription') }}</CardDescription>
          </CardHeader>
          <CardContent class="space-y-3">
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95"
              @click="toggleTheme"
            >
              <Sun v-if="theme === 'light'" class="h-4 w-4 mr-2" />
              <Moon v-else class="h-4 w-4 mr-2" />
              {{ t('settings.theme') }}: {{ theme === 'light' ? t('settings.light') : t('settings.dark') }}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{{ t('settings.language') }}</CardTitle>
            <CardDescription>{{ t('settings.languageDescription') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95"
              @click="toggleLocale"
            >
              <Globe class="h-4 w-4 mr-2" />
              {{ locale === 'zh-HK' ? '繁體中文 (香港)' : 'English' }}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{{ t('settings.currency') }}</CardTitle>
            <CardDescription>{{ t('settings.currencyDescription') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95"
              @click="switchCurrency"
            >
              <DollarSign class="h-4 w-4 mr-2" />
              {{ currentCurrency === 'USD' ? t('dashboard.usd') : t('dashboard.hkd') }}
            </Button>
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
