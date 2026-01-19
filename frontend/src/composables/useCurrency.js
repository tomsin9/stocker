import { ref, provide, inject } from 'vue'

const CURRENCY_KEY = Symbol('currency')

export function useCurrency() {
  const currentCurrency = ref(localStorage.getItem('currency') || 'USD')
  
  const switchCurrency = () => {
    currentCurrency.value = currentCurrency.value === 'USD' ? 'HKD' : 'USD'
    localStorage.setItem('currency', currentCurrency.value)
  }
  
  return {
    currentCurrency,
    switchCurrency
  }
}

export function provideCurrency() {
  const currency = useCurrency()
  provide(CURRENCY_KEY, currency)
  return currency
}

export function injectCurrency() {
  const currency = inject(CURRENCY_KEY)
  if (!currency) {
    throw new Error('useCurrency must be used within a component that provides currency')
  }
  return currency
}
