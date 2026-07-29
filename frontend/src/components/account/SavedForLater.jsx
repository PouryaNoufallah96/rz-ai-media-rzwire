import { useAccountStore } from '../../store/accountStore'
import { MEDIA_COLORS, PLAT_COLORS } from '../../store/mmStore'
import { PLAT_ICONS } from '../../utils/platformIcons'
import PreviewPanel from '../mm/PreviewPanel'

const SENTIMENT_COLORS = { Bullish: '#00d4a0', Bearish: '#ef4455', Neutral: '#a7abb2' }
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatSavedDate(iso) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} · ${hh}:${mm}`
}

export default function SavedForLater() {
  const { savedCards, activeSavedCard, setActiveSavedCard } = useAccountStore()

  if (!savedCards.length) {
    return <p className="acct-empty">Nothing saved yet — use "Save for Later" on a post to add it here.</p>
  }

  return (
    <div className="acct-saved-list">
      {savedCards.map(card => {
        const color = MEDIA_COLORS[card.brand] || '#a7abb2'
        const pc = PLAT_COLORS[card.platform] || '#a7abb2'
        const sentColor = SENTIMENT_COLORS[card.sentiment] || '#a7abb2'
        const isActive = activeSavedCard?.id === card.id

        return (
          <div key={card.id} className={`acct-saved-card${isActive ? ' active' : ''}`} onClick={() => setActiveSavedCard(card)}>
            <div className="acct-saved-header">
              <span className="acct-brand-tag" style={{ background: color + '20', color, border: `1px solid ${color}35` }}>{card.brand}</span>
              <span style={{ width: 20, height: 20, borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', background: pc + '1a', color: pc }}>{PLAT_ICONS[card.platform]}</span>
              <span className="sbadge sb-saved" style={{ marginLeft: 'auto' }}>Saved</span>
            </div>
            <div className="acct-saved-headline">{card.headline}</div>
            <div className="acct-saved-summary">{card.copy}</div>
            <div className="acct-saved-meta">
              <span className="sbadge" style={{ background: sentColor + '15', color: sentColor, border: `1px solid ${sentColor}35` }}>{card.sentiment}</span>
              <span className="sbadge sb-ready">Fit {card.suitability}/10</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function SavedCardDetail() {
  const { activeSavedCard, setActiveSavedCard } = useAccountStore()

  if (!activeSavedCard) {
    return <div className="acct-detail-empty">Select a saved card to preview</div>
  }

  const previewCard = {
    ...activeSavedCard,
    media: activeSavedCard.brand,
    srcColor: activeSavedCard.src_color,
    link: activeSavedCard.source_link,
    _modelDisplay: activeSavedCard._modelDisplay || activeSavedCard.model_display,
    _modelColor: activeSavedCard._modelColor || activeSavedCard.model_color,
    _modelKey: activeSavedCard._modelKey || 'gpt',
    timeAgo: `Saved ${formatSavedDate(activeSavedCard.created_at)}`,
  }

  const previewSessionKey = `${previewCard.id || ''}|${previewCard.platform || ''}|${previewCard.headline || ''}`
  return <PreviewPanel key={previewSessionKey} mode="saved" card={previewCard} onClose={() => setActiveSavedCard(null)} />
}
