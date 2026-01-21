<template>
  <div class="min-h-screen bg-background pb-20 md:pb-0 safe-area-bottom flex items-center justify-center p-4 md:p-6 lg:p-8">
    <div class="max-w-2xl w-full text-center">
      <div class="space-y-6">
        <div class="error-code text-8xl md:text-9xl font-bold leading-none text-foreground mb-4">
          {{ errorCode }}
        </div>
        
        <h1 class="text-3xl md:text-4xl font-bold tracking-tight text-foreground">
          {{ errorTitle }}
        </h1>
        
        <p class="text-lg text-muted-foreground max-w-md mx-auto">
          {{ errorMessage }}
        </p>
        
        <div v-if="errorDetails" class="mt-6 p-4 bg-muted rounded-lg border-l-4 border-destructive text-left">
          <p class="text-sm text-muted-foreground break-words">
            {{ errorDetails }}
          </p>
        </div>
        
        <div class="flex flex-col sm:flex-row gap-3 justify-center mt-8">
          <Button as-child variant="default" class="min-h-[44px]">
            <router-link to="/">
              {{ t('common.backToHome') }}
            </router-link>
          </Button>
          
          <Button 
            v-if="canRetry" 
            @click="retry" 
            variant="outline"
            class="min-h-[44px]"
          >
            {{ t('common.retry') }}
          </Button>
          
          <Button 
            v-else 
            @click="goBack" 
            variant="outline"
            class="min-h-[44px]"
          >
            {{ t('errors.goBack') }}
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// Get error information from route params or query
const errorCode = computed(() => {
  return route.params.code || route.query.code || '500'
})

const errorTitle = computed(() => {
  const code = errorCode.value
  if (code === '404') {
    return t('errors.notFound.title')
  } else if (code === '500') {
    return t('errors.serverError.title')
  } else if (code === '403') {
    return t('errors.forbidden.title')
  } else if (code === '401') {
    return t('errors.unauthorized.title')
  } else {
    return t('errors.generic.title')
  }
})

const errorMessage = computed(() => {
  const code = errorCode.value
  if (code === '404') {
    return t('errors.notFound.message')
  } else if (code === '500') {
    return t('errors.serverError.message')
  } else if (code === '403') {
    return t('errors.forbidden.message')
  } else if (code === '401') {
    return t('errors.unauthorized.message')
  } else {
    return t('errors.generic.message')
  }
})

const errorDetails = computed(() => {
  return route.query.details || route.params.details || null
})

const canRetry = computed(() => {
  const code = errorCode.value
  return code === '500' || code === '503' || code === '502'
})

const goBack = () => {
  if (window.history.length > 1) {
    router.go(-1)
  } else {
    router.push('/')
  }
}

const retry = () => {
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
