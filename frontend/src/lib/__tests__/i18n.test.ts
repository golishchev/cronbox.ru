import { describe, it, expect, vi, beforeEach } from 'vitest'
import i18n, { changeLanguage, getCurrentLanguage } from '../i18n'

describe('i18n module', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should export default i18n instance', () => {
    expect(i18n).toBeDefined()
    expect(i18n.t).toBeDefined()
  })

  it('should export changeLanguage function', () => {
    expect(changeLanguage).toBeDefined()
    expect(typeof changeLanguage).toBe('function')
  })

  it('should export getCurrentLanguage function', () => {
    expect(getCurrentLanguage).toBeDefined()
    expect(typeof getCurrentLanguage).toBe('function')
  })

  it('should return current language from getCurrentLanguage', () => {
    const lang = getCurrentLanguage()
    expect(['en', 'ru']).toContain(lang)
  })

  it('should have fallback language set to English', () => {
    expect(i18n.options.fallbackLng).toContain('en')
  })

  it('should change language when changeLanguage is called', async () => {
    const originalLang = getCurrentLanguage()
    const newLang = originalLang === 'en' ? 'ru' : 'en'

    await changeLanguage(newLang)

    expect(getCurrentLanguage()).toBe(newLang)

    // Restore original language
    await changeLanguage(originalLang)
  })
})
