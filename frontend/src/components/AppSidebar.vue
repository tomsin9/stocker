<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Home, History, Settings, Globe, Moon, Sun, User, ChartBar, PanelLeftClose, PanelLeft, LogOut, ChevronsUpDown } from 'lucide-vue-next'
import { useTheme } from '@/composables/useTheme'

const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
const { theme, toggleTheme } = useTheme()
const { state, toggleSidebar, isMobile } = useSidebar()

const username = ref(null)

const loadUsername = () => {
  try {
    username.value = localStorage.getItem('username') || null
  } catch {
    username.value = null
  }
}

const onStorage = (e) => {
  if (e.key === 'username') username.value = e.newValue
}

onMounted(() => {
  loadUsername()
  window.addEventListener('storage', onStorage)
  window.addEventListener('user-login', loadUsername)
})

onUnmounted(() => {
  window.removeEventListener('storage', onStorage)
  window.removeEventListener('user-login', loadUsername)
})

const toggleLocale = () => {
  const next = locale.value === 'zh-HK' ? 'en' : 'zh-HK'
  locale.value = next
  localStorage.setItem('locale', next)
}

const navItems = computed(() => [
  { name: 'home', path: '/', icon: Home, label: t('navigation.overview') },
  { name: 'monthly-tracking', path: '/monthly-tracking', icon: ChartBar, label: t('navigation.monthlyTracking') },
  { name: 'transactions', path: '/transactions', icon: History, label: t('navigation.transactions') },
  { name: 'settings', path: '/settings', icon: Settings, label: t('navigation.settings') },
])

const isActive = (path) => route.path === path

const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('username')
  username.value = null
  router.push('/login')
}
</script>

<template>
  <Sidebar collapsible="icon">
    <SidebarHeader>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton size="lg" as-child tooltip="Stocker">
            <router-link to="/" class="justify-center">
              <div class="flex aspect-square size-7 shrink-0 items-center justify-center rounded-lg overflow-hidden bg-sidebar-primary text-sidebar-primary-foreground">
                <img src="/favicon/apple-touch-icon.png" alt="Stocker" class="size-full object-cover" />
              </div>
              <div class="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                <span class="truncate font-semibold">Stocker</span>
                <span class="truncate text-xs text-muted-foreground">{{ t('sidebar.subtitle') }}</span>
              </div>
            </router-link>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem class="hidden md:block">
          <SidebarMenuButton :tooltip="state === 'expanded' ? t('sidebar.collapse') : t('sidebar.expand')" @click="toggleSidebar">
            <PanelLeftClose v-if="state === 'expanded'" />
            <PanelLeft v-else />
            <span>{{ state === 'expanded' ? t('sidebar.collapseSidebar') : t('sidebar.expandSidebar') }}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarHeader>

    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="item in navItems" :key="item.name">
              <SidebarMenuButton
                as-child
                :tooltip="item.label"
                :data-active="isActive(item.path)"
              >
                <router-link :to="item.path">
                  <component :is="item.icon" />
                  <span>{{ item.label }}</span>
                </router-link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>

    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <SidebarMenuButton :tooltip="theme === 'light' ? t('sidebar.lightTheme') : t('sidebar.darkTheme')" @click="toggleTheme">
            <Sun v-if="theme === 'light'" />
            <Moon v-else />
            <span>{{ theme === 'light' ? t('sidebar.lightMode') : t('sidebar.darkMode') }}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem>
          <SidebarMenuButton :tooltip="t('sidebar.language')" @click="toggleLocale">
            <Globe />
            <span>{{ locale === 'zh-HK' ? '中文（香港）' : 'English' }}</span>
          </SidebarMenuButton>
        </SidebarMenuItem>
        <SidebarMenuItem v-if="username">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <SidebarMenuButton
                :tooltip="t('sidebar.account')"
                class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
              >
                <User />
                <span>{{ username }}</span>
                <ChevronsUpDown class="ml-auto size-4 group-data-[collapsible=icon]:hidden" />
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              class="w-[--reka-dropdown-menu-trigger-width] min-w-56 rounded-lg"
              :side="isMobile ? 'bottom' : 'right'"
              align="end"
              :side-offset="4"
            >
              <DropdownMenuLabel class="p-0 font-normal">
                <div class="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                  <User class="size-4" />
                  <div class="grid flex-1 text-left text-sm leading-tight">
                    <span class="truncate font-semibold">{{ username }}</span>
                  </div>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem @click="handleLogout" class="cursor-pointer">
                <LogOut class="mr-2 size-4 text-red-500" />
                <span class="text-red-500">{{ t('sidebar.logout') }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>

    <SidebarRail />
  </Sidebar>
</template>
