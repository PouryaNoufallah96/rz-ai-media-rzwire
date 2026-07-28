import { useEffect, useRef, useState } from 'react'
import { useChatStore } from '../../store/chatStore'
import { useMmStore } from '../../store/mmStore'
import './ChatWidget.css'

function formatMediaList(media) {
  if (media.length < 2) return media[0] || ''
  if (media.length === 2) return `${media[0]} or ${media[1]}`
  return `${media.slice(0, -1).join(', ')}, or ${media.at(-1)}`
}

function mediaSelectionPrompt(media) {
  if (media.length === 0) {
    return 'No media brand is selected. Choose a media brand and I will tailor my help to it.'
  }
  if (media.length === 1) {
    return `${media[0]} is selected. What would you like to know about ${media[0]}?`
  }
  return `You selected ${media.join(', ')}. Which media would you like to know about: ${formatMediaList(media)}?`
}

// Optional: pass `activeCard` from mmStore so the bot sees the open card.
// On the account page, leave `activeCard` null.
export default function ChatWidget({ activeCard = null }) {
  const { isOpen, toggleOpen, messages, loading, error, send, fetchHistory, clear } = useChatStore()
  const selectedMedia = useMmStore(state => state.selectedMedia)
  const [input, setInput] = useState('')
  const [dismissedSelectionKey, setDismissedSelectionKey] = useState('')
  const scrollRef = useRef(null)
  const mediaSelectionKey = selectedMedia.join('|')
  const selectionPrompt = messages.length === 0 || dismissedSelectionKey !== mediaSelectionKey
    ? mediaSelectionPrompt(selectedMedia)
    : ''

  useEffect(() => { fetchHistory() }, [fetchHistory])

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, isOpen, selectionPrompt])

  function currentContext() {
    return {
      selectedMedia,
      brand: activeCard?.media || activeCard?.brand || '',
      platform: activeCard?.platform || '',
      headline: activeCard?.headline || '',
      copy: activeCard?.copy || '',
    }
  }

  function submit() {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setDismissedSelectionKey(mediaSelectionKey)
    send(text, currentContext())
  }

  function askSuggestion(text) {
    if (!text || loading) return
    setDismissedSelectionKey(mediaSelectionKey)
    send(text, currentContext())
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <>
      {!isOpen && (
        <div className="chat-proactive-wrap">
          {selectionPrompt && (
            <button className="chat-selection-toast" onClick={toggleOpen}>
              {selectionPrompt}
            </button>
          )}
          <button className="chat-fab" onClick={toggleOpen} aria-label="Open chat assistant">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
            </svg>
          </button>
        </div>
      )}

      {isOpen && (
        <div className="chat-panel">
          <div className="chat-header">
            <div className="chat-title">
              <span className="chat-dot" />
              <span>
                RZWire Assistant
                <small>Local AI · no paid tokens</small>
              </span>
            </div>
            <div className="chat-header-actions">
              <button className="chat-icon-btn" onClick={clear} title="Clear chat">Clear</button>
              <button className="chat-icon-btn" onClick={toggleOpen} title="Close">✕</button>
            </div>
          </div>

          <div className="chat-messages" ref={scrollRef}>
            {messages.length === 0 && !loading && (
              <div className="chat-empty">
                Hi! Ask me about MGC Coin, Ranking Platform, Oasis Coin, Jewelry Coin,
                or how to use this workspace (analyze, copy, images, scheduling, posting).
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat-msg ${m.role}`}>
                <div className="chat-msg-bubble">
                  <div>{m.content}</div>
                  {m.role === 'assistant' && (m.confidence === 'medium' || m.confidence === 'low') && (
                    <span className={`chat-confidence ${m.confidence}`}>
                      {m.confidence === 'low' ? 'Low confidence' : 'Medium confidence'}
                    </span>
                  )}
                  {m.role === 'assistant' && m.sources?.length > 0 && (
                    <details className="chat-sources">
                      <summary>{m.sources.length === 1 ? 'Source' : 'Sources'}</summary>
                      <ul>
                        {m.sources.map((source) => (
                          <li key={source.id}>
                            <strong>{source.title}</strong>
                            {source.section && source.section !== source.title && (
                              <span> — {source.section}</span>
                            )}
                            {source.brand && <em>{source.brand}</em>}
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  {m.role === 'assistant' && m.suggestions?.length > 0 && (
                    <div className="chat-suggestions">
                      {m.suggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() => askSuggestion(suggestion)}
                          disabled={loading}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {selectionPrompt && (
              <div className="chat-msg assistant chat-selection-message">
                <div className="chat-msg-bubble">{selectionPrompt}</div>
              </div>
            )}
            {loading && (
              <div className="chat-msg assistant">
                <div className="chat-msg-bubble chat-typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
          </div>

          {error && <div className="chat-error">{error}</div>}

          <div className="chat-input-row">
            <textarea
              className="chat-input"
              rows={3}
              placeholder="Ask about a brand or the workspace…"
              maxLength={2000}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
            />
            <button className="chat-send" onClick={submit} disabled={loading || !input.trim()}>Send</button>
          </div>
        </div>
      )}
    </>
  )
}
