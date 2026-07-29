import { useRef, useEffect } from 'react'
import { useMmStore, MEDIA_COLORS, PLAT_COLORS, EDITORIAL_MODEL_META, mkey } from '../../store/mmStore'
import { routeCardToPlatform } from '../../utils/routeCardToPlatform'
import EditorialCard from './EditorialCard'

// Drag state
let _dragCardId = null

function ModelLane({ modelKey, brand }) {
  const { modelLanes, editorial } = useMmStore()
  const meta  = EDITORIAL_MODEL_META[modelKey]
  const color = meta?.color || '#a7abb2'
  const cards = modelLanes[modelKey]?.[brand] || []
  const errMsg = editorial?.[modelKey]?.error || null

  return (
    <div className="lane" style={{borderRight:`1px solid ${color}22`}} data-lane-type="model" data-model-key={modelKey} data-brand={brand}>
      <div className="lane-header" style={{background:color+'0e',borderBottom:`1px solid ${color}22`}}>
        <div style={{width:20,height:20,borderRadius:5,background:color+'20',color,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,fontSize:7,fontWeight:800}}>{meta?.badge?.slice(0,2).toUpperCase()}</div>
        <span style={{fontSize:10.5,fontWeight:700,color:'#eeeae2',flex:1}}>{meta?.display}</span>
        <span style={{fontSize:9.5,fontWeight:700,padding:'1px 6px',borderRadius:4,background:color+'15',color}}>{cards.length}</span>
      </div>
      <div className="lane-cards">
        {errMsg && <div style={{padding:14,textAlign:'center',color:'#ef4455',fontSize:10,lineHeight:1.5}}>Error: {errMsg}</div>}
        {!cards.length && !errMsg && <div className="empty-lane"><p style={{fontSize:10,color:'#3a4258',textAlign:'center'}}>No articles</p></div>}
        {cards.map(c => <EditorialCard key={c.id} card={c} onDragStart={id => { _dragCardId = id }} />)}
      </div>
    </div>
  )
}

function PlatformLane({ brand, plat }) {
  const { platformLanes, modelLanes, telegramLanes, setPlatformLanes, updatePlatformCard, getCachedCopy, setCachedCopy, setActiveCard, promoMode } = useMmStore()
  const col = PLAT_COLORS[plat] || '#a7abb2'
  const cards = platformLanes[brand]?.[plat] || []

  function handleDrop(e) {
    e.preventDefault()
    const cardId = e.dataTransfer.getData('text/plain') || _dragCardId
    if (!cardId) return
    e.currentTarget.classList.remove('drag-over')
    _dragCardId = null
    routeCardToPlatform(cardId, plat, brand, { modelLanes, telegramLanes, platformLanes, setPlatformLanes, updatePlatformCard, getCachedCopy, setCachedCopy, setActiveCard, promoMode })
  }

  const PlatIcons = {
    X: <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.81l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>,
    Telegram: <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8l-1.7 8c-.12.56-.45.7-.9.44l-2.5-1.84-1.2 1.16c-.13.13-.24.24-.5.24l.18-2.52 4.56-4.12c.2-.18-.04-.27-.3-.1L7.56 15.4l-2.46-.77c-.53-.17-.54-.53.12-.78l9.62-3.72c.44-.16.83.1.8.67z"/></svg>,
    Instagram: <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><rect x="2" y="2" width="20" height="20" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".7" fill="currentColor" stroke="none"/></svg>,
  }

  return (
    <div className="lane"
      onDragOver={e => { e.preventDefault(); e.currentTarget.classList.add('drag-over') }}
      onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget)) e.currentTarget.classList.remove('drag-over') }}
      onDrop={handleDrop}
    >
      <div className="lane-header" style={{background:col+'0e',borderBottom:`1px solid ${col}22`}}>
        <span style={{color:col,display:'flex',alignItems:'center'}}>{PlatIcons[plat]}</span>
        <span style={{fontSize:10.5,fontWeight:700,color:'#eeeae2',flex:1}}>{plat}</span>
        <span style={{fontSize:9.5,fontWeight:700,padding:'1px 6px',borderRadius:4,background:col+'15',color:col}}>{cards.length}</span>
      </div>
      <div className="lane-cards">
        {!cards.length && (
          <div className="empty-lane">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#3a4258" strokeWidth="1.4" strokeLinecap="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <p style={{fontSize:10,color:'#3a4258',textAlign:'center'}}>No stories routed here yet</p>
          </div>
        )}
        {cards.map(c => <EditorialCard key={c.id} card={c} onDragStart={id => { _dragCardId = id }} />)}
      </div>
    </div>
  )
}

