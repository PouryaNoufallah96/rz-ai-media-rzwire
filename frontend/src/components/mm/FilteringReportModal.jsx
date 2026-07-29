import { useState } from 'react'
import { useMmStore } from '../../store/mmStore'

const STATUS_LABELS = {
  selected:             'Selected',
  floor_rescued:        'Rescued',
  backfilled_secondary: 'Backfilled',
  too_old:              'Too Old',
  duplicate:            'Duplicate',
  clustered_out:        'Clustered',
  no_media_fit:         'No Fit',
  low_score:            'Low Score',
  cap_exceeded:         'Cap',
}

function StatusBadge({ status }) {
  const cls = `rpt-status rpt-s-${status}`
  return <span className={cls}>{STATUS_LABELS[status] || status}</span>
}

function ScoreBar({ value, color = '#9b72f5' }) {
  const pct = Math.max(0, Math.min(100, (value || 0) * 100))
  return (
    <span className="score-bar-wrap">
      <span className="score-bar" style={{ width: `${pct}%`, background: color }} />
    </span>
  )
}

function FunnelStat({ label, value, color }) {
  return (
    <div style={{ textAlign: 'center', minWidth: 70 }}>
      <div style={{ fontSize: 20, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 9, color: '#a7abb2', fontWeight: 600, letterSpacing: '.04em', textTransform: 'uppercase', marginTop: 2 }}>{label}</div>
    </div>
  )
}

function FunnelArrow() {
  return <span style={{ color: '#3a3f4e', fontSize: 16 }}>→</span>
}

