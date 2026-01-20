import { ref, provide, inject } from 'vue'

const ADD_OPTIONS_KEY = Symbol('addOptions')

export function useAddOptions() {
  const showAddOptionsModal = ref(false)
  
  const openAddOptions = () => {
    showAddOptionsModal.value = true
  }
  
  const closeAddOptions = () => {
    showAddOptionsModal.value = false
  }
  
  return {
    showAddOptionsModal,
    openAddOptions,
    closeAddOptions
  }
}

export function provideAddOptions() {
  const addOptions = useAddOptions()
  provide(ADD_OPTIONS_KEY, addOptions)
  return addOptions
}

export function injectAddOptions() {
  const addOptions = inject(ADD_OPTIONS_KEY)
  if (!addOptions) {
    throw new Error('useAddOptions must be used within a component that provides addOptions')
  }
  return addOptions
}
