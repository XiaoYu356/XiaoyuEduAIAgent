import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useCodeStore = defineStore('code', () => {
  const code = ref('')
  const language = ref('python')
  const result = ref('')

  function loadFromStorage() {
    try {
      const saved = sessionStorage.getItem('code_state')
      if (saved) {
        const data = JSON.parse(saved)
        code.value = data.code || ''
        language.value = data.language || 'python'
        result.value = data.result || ''
      }
    } catch (e) {
      console.error('Failed to load code state:', e)
    }
  }

  function saveToStorage() {
    try {
      sessionStorage.setItem('code_state', JSON.stringify({
        code: code.value,
        language: language.value,
        result: result.value,
      }))
    } catch (e) {
      console.error('Failed to save code state:', e)
    }
  }

  function setCode(c) {
    code.value = c
    saveToStorage()
  }

  function setLanguage(lang) {
    language.value = lang
    saveToStorage()
  }

  function setResult(r) {
    result.value = r
    saveToStorage()
  }

  function reset() {
    code.value = ''
    language.value = 'python'
    result.value = ''
    sessionStorage.removeItem('code_state')
  }

  loadFromStorage()

  return {
    code,
    language,
    result,
    setCode,
    setLanguage,
    setResult,
    reset,
    saveToStorage,
  }
})
