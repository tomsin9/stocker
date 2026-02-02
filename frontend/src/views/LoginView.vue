<template>
  <div class="min-h-screen bg-background flex items-center justify-center p-4">
    <Card class="w-full max-w-md">
      <CardHeader class="space-y-1">
        <CardTitle class="text-2xl font-bold tracking-tight text-center">
          {{ t('login.title') }}
        </CardTitle>
        <CardDescription class="text-center">
          {{ t('login.description') }}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="space-y-2">
            <label for="username" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {{ t('login.username') }}
            </label>
            <Input
              id="username"
              v-model="form.username"
              type="text"
              required
              :placeholder="t('login.usernamePlaceholder')"
              class="min-h-[44px]"
              :disabled="loading"
            />
          </div>
          <div class="space-y-2">
            <label for="password" class="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
              {{ t('login.password') }}
            </label>
            <Input
              id="password"
              v-model="form.password"
              type="password"
              required
              :placeholder="t('login.passwordPlaceholder')"
              class="min-h-[44px]"
              :disabled="loading"
            />
          </div>
          <!-- Cloudflare Turnstile widget -->
          <div v-if="turnstileSiteKey" class="flex justify-center min-h-[65px]">
            <div ref="turnstileContainer" id="turnstile-container"></div>
          </div>
          <div 
            v-if="error" 
            class="text-sm text-destructive text-center min-h-[20px] py-1"
            role="alert"
            aria-live="polite"
          >
            {{ error }}
          </div>
          <div v-else class="min-h-[20px]"></div>
          <Button
            type="submit"
            :disabled="loading || (!!turnstileSiteKey && !turnstileToken)"
            class="w-full min-h-[44px] active:scale-95"
          >
            {{ loading ? t('login.submitting') : t('login.submit') }}
          </Button>
        </form>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import api from '../api'

const { t } = useI18n()

const router = useRouter()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })

const turnstileSiteKey = ref(import.meta.env.VITE_TURNSTILE_SITE_KEY || '')
const turnstileToken = ref('')
const turnstileContainer = ref(null)
let turnstileWidgetId = null

function renderTurnstile() {
  if (!turnstileSiteKey.value || !turnstileContainer.value || typeof window.turnstile === 'undefined') return
  turnstileWidgetId = window.turnstile.render(turnstileContainer.value, {
    sitekey: turnstileSiteKey.value,
    theme: 'light',
    size: 'normal',
    callback: (token) => {
      turnstileToken.value = token
    },
    'error-callback': () => {
      turnstileToken.value = ''
    },
    'expired-callback': () => {
      turnstileToken.value = ''
    },
  })
}

function resetTurnstile() {
  turnstileToken.value = ''
  if (turnstileWidgetId != null && typeof window.turnstile !== 'undefined') {
    try {
      window.turnstile.reset(turnstileWidgetId)
    } catch (_) {}
  }
}

onMounted(async () => {
  if (!turnstileSiteKey.value) {
    try {
      const res = await api.get('public-config/')
      const key = res.data?.turnstile_site_key
      if (key && typeof key === 'string') turnstileSiteKey.value = key.trim()
    } catch (_) {}
  }
  await nextTick()
  if (!turnstileSiteKey.value) {
    turnstileToken.value = 'skip'
    return
  }
  if (typeof window.turnstile !== 'undefined') {
    renderTurnstile()
  } else {
    window.addEventListener('load', () => {
      if (window.turnstile && window.turnstile.ready) {
        window.turnstile.ready(renderTurnstile)
      } else {
        renderTurnstile()
      }
    })
    if (document.readyState === 'complete') {
      setTimeout(() => {
        if (window.turnstile && window.turnstile.ready) {
          window.turnstile.ready(renderTurnstile)
        } else {
          renderTurnstile()
        }
      }, 300)
    }
  }
})

onUnmounted(() => {
  if (turnstileWidgetId != null && typeof window.turnstile !== 'undefined') {
    try {
      window.turnstile.remove(turnstileWidgetId)
    } catch (_) {}
  }
})

const handleLogin = async () => {
  if (turnstileSiteKey.value && !turnstileToken.value) {
    error.value = t('login.errors.turnstileRequired')
    return
  }
  loading.value = true
  error.value = ''
  try {
    const payload = {
      username: form.username,
      password: form.password,
    }
    if (turnstileSiteKey.value && turnstileToken.value && turnstileToken.value !== 'skip') {
      payload.cf_turnstile_response = turnstileToken.value
    }
    const response = await api.post('/token/', payload)
    
    // 儲存 Token 到本地
    localStorage.setItem('access_token', response.data.access)
    localStorage.setItem('refresh_token', response.data.refresh)
    
    // 儲存 username 到本地（用於顯示）
    localStorage.setItem('username', form.username)
    
    // 觸發自定義事件，通知其他組件更新 username
    window.dispatchEvent(new CustomEvent('user-login', { detail: { username: form.username } }))
    
    // 登入成功後跳轉首頁
    router.push('/')
  } catch (err) {
    // 改進錯誤處理，顯示後端返回的具體錯誤訊息
    if (err.response) {
      // 後端返回的錯誤
      const status = err.response.status
      const data = err.response.data
      
      if (status === 401) {
        // 認證失敗 - 替換後端的英文錯誤訊息為翻譯後的訊息
        const backendError = data.detail || data.error || data.message || ''
        // 檢查是否為常見的認證錯誤訊息，如果是則使用翻譯
        if (backendError.includes('No active account found') || 
            backendError.includes('Unable to log in') ||
            backendError.toLowerCase().includes('credentials')) {
          error.value = t('login.errors.invalidCredentials')
        } else if (backendError) {
          // 如果有其他具體錯誤訊息，顯示原訊息
          error.value = backendError
        } else {
          // 沒有具體錯誤訊息時使用默認翻譯
          error.value = t('login.errors.invalidCredentials')
        }
      } else if (status === 400) {
        const msg = (data.detail || data.error || data.message || '').toString()
        if (msg.toLowerCase().includes('turnstile')) {
          error.value = t('login.errors.turnstileFailed')
        } else {
          error.value = msg || t('login.errors.badRequest')
        }
      } else if (status === 500 || status >= 500) {
        // 伺服器錯誤
        error.value = t('login.errors.serverError')
      } else {
        error.value = data.detail || data.error || data.message || t('login.errors.default')
      }
    } else if (err.request) {
      // 請求已發出但沒有收到回應
      error.value = t('login.errors.networkError')
    } else {
      // 其他錯誤
      const errorMessage = err.message || '未知錯誤'
      error.value = t('login.errors.unknownError', { message: errorMessage })
    }
    if (import.meta.env.DEV) {
      console.error('Login error:', err.response?.status, err.response?.data ?? err.message)
    }
    if (turnstileSiteKey.value) resetTurnstile()
  } finally {
    loading.value = false
  }
}
</script>