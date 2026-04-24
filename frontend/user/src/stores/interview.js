import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useInterviewStore = defineStore('interview', () => {
  const interviewStarted = ref(false)
  const conversationId = ref(null)
  const currentStage = ref('INTRO')
  const messages = ref([])
  const reportData = ref(null)
  const form = ref({
    resume_id: null,
    focus_areas: [],
  })

  function loadFromStorage() {
    try {
      const saved = sessionStorage.getItem('interview_state')
      if (saved) {
        const data = JSON.parse(saved)
        interviewStarted.value = data.interviewStarted || false
        conversationId.value = data.conversationId || null
        currentStage.value = data.currentStage || 'INTRO'
        messages.value = data.messages || []
        reportData.value = data.reportData || null
        form.value = data.form || { resume_id: null, focus_areas: [] }
      }
    } catch (e) {
      console.error('Failed to load interview state:', e)
    }
  }

  function saveToStorage() {
    try {
      sessionStorage.setItem('interview_state', JSON.stringify({
        interviewStarted: interviewStarted.value,
        conversationId: conversationId.value,
        currentStage: currentStage.value,
        messages: messages.value,
        reportData: reportData.value,
        form: form.value,
      }))
    } catch (e) {
      console.error('Failed to save interview state:', e)
    }
  }

  function startInterview(data) {
    interviewStarted.value = true
    conversationId.value = data.conversationId
    currentStage.value = data.stage
    messages.value = [{ role: 'assistant', content: data.message }]
    saveToStorage()
  }

  function addMessage(role, content) {
    messages.value.push({ role, content })
    saveToStorage()
  }

  function updateStage(stage) {
    currentStage.value = stage
    saveToStorage()
  }

  function setReportData(data) {
    reportData.value = data
    saveToStorage()
  }

  function reset() {
    interviewStarted.value = false
    conversationId.value = null
    currentStage.value = 'INTRO'
    messages.value = []
    reportData.value = null
    form.value = { resume_id: null, focus_areas: [] }
    sessionStorage.removeItem('interview_state')
  }

  loadFromStorage()

  return {
    interviewStarted,
    conversationId,
    currentStage,
    messages,
    reportData,
    form,
    startInterview,
    addMessage,
    updateStage,
    setReportData,
    reset,
    saveToStorage,
  }
})
