import { MEDIA_LIST, MEDIA_COLORS } from '../../store/mmStore'

export default function PostsByBrand({ postsByBrand }) {
  const data = postsByBrand || {}
  const max = Math.max(1, ...MEDIA_LIST.map(b => data[b]?.generated || 0))

  return (
    <div className="acct-brand-list">
      {MEDIA_LIST.map(brand => {
        const stats = data[brand] || { generated: 0, scheduled: 0 }
        const color = MEDIA_COLORS[brand] || '#a7abb2'
        const pct = Math.round((stats.generated / max) * 100)
        return (
          <div key={brand} className="acct-brand-row">
            <span className="acct-brand-name" style={{ color }}>{brand}</span>
            <div className="acct-brand-bar-track">
              <div className="acct-brand-bar-fill" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="acct-brand-counts">{stats.generated} / {stats.scheduled}</span>
          </div>
        )
      })}
    </div>
  )
}
