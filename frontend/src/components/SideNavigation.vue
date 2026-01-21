<script setup>
  import { computed, ref, onMounted, nextTick } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useI18n } from 'vue-i18n'
  import { Button } from '@/components/ui/button'
  import { Home, History, Settings, DollarSign, Globe, Moon, Sun, ChevronLeft, ChevronRight, User, ChartBar } from 'lucide-vue-next'
  import { cn } from '@/lib/utils'
  import { injectCurrency } from '@/composables/useCurrency'
  import { useTheme } from '@/composables/useTheme'
  
  const props = defineProps({
    onAddClick: { type: Function, default: null }
  })
  
  const route = useRoute()
  const router = useRouter()
  const { t, locale } = useI18n()
  const { currentCurrency, switchCurrency } = injectCurrency()
  const { theme, toggleTheme } = useTheme()
  
  const isCollapsed = ref(false)
  const username = ref(null)
  const hasAccessToken = ref(false)
  const tooltipState = ref({ show: false, text: '', x: 0, y: 0 })
  
  // 檢查是否有 access token
  const checkAccessToken = () => {
    try {
      hasAccessToken.value = !!localStorage.getItem('access_token')
    } catch (error) {
      hasAccessToken.value = false
    }
  }
  
  // 從 localStorage 獲取用戶名（只使用登入時保存的 username，不使用 user_id）
  const loadUsername = () => {
    try {
      const storedUsername = localStorage.getItem('username')
      if (storedUsername) {
        username.value = storedUsername
        // console.log('Username loaded from localStorage:', storedUsername)
      } else {
        // 如果沒有保存的 username，不從 JWT token 解析（因為 JWT 中可能只有 user_id）
        // 用戶需要重新登入以保存 username
        username.value = null
        // console.warn('No username found in localStorage. Please login again to save username.')
      }
    } catch (error) {
      console.error('Failed to access localStorage:', error)
      username.value = null
    }
  }
  
  onMounted(() => {
    const savedState = localStorage.getItem('sidebarCollapsed')
    if (savedState !== null) {
      isCollapsed.value = savedState === 'true'
    }
    // 載入用戶名
    loadUsername()
    
    // 監聽 storage 事件，以便在其他標籤頁登入/登出時更新
    window.addEventListener('storage', (e) => {
      if (e.key === 'username') {
        username.value = e.newValue
      }
    })
    
    // 監聽自定義事件，當登入成功時更新 username
    window.addEventListener('user-login', () => {
      loadUsername()
    })
    
    // 定期檢查 username（以防在其他地方更新）
    const checkInterval = setInterval(() => {
      const currentUsername = localStorage.getItem('username')
      if (currentUsername !== username.value) {
        username.value = currentUsername
      }
    }, 1000)
    
    // 清理定時器
    return () => {
      clearInterval(checkInterval)
    }
  })
  
  const toggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value
    localStorage.setItem('sidebarCollapsed', isCollapsed.value.toString())
  }
  
  // 處理 tooltip 顯示
  const showTooltip = (event, text) => {
    if (!isCollapsed.value) return
    const rect = event.currentTarget.getBoundingClientRect()
    tooltipState.value = {
      show: true,
      text,
      x: rect.right + 16, // 64px sidebar width + 16px margin
      y: rect.top + rect.height / 2
    }
  }
  
  const hideTooltip = () => {
    tooltipState.value.show = false
  }
  
  const navItems = computed(() => [
    { name: 'home', path: '/', icon: Home, label: t('navigation.overview') },
    { name: 'monthly-tracking', path: '/monthly-tracking', icon: ChartBar, label: t('navigation.monthlyTracking') },
    { name: 'transactions', path: '/transactions', icon: History, label: t('navigation.transactions') },
    { name: 'settings', path: '/settings', icon: Settings, label: t('navigation.settings') },
  ])
  
  const isActive = (path) => route.path === path
  
  const handleClick = (item) => {
    if (item.path) router.push(item.path)
  }
  
  const toggleLocale = () => {
    const newLocale = locale.value === 'zh-HK' ? 'en' : 'zh-HK'
    locale.value = newLocale
    localStorage.setItem('locale', newLocale)
  }
</script>
  
