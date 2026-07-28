import { create } from 'zustand'
import { API_BASE } from './mmStore'

export const useAccountStore = create((set, get) => ({
  summary: null,
  savedCards: [],
  activeSavedCard: null,
  loading: false,
  error: '',

  setActiveSavedCard: (card) => set({ activeSavedCard: card }),
  updateSavedCardLocal: (id, patch) => set(s => {
    const savedCards = s.savedCards.map(c => c.id === id ? { ...c, ...patch } : c)
    const activeSavedCard = s.activeSavedCard?.id === id ? { ...s.activeSavedCard, ...patch } : s.activeSavedCard
    return { savedCards, activeSavedCard }
  }),

  fetchSummary: async () => {
    set({ loading: true, error: '' })
    try {
      const res = await fetch(`${API_BASE}/api/account/summary`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Summary failed (${res.status})`)
      const data = await res.json()
      set({ summary: data, loading: false })
    } catch (e) {
      set({ error: e.message || 'Failed to load summary', loading: false })
    }
  },

  fetchSaved: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/account/saved`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Saved failed (${res.status})`)
      const data = await res.json()
      set({ savedCards: data.cards || [] })
    } catch (e) {
      set({ error: e.message || 'Failed to load saved cards' })
    }
  },

  discardSaved: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/account/saved/discard`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
      if (!res.ok) throw new Error(`Discard failed (${res.status})`)
      set({ savedCards: get().savedCards.filter(c => c.id !== id) })
      return true
    } catch (e) {
      set({ error: e.message || 'Failed to discard card' })
      return false
    }
  },

  updateSavedCard: async (id, patch) => {
    try {
      const res = await fetch(`${API_BASE}/api/account/saved/update`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, ...patch }),
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Update failed (${res.status})`) }
      const data = await res.json()
      const card = data.card || patch
      get().updateSavedCardLocal(id, card)
      return card
    } catch (e) {
      const msg = e.message || 'Failed to update saved card'
      set({ error: msg })
      throw new Error(msg)
    }
  },

  confirmScheduleSaved: async (id, scheduledDate, scheduledTime, copy, hashtags, overrides = {}) => {
    try {
      const res = await fetch(`${API_BASE}/api/account/saved/confirm-schedule`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, scheduledDate, scheduledTime, copy, hashtags, ...overrides }),
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Schedule failed (${res.status})`) }
      set({ savedCards: get().savedCards.filter(c => c.id !== id) })
      get().fetchSummary()
      return true
    } catch (e) {
      set({ error: e.message || 'Failed to schedule card' })
      return false
    }
  },

  scheduledPosts: [],

  fetchScheduled: async () => {
    try {
      const res = await fetch(`${API_BASE}/api/schedule/list`, { credentials: 'include' })
      if (!res.ok) throw new Error(`Scheduled failed (${res.status})`)
      const data = await res.json()
      set({ scheduledPosts: data.posts || [] })
    } catch (e) {
      set({ error: e.message || 'Failed to load scheduled posts' })
    }
  },

  cancelScheduled: async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/schedule/cancel`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Cancel failed (${res.status})`) }
      set({ scheduledPosts: get().scheduledPosts.filter(p => p.id !== id) })
      get().fetchSaved()
      get().fetchSummary()
      return true
    } catch (e) {
      set({ error: e.message || 'Failed to cancel scheduled post' })
      return false
    }
  },

  rescheduleScheduled: async (id, scheduledAtIso) => {
    try {
      const res = await fetch(`${API_BASE}/api/schedule/reschedule`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, scheduledAt: scheduledAtIso }),
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Reschedule failed (${res.status})`) }
      get().fetchScheduled()
      return true
    } catch (e) {
      set({ error: e.message || 'Failed to reschedule post' })
      return false
    }
  },
}))
