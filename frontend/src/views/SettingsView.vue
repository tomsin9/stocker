<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Globe, Moon, Sun, DollarSign, ArrowLeft, LogOut, Info, Upload, Download } from 'lucide-vue-next'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { injectCurrency } from '@/composables/useCurrency'
import { useTheme } from '@/composables/useTheme'
import BottomNavigation from '@/components/BottomNavigation.vue'
import api from '@/api'
import ImportCSVSheet from '@/components/ImportCSVSheet.vue'
import { APP_INFO } from '@/config/app'

const { locale, t } = useI18n()
const router = useRouter()
const { currentCurrency, switchCurrency } = injectCurrency()
const { theme, toggleTheme } = useTheme()

const showImportSheet = ref(false)
const handleImportSuccess = () => {
  window.dispatchEvent(new CustomEvent('dashboardRefresh'))
}

const isDownloadingTemplate = ref(false)
const downloadTemplate = async () => {
  if (isDownloadingTemplate.value) return
  isDownloadingTemplate.value = true
  try {
    const { data } = await api.get('/trades-csv-template/', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = 'trades_csv_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    console.error(e)
    alert(e.response?.data?.error || 'Download failed')
  } finally {
    isDownloadingTemplate.value = false
  }
}

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
            class="min-h-[44px] min-w-[44px] active:scale-95 md:hidden"
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

        <Card>
          <CardHeader>
            <CardTitle>{{ t('dashboard.importCSV') }}</CardTitle>
            <CardDescription>{{ t('dashboard.importCSVDescription') }}</CardDescription>
          </CardHeader>
          <CardContent class="flex flex-col gap-3 lg:flex-row lg:gap-4">
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95 lg:flex-1"
              @click="showImportSheet = true"
            >
              <Upload class="h-4 w-4 mr-2" />
              {{ t('dashboard.importCSV') }}
            </Button>
            <Button 
              variant="outline" 
              class="w-full justify-start min-h-[44px] active:scale-95 lg:flex-1"
              :disabled="isDownloadingTemplate"
              @click="downloadTemplate"
            >
              <Download class="h-4 w-4 mr-2" />
              {{ t('dashboard.downloadCSVTemplate') }}
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

    <!-- Import CSV Sheet -->
    <ImportCSVSheet 
      v-model:open="showImportSheet"
      @success="handleImportSuccess"
    />

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
  padding-bottom: env(safe-area-inset-bottom);
}

@media (min-width: 768px) {
  .safe-area-bottom {
    padding-bottom: 0;
  }
}
</style>
