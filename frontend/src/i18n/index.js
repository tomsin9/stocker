import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import zhHK from './locales/zh-HK.json'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || 'zh-HK',
  fallbackLocale: 'en',
  messages: {
    en,
    'zh-HK': zhHK
  }
})

export default i18n
