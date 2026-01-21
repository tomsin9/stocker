<script setup>
import { ref, watch, computed } from 'vue'
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
  },
  cashflow: {
    type: Object,
    default: null // 編輯模式時傳入的現金流數據
  }
})

const emit = defineEmits(['update:open', 'success'])

// 計算是否為編輯模式
const isEditMode = computed(() => !!props.cashflow)

const cashFlowData = ref({
  amount: 0,
  type: 'DEPOSIT',
  currency: 'USD',
  date: new Date().toISOString().split('T')[0],
  notes: ''
})
const isSubmitting = ref(false)

// 標題和描述
const title = computed(() => {
  if (isEditMode.value) {
    return props.cashflow.action === 'DEPOSIT' 
      ? t('cashflow.depositTitle') 
      : t('cashflow.withdrawTitle')
  }
  return cashFlowData.value.type === 'DEPOSIT' 
    ? t('cashflow.depositTitle') 
    : t('cashflow.withdrawTitle')
})

const description = computed(() => {
  if (isEditMode.value) {
    return props.cashflow.action === 'DEPOSIT' 
      ? t('cashflow.depositDescription') 
      : t('cashflow.withdrawDescription')
  }
  return cashFlowData.value.type === 'DEPOSIT' 
    ? t('cashflow.depositDescription') 
    : t('cashflow.withdrawDescription')
})

const submitCashFlow = async () => {
  // 防止重複提交
  if (isSubmitting.value) {
    return
  }
  
  isSubmitting.value = true
  try {
    const data = {
      amount: cashFlowData.value.amount,
      type: isEditMode.value 
        ? (props.cashflow.action === 'DEPOSIT' ? 'DEPOSIT' : 'WITHDRAW')
        : cashFlowData.value.type,
      currency: cashFlowData.value.currency,
      date: cashFlowData.value.date,
      notes: cashFlowData.value.notes || ''
    }
    
    if (isEditMode.value) {
      await api.put(`/cashflow/${props.cashflow.id}/`, data)
    } else {
      await api.post('/cashflow/', data)
    }
    
    emit('update:open', false)
    // 重置表單
    cashFlowData.value = {
      amount: 0,
      type: 'DEPOSIT',
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

// 監聽 modal 打開，初始化數據
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    if (isEditMode.value && props.cashflow) {
      // 編輯模式：載入現有數據
      cashFlowData.value = {
        amount: props.cashflow.amount || 0,
        type: props.cashflow.action === 'DEPOSIT' ? 'DEPOSIT' : 'WITHDRAW',
        currency: props.cashflow.currency || 'USD',
        date: props.cashflow.date ? new Date(props.cashflow.date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
        notes: props.cashflow.notes || ''
      }
    } else {
      // 新增模式：重置表單
      cashFlowData.value = {
        amount: 0,
        type: 'DEPOSIT',
        currency: 'USD',
        date: new Date().toISOString().split('T')[0],
        notes: ''
      }
    }
  }
})
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>{{ title }}</SheetTitle>
        <SheetDescription>
          {{ description }}
        </SheetDescription>
      </SheetHeader>
      <div class="grid gap-4 py-4">
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.amount') }}</label>
          <Input 
            v-model.number="cashFlowData.amount" 
            type="number" 
            step="0.01"
            :placeholder="t('cashflow.amountPlaceholder')"
            class="min-h-[44px]"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.currency') }}</label>
          <Select v-model="cashFlowData.currency" class="min-h-[44px]">
            <option value="USD">{{ t('dashboard.usd') }}</option>
            <option value="HKD">{{ t('dashboard.hkd') }}</option>
          </Select>
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.date') }}</label>
          <Input 
            v-model="cashFlowData.date" 
            type="date"
            class="min-h-[44px]"
          />
        </div>
        <div class="grid gap-2">
          <label class="text-sm font-medium">{{ t('cashflow.notes') }}</label>
          <Input 
            v-model="cashFlowData.notes" 
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