function TelegramLane({ brand }) {
  const { telegramLanes } = useMmStore()
  const cards = telegramLanes[brand] || []
  const color = '#24a1de'

  return (
    <div className="lane" style={{borderRight:`1px solid ${color}22`}} data-lane-type="telegram" data-brand={brand}>
      <div className="lane-header" style={{background:color+'0e',borderBottom:`1px solid ${color}22`}}>
        <div style={{width:20,height:20,borderRadius:5,background:color+'20',color,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,fontSize:8,fontWeight:800}}>TG</div>
        <span style={{fontSize:10.5,fontWeight:700,color:'#eeeae2',flex:1}}>Telegram News</span>
        <span style={{fontSize:9.5,fontWeight:700,padding:'1px 6px',borderRadius:4,background:color+'15',color}}>{cards.length}</span>
      </div>
      <div className="lane-cards">
        {!cards.length && <div className="empty-lane"><p style={{fontSize:10,color:'#3a4258',textAlign:'center'}}>No Telegram posts</p></div>}
        {cards.map(c => <EditorialCard key={c.id} card={c} onDragStart={id => { _dragCardId = id }} />)}
      </div>
    </div>
  )
}

function BrandSection({ brand }) {
  const { selectedModels, selectedPlatforms, modelLanes, telegramLanes, platformLanes, editorial } = useMmStore()
  const hasEditorial = !!editorial
  const col = MEDIA_COLORS[brand] || '#a7abb2'
  const abbrs = {'MGC Coin':'MGC','Ranking Platform':'RK','Oasis Coin':'OAS','Jewelry Coin':'JWL'}
  const tags  = {'MGC Coin':'Gaming Utility · Rewards · BNB Smart Chain · RZ Ecosystem','Ranking Platform':'Competition · Profiles · Teams · Tournaments · Community','Oasis Coin':'Metaverse · Gaming · Digital Worlds · Future Utility','Jewelry Coin':'Digital Jewelry · NFTs · Marketplace · Physical Craft'}
  const totalCards = (hasEditorial ? selectedModels.reduce((s,k) => s+(modelLanes[k]?.[brand]?.length||0), 0) : 0)
    + (telegramLanes[brand]?.length || 0)
    + selectedPlatforms.reduce((s,p) => s+(platformLanes[brand]?.[p]?.length||0), 0)
  const lanesRowRef = useRef(null)

  useEffect(() => {
    const el = lanesRowRef.current
    if (!el) return
    const lanes = [...el.querySelectorAll(':scope > .lane')]
    if (lanes.length < 2) return
    lanes.forEach(l => { l.style.flex = 'none' })
    const resizers = []
    lanes.forEach((lane, i) => {
      if (i === lanes.length - 1) return
      const r = document.createElement('div')
      r.className = 'lane-resizer'
      lane.after(r)
      const onDown = e => {
        e.preventDefault()
        const lw = lane.offsetWidth, rw = lane.nextElementSibling.offsetWidth, sx = e.clientX
        r.classList.add('active')
        const onMove = ev => { const dx=ev.clientX-sx; lane.style.width=Math.max(160,lw+dx)+'px'; lane.nextElementSibling.style.width=Math.max(160,rw-dx)+'px' }
        const onUp   = () => { r.classList.remove('active'); document.removeEventListener('mousemove',onMove); document.removeEventListener('mouseup',onUp) }
        document.addEventListener('mousemove', onMove)
        document.addEventListener('mouseup', onUp)
      }
      r.addEventListener('mousedown', onDown)
      resizers.push(() => r.removeEventListener('mousedown', onDown))
    })
    return () => resizers.forEach(fn => fn())
  }, [selectedModels.join(), selectedPlatforms.join(), (telegramLanes[brand] || []).length])

  return (
    <div className="media-section fade-up" style={{borderTop:`2px solid ${col}55`}}>
      <div className="section-header">
        <div style={{width:28,height:28,borderRadius:7,background:col+'20',border:`1px solid ${col}40`,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,fontSize:7.5,fontWeight:800,color:col,letterSpacing:'.02em'}}>{abbrs[brand]||brand.slice(0,2)}</div>
        <div className="brand-header-copy" style={{flex:1,minWidth:0,display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
          <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:14,color:'#eeeae2',whiteSpace:'nowrap'}}>{brand}</span>
          <span style={{fontSize:11,color:'#a7abb2',lineHeight:1.5}}>{tags[brand]}</span>
        </div>
        <span style={{fontSize:11,fontWeight:700,padding:'2px 8px',borderRadius:5,background:col+'15',color:col,border:`1px solid ${col}35`}}>{totalCards} stories</span>
      </div>
      <div className="lanes-row" ref={lanesRowRef}>
        {!!(telegramLanes[brand]?.length) && <TelegramLane brand={brand} />}
        {hasEditorial && selectedModels.map(key => <ModelLane key={key} modelKey={key} brand={brand} />)}
        {selectedPlatforms.map(p => <PlatformLane key={p} brand={brand} plat={p} />)}
      </div>
    </div>
  )
}

