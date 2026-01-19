import { ref, watch, onMounted } from 'vue'

export function useTheme() {
  // 從 localStorage 讀取主題，默認使用 light
  const getInitialTheme = () => {
    if (typeof window === 'undefined') return 'light'
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'dark' || savedTheme === 'light') {
      return savedTheme
    }
    // 默認使用 light 主題
    return 'light'
  }
  
  const theme = ref(getInitialTheme())
  
  const updateThemeClass = (themeValue) => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    // 強制移除和添加，確保生效
    root.classList.remove('dark', 'light')
    if (themeValue === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    // 調試用（可在開發時查看）
    console.log('Theme updated to:', themeValue, 'Has dark class:', root.classList.contains('dark'))
  }
  
  // 在組件掛載時應用主題
  onMounted(() => {
    updateThemeClass(theme.value)
  })
  
  // 如果已經在瀏覽器環境，立即應用
  if (typeof document !== 'undefined') {
    updateThemeClass(theme.value)
  }
  
  const setTheme = (newTheme) => {
    theme.value = newTheme
    if (typeof window !== 'undefined') {
      localStorage.setItem('theme', newTheme)
    }
    updateThemeClass(newTheme)
  }
  
  const toggleTheme = () => {
    const newTheme = theme.value === 'light' ? 'dark' : 'light'
    setTheme(newTheme)
  }
  
  // 監聽主題變化
  watch(theme, (newTheme) => {
    updateThemeClass(newTheme)
  }, { immediate: true })
  
  return {
    theme,
    setTheme,
    toggleTheme
  }
}
