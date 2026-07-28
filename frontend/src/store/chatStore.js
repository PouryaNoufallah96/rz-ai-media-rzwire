import { create } from 'zustand'
import { API_BASE } from './mmStore'

const CHAT_TTL_MS = 60 * 60 * 1000
const CHAT_REQUEST_TIMEOUT_MS = 35 * 1000
let expiryTimer = null
let activeRequest = null

function cancelExpiryTimer() {
  if (expiryTimer) window.clearTimeout(expiryTimer)
  expiryTimer = null
}

function scheduleExpiry(expiresAt, get) {
  cancelExpiryTimer()
  if (!expiresAt) return
  const delay = Math.max(0, new Date(expiresAt).getTime() - Date.now())
  expiryTimer = window.setTimeout(() => get().expire(), delay)
}

function cancelActiveRequest() {
  if (activeRequest) activeRequest.abort()
  activeRequest = null
}

// Assistant messages may also include confidence, sources, and suggestions.
export const useChatStore = create((set, get) => ({
  messages: [],
  isOpen: false,
  loading: false,
  error: '',
  expiresAt: null,

  toggleOpen: () => set({ isOpen: !get().isOpen }),
  setOpen: (v) => set({ isOpen: v }),

  fetchHistory: async () => {
    const initialMessageCount = get().messages.length
    try {
      const res = await fetch(`${API_BASE}/api/chat/history`, { credentials: 'include' })
      if (!res.ok) throw new Error(`History failed (${res.status})`)
      const data = await res.json()
      // Do not let a late history response overwrite a message sent meanwhile.
      if (get().loading || get().messages.length !== initialMessageCount) return
      set({ messages: data.messages || [], expiresAt: data.expiresAt || null })
      scheduleExpiry(data.expiresAt, get)
    } catch {
      // silent — fresh chat on error
    }
  },

  send: async (text, context = null) => {
    const message = (text || '').trim()
    if (!message || get().loading) return
    const optimisticExpiry = new Date(Date.now() + CHAT_TTL_MS).toISOString()
    set({ loading: true, error: '', expiresAt: optimisticExpiry })
    scheduleExpiry(optimisticExpiry, get)
    // optimistic user turn
    set({ messages: [...get().messages, { role: 'user', content: message }] })
    const controller = new AbortController()
    activeRequest = controller
    const timeout = window.setTimeout(() => controller.abort(), CHAT_REQUEST_TIMEOUT_MS)
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, context }),
        signal: controller.signal,
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e?.error || `Chat failed (${res.status})`)
      }
      const data = await res.json()
      set({
        messages: [...get().messages, {
          role: 'assistant',
          content: data.reply,
          answerSource: data.answerSource,
          confidence: data.confidence,
          sources: data.sources || [],
          suggestions: data.suggestions || [],
          tokenUsed: false,
          knowledgeVersion: data.knowledgeVersion,
        }],
        loading: false,
        expiresAt: data.expiresAt || optimisticExpiry,
      })
      scheduleExpiry(data.expiresAt || optimisticExpiry, get)
    } catch (e) {
      // Clear/expiry intentionally aborts the request and owns the UI reset.
      if (e.name === 'AbortError' && activeRequest !== controller) return
      const messageText = e.name === 'AbortError'
        ? 'The assistant took too long to respond. Please try again.'
        : (e.message || 'Something went wrong.')
      set({
        error: messageText,
        loading: false,
        messages: [...get().messages, { role: 'assistant', content: `⚠️ ${messageText}` }],
      })
    } finally {
      window.clearTimeout(timeout)
      if (activeRequest === controller) activeRequest = null
    }
  },

  clear: async () => {
    cancelActiveRequest()
    cancelExpiryTimer()
    try {
      const res = await fetch(`${API_BASE}/api/chat/clear`, {
        method: 'POST', credentials: 'include',
      })
      if (!res.ok) throw new Error(`Clear failed (${res.status})`)
      set({ messages: [], error: '', expiresAt: null, loading: false })
    } catch (e) {
      set({ error: e.message || 'Failed to clear chat', loading: false })
    }
  },

  expire: () => {
    cancelActiveRequest()
    cancelExpiryTimer()
    set({ messages: [], error: '', expiresAt: null, loading: false })
    fetch(`${API_BASE}/api/chat/clear`, {
      method: 'POST', credentials: 'include',
    }).catch(() => {})
  },
}))
