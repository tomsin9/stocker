<script setup>
import { provideCurrency } from '@/composables/useCurrency'
import SideNavigation from '@/components/SideNavigation.vue'

// 提供貨幣狀態給子組件
provideCurrency()
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
  </div>
</template>