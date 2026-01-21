<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Upload } from 'lucide-vue-next'
import api from '@/api'

const { t } = useI18n()

const props = defineProps({
  open: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:open', 'success'])

const isSubmitting = ref(false)

const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  // 防止重複提交
  if (isSubmitting.value) {
    return
  }
  
  isSubmitting.value = true
  const formData = new FormData()
  formData.append('file', file)
  try {
    await api.post('/import-csv/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    emit('update:open', false)
    emit('success')
    alert(t('messages.importSuccess'))
  } catch (e) { 
    console.error(e)
    const errorMessage = e.response?.data?.detail || 
                        e.response?.data?.error || 
                        e.response?.data?.message ||
                        e.message || 
                        t('messages.uploadError')
    alert(`${t('messages.uploadError')}: ${errorMessage}`)
  } finally {
    isSubmitting.value = false
    // 重置文件輸入，允許重新選擇同一個文件
    if (event.target) {
      event.target.value = ''
    }
  }
}
</script>

<template>
  <Sheet :open="open" @update:open="emit('update:open', $event)">
    <SheetContent side="bottom">
      <SheetHeader>
        <SheetTitle>{{ t('dashboard.importCSV') }}</SheetTitle>
        <SheetDescription>
          {{ t('dashboard.importCSVDescription') }}
        </SheetDescription>
      </SheetHeader>
      <div class="py-4">
        <label class="cursor-pointer block">
          <Button variant="outline" as="span" :disabled="isSubmitting" class="w-full min-h-[44px] active:scale-95">
            <Upload class="h-4 w-4 mr-2" />
            {{ isSubmitting ? (t('common.uploading') || t('dashboard.importCSV')) : t('dashboard.importCSV') }}
          </Button>
          <input 
            type="file" 
            class="hidden" 
            @change="handleFileUpload" 
            accept=".csv"
            :disabled="isSubmitting"
          />
        </label>
      </div>
    </SheetContent>
  </Sheet>
</template>