function ScoreDrawer({ article, onClose }) {
  if (!article) return null
  const scores = article._scores || {}
  const keywords = article._keywords || []

  const subScores = [
    { label: 'User Topic',  val: scores.userTopic },
    { label: 'Virality',    val: scores.virality },
    { label: 'Freshness',   val: scores.freshness },
    { label: 'Authority',   val: scores.authority },
    { label: 'Diversity',   val: scores.diversity },
  ]

  const mediaFit = scores.mediaFit || scores.kwScores || {}

  return (
    <div id="score-drawer" className="open">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#eeeae2' }}>Score Detail</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#a7abb2', cursor: 'pointer', fontSize: 16, padding: 4 }}>✕</button>
      </div>

      <div style={{ fontSize: 12, fontWeight: 600, color: '#c8cdd8', lineHeight: 1.4 }}>{article.title}</div>
      <div style={{ fontSize: 10, color: '#a7abb2' }}>{article.source} · {article._pipelineStatus}</div>

      {scores.final != null && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
          <span style={{ fontSize: 10, color: '#a7abb2', fontWeight: 600, width: 70 }}>FINAL</span>
          <ScoreBar value={scores.final} color="#00d4a0" />
          <span style={{ fontSize: 10, color: '#c8cdd8' }}>{(scores.final * 100).toFixed(0)}</span>
        </div>
      )}

      {subScores.filter(s => s.val != null).map(s => (
        <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 10, color: '#a7abb2', fontWeight: 600, width: 70 }}>{s.label}</span>
          <ScoreBar value={s.val} />
          <span style={{ fontSize: 10, color: '#c8cdd8' }}>{(s.val * 100).toFixed(0)}</span>
        </div>
      ))}

      {Object.keys(mediaFit).length > 0 && (
        <>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a7abb2', letterSpacing: '.06em', textTransform: 'uppercase', marginTop: 6 }}>Brand Fit</div>
          {Object.entries(mediaFit).map(([brand, val]) => (
            <div key={brand} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 10, color: '#a7abb2', fontWeight: 600, width: 70, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{brand}</span>
              <ScoreBar value={val / 100} color="#3d8ef0" />
              <span style={{ fontSize: 10, color: '#c8cdd8' }}>{typeof val === 'number' ? val.toFixed(0) : val}</span>
            </div>
          ))}
        </>
      )}

      {keywords.length > 0 && (
        <>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a7abb2', letterSpacing: '.06em', textTransform: 'uppercase', marginTop: 6 }}>Keywords</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {keywords.map((kw, i) => {
              const kwStr = typeof kw === 'string' ? kw : kw.word || kw.keyword || ''
              const strength = typeof kw === 'object' ? kw.strength : null
              const cls = strength === 'strong' ? 'kw-pill kw-strong' : strength === 'weak' ? 'kw-pill kw-weak' : strength === 'bias' ? 'kw-pill kw-bias' : 'kw-pill'
              return <span key={i} className={cls}>{kwStr}</span>
            })}
          </div>
        </>
      )}

      {article._dupOf && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a7abb2', letterSpacing: '.06em', textTransform: 'uppercase' }}>Duplicate Of</div>
          <div style={{ fontSize: 10, color: '#c8cdd8', marginTop: 2 }}>{article._dupOf}</div>
          {article._dupReason && <div style={{ fontSize: 10, color: '#a7abb2', marginTop: 1 }}>{article._dupReason}</div>}
        </div>
      )}

      {article._routing && (
        <div style={{ marginTop: 6 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#a7abb2', letterSpacing: '.06em', textTransform: 'uppercase' }}>Routing</div>
          <div style={{ fontSize: 10, color: '#c8cdd8', marginTop: 2 }}>
            {Object.entries(article._routing).map(([brand, conf]) => (
              <div key={brand}>{brand}: {typeof conf === 'number' ? conf.toFixed(0) : JSON.stringify(conf)}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function FilteringReportModal() {
  const { reportOpen, setReportOpen, mmReport } = useMmStore()
  const [tab, setTab] = useState('all')
  const [drawerArticle, setDrawerArticle] = useState(null)

  if (!reportOpen || !mmReport) return null

  const articles = mmReport.allArticles || []
  const rejected = mmReport.rejected || {}
  const perMedia = mmReport.perMedia || {}
  const afterQuality = mmReport.afterRecency - (rejected.duplicate || 0)
  const ts = mmReport.runAt ? new Date(mmReport.runAt).toLocaleTimeString() : ''

  const rejectionGroups = {}
  articles.filter(a => !['selected', 'floor_rescued', 'backfilled_secondary'].includes(a._pipelineStatus)).forEach(a => {
    const key = a._pipelineStatus || 'unknown'
    if (!rejectionGroups[key]) rejectionGroups[key] = []
    rejectionGroups[key].push(a)
  })

  const bestBrand = (art) => {
    const fit = art._scores?.mediaFit || art._scores?.kwScores || {}
    let best = '', bestVal = -1
    Object.entries(fit).forEach(([b, v]) => { if (v > bestVal) { bestVal = v; best = b } })
    return best
  }

  return (
    <div id="report-modal-overlay" className="open" onClick={() => { setReportOpen(false); setDrawerArticle(null) }}>
      <div id="report-modal" onClick={e => e.stopPropagation()} style={{ position: 'relative' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 18px 10px', borderBottom: '1px solid rgba(255,255,255,.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: '#eeeae2' }}>Filtering Report</span>
            {mmReport.filterMode && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4, background: 'rgba(155,114,245,.12)', color: '#9b72f5', border: '1px solid rgba(155,114,245,.25)', letterSpacing: '.04em' }}>
                {mmReport.filterMode.toUpperCase().replace(/_/g, ' ')}
              </span>
            )}
            {ts && <span style={{ fontSize: 10, color: '#a7abb2' }}>{ts}</span>}
          </div>
          <button onClick={() => { setReportOpen(false); setDrawerArticle(null) }} style={{ background: 'none', border: 'none', color: '#a7abb2', cursor: 'pointer', fontSize: 18, padding: 4 }}>✕</button>
        </div>

        {/* Funnel summary */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, padding: '14px 18px', borderBottom: '1px solid rgba(255,255,255,.06)' }}>
          <FunnelStat label="Fetched" value={mmReport.fetchedTotal} color="#eeeae2" />
          <FunnelArrow />
          <FunnelStat label="Recent" value={mmReport.afterRecency} color="#f0a040" />
          <FunnelArrow />
          <FunnelStat label="Quality" value={afterQuality} color="#3d8ef0" />
          <FunnelArrow />
          <FunnelStat label="Shortlisted" value={mmReport.shortlistedCount} color="#00d4a0" />

          <div style={{ width: 1, height: 32, background: 'rgba(255,255,255,.08)', margin: '0 6px' }} />

          {Object.entries(perMedia).map(([brand, count]) => (
            <div key={brand} style={{ textAlign: 'center', minWidth: 50 }}>
              <div style={{ fontSize: 16, fontWeight: 800, color: '#9b72f5' }}>{count}</div>
              <div style={{ fontSize: 8, color: '#a7abb2', fontWeight: 600, maxWidth: 70, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{brand}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ padding: '8px 12px 0', borderBottom: '1px solid rgba(255,255,255,.06)' }}>
          <div className="rpt-tabs">
            <button className={`rpt-tab ${tab === 'all' ? 'active' : ''}`} onClick={() => setTab('all')}>All Articles ({articles.length})</button>
            <button className={`rpt-tab ${tab === 'rejected' ? 'active' : ''}`} onClick={() => setTab('rejected')}>Rejection Breakdown</button>
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
          {tab === 'all' && (
            <table className="rpt-table">
              <thead>
                <tr>
                  <th style={{ width: '40%' }}>Title</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Best Brand</th>
                </tr>
              </thead>
              <tbody>
                {articles.map((art, i) => (
                  <tr key={i} onClick={() => setDrawerArticle(drawerArticle === art ? null : art)} style={{ cursor: 'pointer', background: drawerArticle === art ? 'rgba(155,114,245,.06)' : undefined }}>
                    <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{art.title}</td>
                    <td>{art.source || ''}</td>
                    <td><StatusBadge status={art._pipelineStatus} /></td>
                    <td>
                      {art._scores?.final != null ? (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <ScoreBar value={art._scores.final} color="#00d4a0" />
                          <span style={{ fontSize: 10, color: '#a7abb2' }}>{(art._scores.final * 100).toFixed(0)}</span>
                        </span>
                      ) : (
                        <span style={{ fontSize: 10, color: '#3a3f4e' }}>—</span>
                      )}
                    </td>
                    <td style={{ fontSize: 10 }}>{bestBrand(art)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {tab === 'rejected' && (
            <div style={{ padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {Object.entries(rejectionGroups).map(([status, arts]) => (
                <div key={status}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                    <StatusBadge status={status} />
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#c8cdd8' }}>{arts.length} articles</span>
                  </div>
                  <table className="rpt-table">
                    <thead>
                      <tr>
                        <th style={{ width: '50%' }}>Title</th>
                        <th>Source</th>
                        <th>Detail</th>
                      </tr>
                    </thead>
                    <tbody>
                      {arts.map((art, i) => (
                        <tr key={i} onClick={() => setDrawerArticle(drawerArticle === art ? null : art)} style={{ cursor: 'pointer', background: drawerArticle === art ? 'rgba(155,114,245,.06)' : undefined }}>
                          <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{art.title}</td>
                          <td>{art.source || ''}</td>
                          <td style={{ fontSize: 10, color: '#a7abb2' }}>
                            {status === 'duplicate' && art._dupOf ? `dup of: ${art._dupOf.slice(0, 40)}…` : ''}
                            {status === 'low_score' && art._scores?.final != null ? `score: ${(art._scores.final * 100).toFixed(0)}` : ''}
                            {status === 'no_media_fit' ? 'no brand match' : ''}
                            {status === 'too_old' ? 'outside recency window' : ''}
                            {status === 'clustered_out' && art._clusteredWith ? `clustered with: ${art._clusteredWith.slice(0, 40)}…` : ''}
                            {status === 'cap_exceeded' ? 'brand cap reached' : ''}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
              {Object.keys(rejectionGroups).length === 0 && (
                <div style={{ textAlign: 'center', color: '#a7abb2', fontSize: 12, padding: 20 }}>No rejected articles</div>
              )}
            </div>
          )}

          <ScoreDrawer article={drawerArticle} onClose={() => setDrawerArticle(null)} />
        </div>
      </div>
    </div>
  )
}
