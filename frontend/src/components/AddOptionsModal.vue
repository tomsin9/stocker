<script setup>
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Plus, ArrowDownCircle, ArrowUpCircle, Upload } from 'lucide-vue-next'
import { injectAddOptions } from '@/composables/useAddOptions'

const { t } = useI18n()
const router = useRouter()
const { showAddOptionsModal, closeAddOptions } = injectAddOptions()

const handleAddTransaction = () => {
  closeAddOptions()
  router.push('/')
  // 等待路由切換後再打開 modal，使用 setTimeout 確保路由已切換
  setTimeout(() => {
    // 觸發自定義事件，讓 HomeView 知道要打開 add modal
    window.dispatchEvent(new CustomEvent('openAddTransaction'))
  }, 100)
}

const handleDeposit = () => {
  closeAddOptions()
  router.push('/')
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('openDeposit'))
  }, 100)
}

const handleWithdraw = () => {
  closeAddOptions()
  router.push('/')
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent('openWithdraw'))
  }, 100)
}

const handleImportFile = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  closeAddOptions()
  
  // 如果不在首頁，先導航到首頁
  if (router.currentRoute.value.path !== '/') {
    await router.push('/')
    // 等待路由切換後再觸發事件
    await new Promise(resolve => setTimeout(resolve, 200))
  }
  
  // 觸發事件，讓 HomeView 處理文件上傳
  window.dispatchEvent(new CustomEvent('importCSV', { detail: { file } }))
  
  // 重置 input
  event.target.value = ''
}
</script>

<template>
  <Sheet v-model:open="showAddOptionsModal">
    <SheetContent side="bottom" class="max-h-[90vh] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>{{ t('navigation.add') }}</SheetTitle>
        <SheetDescription>
          {{ t('dashboard.selectAction') }}
        </SheetDescription>
      </SheetHeader>
      <div class="grid gap-3 py-4">
        <Button 
          @click="handleAddTransaction"
          variant="default"
          size="lg"
          class="w-full min-h-[56px] justify-start active:scale-95"
        >
          <Plus class="h-5 w-5 mr-3" />
          <div class="flex flex-col items-start">
            <span class="font-semibold">{{ t('dashboard.addTransaction') }}</span>
            <span class="text-xs text-muted-foreground">{{ t('transaction.description') }}</span>
          </div>
        </Button>
        
        <Button 
          @click="handleDeposit"
          variant="outline"
          size="lg"
          class="w-full min-h-[56px] justify-start active:scale-95"
        >
          <ArrowDownCircle class="h-5 w-5 mr-3" />
          <div class="flex flex-col items-start">
            <span class="font-semibold">{{ t('dashboard.depositFunds') }}</span>
            <span class="text-xs text-muted-foreground">{{ t('cashflow.depositDescription') }}</span>
          </div>
        </Button>
        
        <Button 
          @click="handleWithdraw"
          variant="outline"
          size="lg"
          class="w-full min-h-[56px] justify-start active:scale-95"
        >
          <ArrowUpCircle class="h-5 w-5 mr-3" />
          <div class="flex flex-col items-start">
            <span class="font-semibold">{{ t('dashboard.withdrawFunds') }}</span>
            <span class="text-xs text-muted-foreground">{{ t('cashflow.withdrawDescription') }}</span>
          </div>
        </Button>
        
        <label class="cursor-pointer">
          <Button 
            variant="outline"
            size="lg"
            as="span"
            class="w-full min-h-[56px] justify-start active:scale-95"
            @click="closeAddOptions"
          >
            <Upload class="h-5 w-5 mr-3" />
            <div class="flex flex-col items-start">
              <span class="font-semibold">{{ t('dashboard.importCSV') }}</span>
              <span class="text-xs text-muted-foreground">{{ t('dashboard.importCSVDescription') }}</span>
            </div>
          </Button>
          <input 
            type="file" 
            class="hidden" 
            @change="handleImportFile"
            accept=".csv"
          />
        </label>
      </div>
      <SheetFooter>
        <!-- <Button variant="outline" @click="closeAddOptions" class="w-full min-h-[44px] active:scale-95">{{ t('common.cancel') }}</Button> -->
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>
