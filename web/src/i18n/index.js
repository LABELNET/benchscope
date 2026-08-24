import { reactive } from 'vue'
import zh from './zh.js'
import en from './en.js'

const messages = { zh, en }

export const i18nState = reactive({
  locale: 'en',
})

export function t(key) {
  const dict = messages[i18nState.locale] || messages.zh
  return dict[key] || key
}

export function setLocale(locale) {
  if (messages[locale]) {
    i18nState.locale = locale
    document.documentElement.lang = locale === 'zh' ? 'zh-CN' : 'en'
  }
}

export function initI18n(savedLocale) {
  if (savedLocale && messages[savedLocale]) {
    setLocale(savedLocale)
  } else {
    // 默认英文，除非用户显式选择中文
    setLocale('en')
  }
}
