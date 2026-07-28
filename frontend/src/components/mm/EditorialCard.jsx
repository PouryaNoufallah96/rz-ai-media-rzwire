import { useEffect, useRef, useState } from 'react'
import { useMmStore, API_BASE, MEDIA_COLORS, PLAT_COLORS, PLAT_LIST } from '../../store/mmStore'
import { useLanguageStore } from '../../store/languageStore'
import { routeCardToPlatform } from '../../utils/routeCardToPlatform'

const STATUS_BADGE = {
  ready:     <span className="sbadge sb-ready"     style={{fontSize:8.5}}>● Ready</span>,
  image:     <span className="sbadge sb-image"     style={{fontSize:8.5}}>● Needs Image</span>,
  approved:  <span className="sbadge sb-approved"  style={{fontSize:8.5}}>● Approved</span>,
  scheduled: <span className="sbadge sb-scheduled" style={{fontSize:8.5}}>● Scheduled</span>,
  published: <span className="sbadge sb-published" style={{fontSize:8.5}}>● Published</span>,
}
const MK_LABEL = {'MGC Coin':'MGC','Ranking Platform':'RK','Oasis Coin':'OAS','Jewelry Coin':'JWL'}

export default function EditorialCard({ card, onDragStart }) {
  const setActiveCard = useMmStore(s => s.setActiveCard)
  const selectedPlatforms = useMmStore(s => s.selectedPlatforms)
  const platformLanes = useMmStore(s => s.platformLanes)
  const modelLanes = useMmStore(s => s.modelLanes)
  const telegramLanes = useMmStore(s => s.telegramLanes)
  const setPlatformLanes = useMmStore(s => s.setPlatformLanes)
  const updatePlatformCard = useMmStore(s => s.updatePlatformCard)
  const getCachedCopy = useMmStore(s => s.getCachedCopy)
  const setCachedCopy = useMmStore(s => s.setCachedCopy)
  const promoMode = useMmStore(s => s.promoMode)
  const updateSourceCard = useMmStore(s => s.updateSourceCard)
  const language = useLanguageStore(s => s.language)

  const [popoverOpen, setPopoverOpen] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [translationError, setTranslationError] = useState('')
  const popoverRef = useRef(null)

  const isSuggested = !card.platform || card.platform === 'suggested'
  const mc = MEDIA_COLORS[card.media] || '#7a8499'
  const pc = isSuggested ? null : (PLAT_COLORS[card.platform] || '#7a8499')
  const sentColor = card.sentiment === 'Bullish' ? '#00d4a0' : card.sentiment === 'Bearish' ? '#ef4455' : '#7a8499'
  const mkLabel = MK_LABEL[card.media] || (card.media||'').slice(0,2)
  const isPersian = language === 'fa'
  const isTranslated = !!card._sourceTranslated

  const routedPlatforms = PLAT_LIST.filter(p => (platformLanes[card.media]?.[p] || []).some(c => c.id === card.id))

  useEffect(() => {
    if (!popoverOpen) return
    function onDown(e) { if (popoverRef.current && !popoverRef.current.contains(e.target)) setPopoverOpen(false) }
    function onKey(e) { if (e.key === 'Escape') setPopoverOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [popoverOpen])

  function sendTo(plat) {
    if (routedPlatforms.includes(plat)) return
    routeCardToPlatform(card.id, plat, card.media, { modelLanes, telegramLanes, platformLanes, setPlatformLanes, updatePlatformCard, getCachedCopy, setCachedCopy, setActiveCard, promoMode })
  }

  async function translateCard(event) {
    event.stopPropagation()
    if (translating || isTranslated) return
    setTranslating(true)
    setTranslationError('')
    try {
      const reason = card.mediaReason || card.selectionReason || ''
      const response = await fetch(`${API_BASE}/api/translate/cards`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          language:'fa',
          articles:[
            { title:card.headline || '', desc:card.copy || '' },
            { title:'', desc:reason },
          ],
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !Array.isArray(data.articles) || !data.articles[0]) {
        throw new Error(data.error || 'ترجمه از سرور دریافت نشد')
      }
      const article = data.articles[0]
      const translatedReason = data.articles[1]?.desc || reason
      updateSourceCard(card.id, {
        _sourceTranslated:true,
        _originalHeadline:card._originalHeadline || card.headline,
        _originalCopy:card._originalCopy || card.copy,
        headline:article.title || card.headline,
        copy:article.desc || card.copy,
        selectionReason:translatedReason,
        mediaReason:translatedReason,
        language:'fa',
      })
    } catch (error) {
      setTranslationError(error.message || 'ترجمه انجام نشد')
    } finally {
      setTranslating(false)
    }
  }

  return (
    <div
      ref={popoverRef}
      className={`mm-card fade-up${card === useMmStore.getState().activeCard ? ' active' : ''}${isTranslated ? ' source-translated' : ''}`}
      id={`card-${card.id}`}
      draggable
      onDragStart={e => { e.dataTransfer.setData('text/plain', card.id); if (onDragStart) onDragStart(card.id); e.currentTarget.classList.add('dragging') }}
      onDragEnd={e => e.currentTarget.classList.remove('dragging')}
      onClick={() => setActiveCard(card)}
    >
      <button className="qs-btn" title="Quick send to platform"
        onClick={e => { e.stopPropagation(); setPopoverOpen(o => !o) }}>⋯</button>
      {popoverOpen && (
        <div className="qs-popover" onClick={e => e.stopPropagation()}>
          <span className="qs-label">Send to</span>
          {selectedPlatforms.map(p => {
            const routed = routedPlatforms.includes(p)
            return (
              <button key={p} className={`qs-plat-btn${routed ? ' routed' : ''}`}
                onClick={() => { sendTo(p); setPopoverOpen(false) }}>
                <span>{p}</span>
                {routed && <span>✓</span>}
              </button>
            )
          })}
        </div>
      )}

      {/* Row 1: media badge + platform + time */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:7,gap:4}}>
        <div style={{display:'flex',alignItems:'center',gap:4}}>
          <span style={{fontSize:8,fontWeight:700,padding:'1.5px 5px',borderRadius:3,background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{mkLabel}</span>
          {isSuggested
            ? <span style={{fontSize:8,fontWeight:600,padding:'1.5px 5px',borderRadius:3,background:'rgba(255,255,255,.04)',color:'#4a5568',border:'1px solid rgba(255,255,255,.08)'}}>drag to platform →</span>
            : <span style={{fontSize:8,fontWeight:700,padding:'1.5px 5px',borderRadius:3,background:pc+'20',color:pc,border:`1px solid ${pc}35`}}>{card.platform}</span>
          }
          {isSuggested && routedPlatforms.length > 0 && <span className="routed-badge">→ {routedPlatforms.join(', ')}</span>}
        </div>
        <span style={{fontSize:9,color:'#4a5568'}}>{card.timeAgo}</span>
      </div>

      {/* Row 2: source */}
      <div style={{display:'flex',alignItems:'center',gap:5,marginBottom:6}}>
        <div style={{width:16,height:16,borderRadius:4,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:6,fontWeight:700,background:card.srcColor+'1a',color:card.srcColor,border:`1px solid ${card.srcColor}30`}}>{card.initials}</div>
        <span style={{fontSize:10,color:'#7a8499'}}>{card.source}</span>
        {card._isTelegramSource && card.viewsLabel && (
          <span style={{fontSize:9,color:'#24a1de',fontWeight:700,marginLeft:'auto'}}>{card.viewsLabel} views</span>
        )}
      </div>

      {/* Headline */}
      <h4 data-no-localize="true" className={isTranslated ? 'article-copy-rtl' : 'article-copy-ltr'} dir={isTranslated ? 'rtl' : 'ltr'} style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:11,color:'#f0f2f8',lineHeight:1.35,letterSpacing:'-.01em',marginBottom:6,display:isTranslated?'block':'-webkit-box',WebkitLineClamp:isTranslated?'unset':2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>{card.headline}</h4>

      {/* Copy preview */}
      <p data-no-localize="true" className={isTranslated ? 'article-copy-rtl' : 'article-copy-ltr'} dir={isTranslated ? 'rtl' : 'ltr'} style={{fontSize:10,color:'#7a8499',lineHeight:1.65,marginBottom:8,display:isTranslated?'block':'-webkit-box',WebkitLineClamp:isTranslated?'unset':2,WebkitBoxOrient:'vertical',overflow:'hidden',opacity:card.isGenerating?0.45:1,transition:'opacity .2s'}}>{card.copy}</p>

      {isPersian && isSuggested && (
        <div className="translate-card-row" onClick={event => event.stopPropagation()}>
          <button type="button" className="translate-card-btn" onClick={translateCard} disabled={translating || isTranslated}>
            {translating ? 'در حال ترجمه…' : isTranslated ? 'ترجمه شد' : 'ترجمه'}
          </button>
          {translationError && <span className="translate-card-error">{translationError}</span>}
        </div>
      )}

      {/* Status + scores */}
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
        {card.isGenerating
          ? <span className="sbadge" style={{fontSize:8.5,color:'#9b72f5',background:'rgba(155,114,245,.12)',border:'1px solid rgba(155,114,245,.3)'}}>✨ Generating…</span>
          : (STATUS_BADGE[card.status] || STATUS_BADGE.ready)}
        <div style={{display:'flex',alignItems:'center',gap:5,flexWrap:'wrap'}}>
          <span style={{fontSize:9,color:sentColor,fontWeight:600}}>{card.sentiment}</span>
          <span style={{fontSize:9,color:'#f0a040',fontWeight:700}}>⚡{card.suitability}/10</span>
          {card.lowConfidence && <span style={{fontSize:7.5,padding:'1px 4px',borderRadius:3,background:'rgba(240,160,64,.12)',color:'#f0a040',border:'1px solid rgba(240,160,64,.3)'}}>⚠ Low Conf</span>}
        </div>
      </div>
    </div>
  )
}
