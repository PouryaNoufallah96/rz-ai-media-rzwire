import { useState } from 'react'
import { MEDIA_COLORS, PLAT_COLORS } from '../../store/mmStore'
import { PLAT_ICONS } from '../../utils/platformIcons'

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

function formatTimestamp(iso) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${MONTHS[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} · ${hh}:${mm}`
}

export default function ActivityHistory({ activity }) {
  const [expanded, setExpanded] = useState(null)
  const rows = activity || []

  if (!rows.length) {
    return <p className="acct-empty">No activity yet — approve or schedule a post to see it here.</p>
  }

  return (
    <div className="acct-activity-list">
      {rows.map((row, i) => {
        const isOpen = expanded === i
        const color = MEDIA_COLORS[row.brand] || '#a7abb2'
        return (
          <div key={i} className="acct-activity-row" onClick={() => setExpanded(isOpen ? null : i)}>
            <div className="acct-activity-main">
              <span className="acct-activity-time">{formatTimestamp(row.createdAt)}</span>
              <span className="acct-brand-tag" style={{ background: color + '20', color, border: `1px solid ${color}35` }}>{row.brand}</span>
              <span className="acct-activity-model">{row.modelDisplay}</span>
              <div className="acct-activity-platforms">
                {row.platforms.map(p => (
                  <span key={p} className="acct-activity-platform-icon" style={{ color: PLAT_COLORS[p] || '#a7abb2' }}>{PLAT_ICONS[p]}</span>
                ))}
              </div>
              <span className="acct-activity-count">{row.count} {row.count === 1 ? 'post' : 'posts'}</span>
              <svg className={`acct-chevron ${isOpen ? 'open' : ''}`} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            </div>
            {isOpen && (
              <div className="acct-activity-detail">
                <p>{row.headline}</p>
                <p style={{ marginTop: 6, color: '#a7abb2', fontSize: 11, textTransform: 'capitalize' }}>{row.actions.join(', ')}</p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
