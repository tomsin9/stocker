<script setup>
import { provideCurrency } from '@/composables/useCurrency'
import { provideAddOptions } from '@/composables/useAddOptions'
import SideNavigation from '@/components/SideNavigation.vue'
import AddOptionsModal from '@/components/AddOptionsModal.vue'

// 提供貨幣狀態給子組件
provideCurrency()

// 提供新增選項狀態給子組件
provideAddOptions()
</script>

<template>
  <div class="min-h-screen bg-background flex flex-col md:flex-row">
    <!-- Desktop: Side Navigation -->
    <SideNavigation />

    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col min-h-screen md:min-h-0">
      <!-- Router View -->
      <div class="flex-1 pb-16 md:pb-0">
        <router-view />
      </div>
    </main>

    <!-- Global Add Options Modal -->
    <AddOptionsModal />
  </div>
</template>