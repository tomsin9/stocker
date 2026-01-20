<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Home, History, Package, Settings, Plus } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { injectAddOptions } from '@/composables/useAddOptions'

const props = defineProps({
  onAddClick: { type: Function, default: null }
})

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { openAddOptions } = injectAddOptions()

const navItems = computed(() => [
  { name: 'home', path: '/', icon: Home, label: t('navigation.overview') },
  { name: 'transactions', path: '/transactions', icon: History, label: t('navigation.transactions') },
  { name: 'add', path: null, icon: Plus, label: t('navigation.add'), action: true, onClick: props.onAddClick },
  { name: 'assets', path: '/assets', icon: Package, label: t('navigation.assets') },
  { name: 'settings', path: '/settings', icon: Settings, label: t('navigation.settings') },
])

const isActive = (path) => {
  if (!path) return false
  return route.path === path
}

const handleClick = (item) => {
  if (item.action) {
    // 優先使用全局的 addOptions，如果沒有則使用 prop 的 onClick
    if (openAddOptions) {
      openAddOptions()
    } else if (item.onClick) {
      item.onClick()
    }
  } else if (item.path) {
    router.push(item.path)
  }
}
</script>

<template>
  <!-- Mobile Only: Bottom Navigation -->
  <nav 
    class="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-background border-t border-border safe-area-bottom"
  >
    <div class="container mx-auto px-2">
      <div class="flex justify-around items-center h-16">
        <button
          v-for="item in navItems"
          :key="item.name"
          @click="handleClick(item)"
          :class="cn(
            'flex flex-col items-center justify-center gap-1 flex-1 h-full min-h-[44px] transition-all active:scale-95',
            isActive(item.path) ? 'text-primary' : 'text-muted-foreground',
            item.action ? 'text-primary' : ''
          )"
        >
          <component :is="item.icon" class="h-5 w-5" />
          <span class="text-xs font-medium">{{ item.label }}</span>
        </button>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.safe-area-bottom {
  padding-bottom: env(safe-area-inset-bottom);
}
</style>
