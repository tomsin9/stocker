<script setup>
  import { computed, ref, onMounted } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { useI18n } from 'vue-i18n'
  import { Button } from '@/components/ui/button'
  import { Home, History, Package, Settings, DollarSign, Globe, Moon, Sun, ChevronLeft, ChevronRight } from 'lucide-vue-next'
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
  
  onMounted(() => {
    const savedState = localStorage.getItem('sidebarCollapsed')
    if (savedState !== null) {
      isCollapsed.value = savedState === 'true'
    }
  })
  
  const toggleCollapse = () => {
    isCollapsed.value = !isCollapsed.value
    localStorage.setItem('sidebarCollapsed', isCollapsed.value.toString())
  }
  
  const navItems = computed(() => [
    { name: 'home', path: '/', icon: Home, label: t('navigation.overview') },
    { name: 'transactions', path: '/transactions', icon: History, label: t('navigation.transactions') },
    { name: 'assets', path: '/assets', icon: Package, label: t('navigation.assets') },
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
        isCollapsed ? 'md:w-[80px]' : 'md:w-[260px]'
      )"
    >
      <div :class="cn('flex items-center border-b my-auto', isCollapsed ? 'justify-center h-[72px]' : 'px-4 h-[72px]')">
        <router-link to="/" :class="cn('flex items-center overflow-hidden group', isCollapsed ? '' : 'gap-3')">
          <div :class="cn(
            'bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20 transition-all duration-300',
            isCollapsed ? 'w-[40px] h-[40px]' : 'w-[40px] h-[40px]'
          )">
            <span class="text-primary-foreground font-black text-2xl italic">S</span>
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
          :class="cn(
            'w-full flex items-center rounded-xl transition-all duration-200 active:scale-95 h-[36px] relative group',
            isCollapsed ? 'justify-center p-0 w-[36px]' : 'px-4 gap-4',
            isActive(item.path) 
              ? 'bg-primary text-primary-foreground shadow-md shadow-primary/20' 
              : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
          )"
          :title="item.label"
        >
          <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          <span :class="cn('font-semibold transition-all duration-300 whitespace-nowrap', isCollapsed ? 'opacity-0 w-0' : 'opacity-100 w-auto')">
            {{ item.label }}
          </span>
          
          <div v-if="isCollapsed" class="absolute left-full ml-4 px-3 py-2 bg-zinc-900 text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50 shadow-xl">
            {{ item.label }}
          </div>
        </button>
      </nav>
  
      <div :class="cn('p-3 border-t bg-muted/20', isCollapsed ? 'p-3 space-y-2' : 'space-y-2')">
      
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

      </div>
    </aside>
</template>