export default function MainArea({ mmReport, onOpenReport }) {
  const { selectedMedia } = useMmStore()

  return (
    <main id="mm-main-area">
      <div style={{background:'rgba(240,160,64,.07)',border:'1px solid rgba(240,160,64,.18)',borderRadius:10,padding:'9px 14px',fontSize:11,color:'#c8a060',display:'flex',alignItems:'center',gap:8,flexShrink:0}}>
        <span style={{fontSize:14}}>💡</span>
        <span>Select media brands, platforms, and sources — then click <strong style={{color:'#f0a040'}}>Analyze &amp; Route News</strong>. AI assigns each story to the right brand and format. Drag cards between lanes to reassign.</span>
      </div>

      {mmReport && (
        <div id="report-trigger-bar">
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <div style={{width:7,height:7,borderRadius:'50%',background:'#9b72f5',boxShadow:'0 0 6px rgba(155,114,245,.8)'}}></div>
            <span style={{fontSize:11,color:'#c8cdd8'}}>
              <strong style={{color:'#9b72f5'}}>{mmReport.shortlistedCount}</strong> shortlisted ·{' '}
              {Object.keys(mmReport.perMedia||{}).length} AI editors chose from{' '}
              <strong style={{color:'#eeeae2'}}>{mmReport.fetchedTotal}</strong> fetched ·{' '}
              <strong style={{color:'#ef4455'}}>{Math.max(0, (mmReport.allArticles||[]).filter(a=>a._pipelineStatus!=='too_old').length - mmReport.shortlistedCount)}</strong> rejected ·{' '}
              <strong style={{color:'#f0a040'}}>{mmReport.tooOld}</strong> too old
            </span>
          </div>
          <button onClick={onOpenReport} style={{fontSize:11,fontWeight:700,padding:'6px 14px',borderRadius:8,border:'1px solid rgba(155,114,245,.4)',background:'rgba(155,114,245,.1)',color:'#9b72f5',cursor:'pointer',letterSpacing:'.04em',transition:'opacity .18s'}}
            onMouseEnter={e=>e.currentTarget.style.opacity='.8'} onMouseLeave={e=>e.currentTarget.style.opacity='1'}>
            View Filtering Report
          </button>
        </div>
      )}

      {selectedMedia.map(brand => <BrandSection key={brand} brand={brand} />)}
    </main>
  )
}
