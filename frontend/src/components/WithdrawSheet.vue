<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import api from '@/api'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:open', 'success'])

const newCashFlow = ref({
  amount: 0,
  type: 'WITHDRAW',
  currency: 'USD',
  date: new Date().toISOString().split('T')[0],
  notes: ''
})
const isSubmitting = ref(false)

const submitCashFlow = async () => {
  // 防止重複提交
  if (isSubmitting.value) {
    return
  }
  
  isSubmitting.value = true
  try {
    const data = {
      ...newCashFlow.value,
      type: 'WITHDRAW'
    }
    await api.post('/cashflow/', data)
    emit('update:open', false)
    // 重置表單
    newCashFlow.value = {
      amount: 0,
      type: 'WITHDRAW',
      currency: 'USD',
      date: new Date().toISOString().split('T')[0],
      notes: ''
    }
    emit('success')
  } catch (e) {
    console.error('Save cashflow error:', e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.saveError')
    alert(`${t('messages.saveError')}: ${errorMessage}`)
  } finally {
    isSubmitting.value = false
  }
}

// 監聽 modal 關閉，重置表單
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    newCashFlow.value = {
      amount: 0,
      type: 'WITHDRAW',
      currency: 'USD',
      date: new Date().toISOString().split('T')[0],
      notes: ''
    }
  }
})
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>{{ t('cashflow.withdrawTitle') }}</SheetTitle>
        <SheetDescription>
          {{ t('cashflow.withdrawDescription') }}
        </SheetDescription>
      </SheetHeader>
      <div class="grid gap-4 py-4">
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.amount') }}</label>
          <Input 
            v-model.number="newCashFlow.amount" 
            type="number" 
            step="0.01"
            :placeholder="t('cashflow.amountPlaceholder')"
            class="min-h-[44px]"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.currency') }}</label>
          <Select v-model="newCashFlow.currency" class="min-h-[44px]">
            <option value="USD">{{ t('dashboard.usd') }}</option>
            <option value="HKD">{{ t('dashboard.hkd') }}</option>
          </Select>
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.date') }}</label>
          <Input 
            v-model="newCashFlow.date" 
            type="date"
            class="min-h-[44px]"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.notes') }}</label>
          <Input 
            v-model="newCashFlow.notes" 
            :placeholder="t('cashflow.notesPlaceholder')"
            class="min-h-[44px]"
          />
        </div>
      </div>
      <SheetFooter>
        <Button variant="outline" @click="emit('update:open', false)" :disabled="isSubmitting" class="min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button>
        <Button @click="submitCashFlow" :disabled="isSubmitting" class="min-h-[44px] active:scale-95">{{ isSubmitting ? t('common.saving') || t('common.save') : t('common.save') }}</Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
