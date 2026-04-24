import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const conversationId = ref(null)
  const messages = ref([])
  const selectedKbIds = ref([])

  function loadFromStorage() {
    try {
      const saved = sessionStorage.getItem('chat_state')
      if (saved) {
        const data = JSON.parse(saved)
        conversationId.value = data.conversationId || null
        messages.value = data.messages || []
        selectedKbIds.value = data.selectedKbIds || []
      }
    } catch (e) {
      console.error('Failed to load chat state:', e)
    }
  }

  function saveToStorage() {
    try {
      sessionStorage.setItem('chat_state', JSON.stringify({
        conversationId: conversationId.value,
        messages: messages.value,
        selectedKbIds: selectedKbIds.value,
      }))
    } catch (e) {
      console.error('Failed to save chat state:', e)
    }
  }

  function setConversation(id) {
    conversationId.value = id
    messages.value = []
    saveToStorage()
  }

  function addMessage(role, content) {
    messages.value.push({ role, content })
    saveToStorage()
  }

  function setMessages(msgs) {
    messages.value = msgs
    saveToStorage()
  }

  function setSelectedKbIds(ids) {
    selectedKbIds.value = ids
    saveToStorage()
  }

  function reset() {
    conversationId.value = null
    messages.value = []
    selectedKbIds.value = []
    sessionStorage.removeItem('chat_state')
  }

  loadFromStorage()

  return {
    conversationId,
    messages,
    selectedKbIds,
    setConversation,
    addMessage,
    setMessages,
    setSelectedKbIds,
    reset,
    saveToStorage,
  }
})
