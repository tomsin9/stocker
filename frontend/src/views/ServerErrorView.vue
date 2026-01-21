<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom flex items-center justify-center p-4 md:p-6 lg:p-8">
    <div class="max-w-2xl w-full text-center">
      <div class="space-y-6">
        <div class="error-code text-8xl md:text-9xl font-bold leading-none text-foreground mb-4">
          500
        </div>
        
        <h1 class="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
          {{ t('errors.serverError.title') }}
        </h1>
        
        <p class="text-lg text-muted-foreground max-w-md mx-auto">
          {{ t('errors.serverError.message') }}
        </p>
        
        <div class="flex flex-col sm:flex-row gap-3 justify-center mt-8">
          <Button as-child variant="default" class="min-h-[44px]">
            <router-link to="/">
              {{ t('common.backToHome') }}
            </router-link>
          </Button>
          
          <Button 
            @click="retry" 
            variant="outline"
            class="min-h-[44px]"
          >
            {{ t('common.retry') }}
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'

const router = useRouter()
const { t } = useI18n()

const retry = () => {
  // Try to reload the previous route or go to home
  if (window.history.length > 1) {
    window.location.reload()
  } else {
    router.push('/')
  }
}
</script>

<style scoped>
.error-code {
  font-family: 'Noto Serif TC', 'Noto Serif', serif;
}

@media (max-width: 768px) {
  .error-code {
    font-size: 5rem;
  }
}
</style>
