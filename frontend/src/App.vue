<script setup>
import { provideCurrency } from '@/composables/useCurrency'
import { provideAddOptions } from '@/composables/useAddOptions'
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import AppSidebar from '@/components/AppSidebar.vue'
import AddOptionsModal from '@/components/AddOptionsModal.vue'

// 提供貨幣狀態給子組件
provideCurrency()

// 提供新增選項狀態給子組件
provideAddOptions()
</script>

<template>
  <SidebarProvider>
    <AppSidebar />
    <SidebarInset>
      <div class="flex-1 pb-16 md:pb-0">
        <router-view />
      </div>
    </SidebarInset>
    <AddOptionsModal />
  </SidebarProvider>
</template>