<template>
    <aside 
      :class="cn(
        'hidden md:flex md:flex-col md:h-screen md:sticky md:top-0 md:border-r md:bg-card transition-all duration-300 ease-in-out',
        isCollapsed ? 'md:w-[64px]' : 'md:w-[260px]'
      )"
    >
      <div :class="cn('flex items-center border-b my-auto', isCollapsed ? 'justify-center h-[72px]' : 'px-4 h-[72px]')">
        <router-link to="/" :class="cn('flex items-center overflow-hidden group', isCollapsed ? '' : 'gap-3')">
          <div :class="cn(
            'rounded-xl flex items-center justify-center shadow-lg shadow-primary/20 transition-all duration-300 overflow-hidden',
            isCollapsed ? 'w-[40px] h-[40px]' : 'w-[40px] h-[40px]'
          )">
            <img 
              src="/favicon/apple-touch-icon.png" 
              alt="Stocker" 
              class="w-full h-full object-cover"
            />
          </div>
          <span :class="cn('text-xl font-bold transition-all duration-300 whitespace-nowrap', isCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto')">
            Stocker
          </span>
        </router-link>
      </div>
  
      <nav class="flex-1 px-3 py-6 space-y-3 overflow-y-auto overflow-x-hidden" :class="isCollapsed ? 'mx-auto' : ''">
        <button
          v-for="item in navItems"
          :key="item.name"
          @click="handleClick(item)"
          @mouseenter="(e) => showTooltip(e, item.label)"
          @mouseleave="hideTooltip"
          :class="cn(
            'w-full flex items-center rounded-xl transition-all duration-200 active:scale-95 h-[36px] relative group',
            isCollapsed ? 'justify-center p-0 w-[36px]' : 'px-4 gap-4',
            isActive(item.path) 
              ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20' 
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          )"
        >
          <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          <span :class="cn('font-semibold transition-all duration-300 whitespace-nowrap', isCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto')">
            {{ item.label }}
          </span>
        </button>
      </nav>
      
      <!-- Fixed tooltip for navigation items -->
      <Teleport to="body">
        <div
          v-if="isCollapsed && tooltipState.show"
          class="fixed px-3 py-2 bg-zinc-900 dark:bg-zinc-800 text-white text-xs rounded-lg pointer-events-none whitespace-nowrap z-[99999] shadow-xl transition-opacity"
          :style="{
            left: tooltipState.x + 'px',
            top: tooltipState.y + 'px',
            transform: 'translateY(-50%)'
          }"
        >
          {{ tooltipState.text }}
        </div>
      </Teleport>

      <div :class="cn('p-4 border-t bg-muted/20 space-y-4', isCollapsed ? 'p-3' : 'p-4')">

        <div :class="cn('grid gap-1', isCollapsed ? 'grid-cols-1 justify-items-center' : 'grid-cols-2')">
          <Button 
            variant="ghost" 
            :class="cn(
              'transition-all duration-300 bg-background/50 border border-transparent hover:border-border relative group',
              isCollapsed ? 'h-10 w-10 rounded-full p-0' : 'h-10 rounded-xl px-0'
              )"
            @click="toggleTheme"
          >
            <Sun v-if="theme === 'light'" class="h-4 w-4" />
            <Moon v-else class="h-4 w-4" />
            <span v-if="!isCollapsed" class="ml-2 text-[11px]">{{ theme === 'light' ? '淺色' : '深色' }}</span>
            <div 
              v-if="isCollapsed" 
              class="absolute left-full ml-4 px-3 py-2 bg-zinc-900 dark:bg-zinc-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-xl"
            >
              {{ theme === 'light' ? '淺色' : '深色' }}
            </div>
          </Button>

          <Button 
            variant="ghost" 
            :class="cn(
              'transition-all duration-300 bg-background/50 border border-transparent hover:border-border relative group',
              isCollapsed ? 'h-10 w-10 rounded-full p-0' : 'h-10 rounded-xl px-0'
            )"
            @click="toggleLocale"
          >
            <Globe class="h-4 w-4" />
            <span v-if="!isCollapsed" class="ml-2 text-[11px]">{{ locale === 'zh-HK' ? '中文（香港）' : 'English' }}</span>
            <div 
              v-if="isCollapsed" 
              class="absolute left-full ml-4 px-3 py-2 bg-zinc-900 dark:bg-zinc-800 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-xl"
            >
              {{ locale === 'zh-HK' ? '中文（香港）' : 'English' }}
            </div>
          </Button>
        </div>

        <div :class="cn('grid gap-1', isCollapsed ? 'grid-cols-1 justify-items-center' : 'grid-cols-2')">
          <button 
            :class="cn(
              'transition-all duration-300 bg-background/50 border border-transparent hover:border-border flex items-center justify-center',
              isCollapsed ? 'h-10 w-10 rounded-full p-0' : 'h-10 rounded-xl px-0'
            )"
            @click="toggleCollapse"
          >
            <ChevronLeft v-if="!isCollapsed" class="h-4 w-4" />
            <ChevronRight v-else class="h-4 w-4" />
          </button>

          <div 
            v-if="username || hasAccessToken" 
            :class="cn(
              'flex items-center rounded-xl transition-all duration-300 relative group',
              isCollapsed ? 'justify-center h-10 w-10 rounded-full p-0 hidden' : 'justify-start px-3 py-2 gap-2'
            )"
          >
            <User 
              :class="cn(
                'flex-shrink-0 transition-all duration-300',
                isCollapsed ? 'h-4 w-4 text-foreground' : 'h-4 w-4 text-muted-foreground'
              )" 
            />
            <span 
              :class="cn(
                'text-sm font-medium text-foreground truncate transition-all duration-300',
                isCollapsed ? 'opacity-0 w-0 overflow-hidden absolute' : 'opacity-100 w-auto'
              )"
            >
              {{ username || 'User' }}
            </span>
            <div 
              v-if="isCollapsed" 
              class="absolute left-full ml-4 px-3 py-2 bg-zinc-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-xl"
            >
              {{ username || 'User' }}
            </div>
          </div>
        </div>

      </div>
  
      <!-- <div :class="cn('p-3 border-t bg-muted/20', isCollapsed ? 'p-3 space-y-2' : 'space-y-2')">
      
        <div :class="cn('grid gap-2', isCollapsed ? 'grid-cols-2' : 'grid-cols-2')">
          <Button 
            variant="outline" 
            :class="cn(
              'rounded-xl active:scale-90 p-0 flex items-center justify-center transition-all border shadow-sm w-full',
              isCollapsed ? 'h-[28px] w-[28px]' : 'h-[28px]'
            )"
            @click="toggleTheme"
          >
            <Sun v-if="theme === 'light'" :class="cn(isCollapsed ? 'h-4 w-4' : 'h-5 w-5')" />
            <Moon v-else :class="cn(isCollapsed ? 'h-4 w-4' : 'h-5 w-5')" />
            <span v-if="!isCollapsed" class="ml-2 text-xs font-medium">{{ theme === 'light' ? '淺色' : '深色' }}</span>
          </Button>

          <Button 
            variant="outline" 
            :class="cn(
              'rounded-xl active:scale-90 p-0 flex items-center justify-center transition-all border shadow-sm w-full',
              isCollapsed ? 'h-[28px] w-[28px]' : 'h-[28px]'
            )"
            @click="toggleLocale"
          >
            <Globe :class="cn(isCollapsed ? 'h-4 w-4' : 'h-5 w-5')" />
            <span v-if="!isCollapsed" class="ml-2 text-xs font-medium">{{ locale === 'zh-HK' ? '繁中' : 'EN' }}</span>
          </Button>
        </div>

        <div :class="cn('grid gap-2', isCollapsed ? 'grid-cols-2' : 'grid-cols-[1fr_44px]')">
          <Button 
            variant="outline" 
            :class="cn(
              'rounded-xl active:scale-90 p-0 flex items-center transition-all border shadow-sm w-full',
              isCollapsed ? 'h-[28px] w-[28px] justify-center' : 'h-[28px] justify-start px-3'
            )"
            @click="switchCurrency"
          >
            <DollarSign :class="cn('text-primary flex-shrink-0', isCollapsed ? 'h-4 w-4' : 'h-5 w-5')" />
            <span v-if="!isCollapsed" class="ml-2 text-xs font-bold">{{ currentCurrency }} ({{ currentCurrency === 'USD' ? '美金' : '港幣' }})</span>
          </Button>

          <Button 
            variant="ghost" 
            :class="cn(
              'rounded-xl active:scale-90 p-0 flex items-center justify-center transition-all border shadow-sm',
              isCollapsed ? 'h-[28px] w-[28px]' : 'h-[28px]'
            )"
            @click="toggleCollapse"
          >
            <ChevronLeft v-if="!isCollapsed" class="h-5 w-5" />
            <ChevronRight v-else class="h-4 w-4" />
          </Button>
        </div>

      </div> -->
    </aside>
</template>