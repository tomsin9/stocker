<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Globe, Moon, Sun, DollarSign, ArrowLeft, LogOut, Info } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { injectCurrency } from '@/composables/useCurrency'
import { useTheme } from '@/composables/useTheme'
import BottomNavigation from '@/components/BottomNavigation.vue'
import { APP_INFO } from '@/config/app'

const { locale, t } = useI18n()
const router = useRouter()
const { currentCurrency, switchCurrency } = injectCurrency()
const { theme, toggleTheme } = useTheme()

const toggleLocale = () => {
  const newLocale = locale.value === 'zh-HK' ? 'en' : 'zh-HK'
  locale.value = newLocale
  localStorage.setItem('locale', newLocale)
}

const goBack = () => {
  router.back()
}

const handleLogout = () => {
  // 清除所有本地存儲的認證信息
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  
  // 跳轉到登入頁
  router.push('/login')
}

const showAboutDialog = ref(false)
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
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
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

        <!-- About & License -->
        <Card>
          <CardHeader>
            <CardTitle>{{ t('settings.about') }}</CardTitle>
            <CardDescription>{{ t('settings.aboutDescription') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95"
              @click="showAboutDialog = true"
            >
              <Info class="h-4 w-4 mr-2" />
              {{ t('settings.viewAbout') }}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{{ t('settings.logout') }}</CardTitle>
            <CardDescription>{{ t('settings.logoutDescription') }}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95 text-red-500 hover:text-red-700 hover:bg-destructive/10"
              @click="handleLogout"
            >
              <LogOut class="h-4 w-4 mr-2" />
              {{ t('settings.logout') }}
            </Button>
          </CardContent>
        </Card>

      </div>
    </div>

    <!-- About Dialog -->
    <Dialog v-model:open="showAboutDialog">
      <DialogContent class="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{{ t('settings.about') }}</DialogTitle>
          <DialogDescription>{{ t('settings.aboutDescription') }}</DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-4">
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <Info class="h-5 w-5 text-muted-foreground" />
              <a 
                :href="APP_INFO.repository" target="_blank" 
                rel="noopener noreferrer" 
                class="font-semibold text-lg underline text-primary">
                {{ APP_INFO.name }}
              </a>
            </div>
            <p class="text-sm text-muted-foreground ml-7">
              {{ t('settings.appDescription') }}
            </p>
          </div>
          
          <div class="space-y-3 pt-2 border-t">
            <div class="space-y-1">
              <span class="text-sm font-medium">{{ t('settings.appVersion') }}:</span>
              <span class="text-sm text-muted-foreground ml-2">{{ APP_INFO.version }}</span>
            </div>
            <div class="space-y-1">
              <span class="text-sm font-medium">{{ t('settings.author') }}:</span>
              <a 
                :href="`mailto:${APP_INFO.authorEmail}`" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-sm text-muted-foreground ml-2 underline hover:text-primary"
              >
                {{ APP_INFO.author }}
              </a>
            </div>
            <div class="space-y-1">
              <span class="text-sm font-medium">{{ t('settings.license') }}:</span>
              <a 
                :href="APP_INFO.licenseUrl" 
                target="_blank" 
                rel="noopener noreferrer"
                class="text-sm text-muted-foreground ml-2 underline hover:text-primary"
              >
                {{ APP_INFO.license }}
              </a>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>

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
