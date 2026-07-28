import { useState, useEffect } from 'react'
import { useMmStore, API_BASE } from '../store/mmStore'
import { useAnalyzeAndRoute } from '../hooks/useAnalyzeAndRoute'
import Sidebar from '../components/mm/Sidebar'
import MainArea from '../components/mm/LaneBoard'
import PreviewPanel from '../components/mm/PreviewPanel'
import NavBar from '../components/NavBar'
import FilteringReportModal from '../components/mm/FilteringReportModal'
import ChatWidget from '../components/chat/ChatWidget'
import { useLanguageStore } from '../store/languageStore'
import './MultimediaPage.css'

const SIDEBAR_MIN_WIDTH = 262
const SIDEBAR_MAX_WIDTH = 560

// Load the HuggingFace semantic router as a module script (same as original)
let _semLoaded = false
function loadSemRouter() {
  if (_semLoaded) return
  _semLoaded = true
  const s = document.createElement('script')
  s.type = 'module'
  s.textContent = `
import { pipeline } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3';
const PROFILES = {
  'MGC Coin': 'Meta Games Coin MGC, gaming utility token, player rewards, creator rewards, tournament rewards, play to earn, GameFi, blockchain gaming, gaming economy, digital ownership, BNB Smart Chain, BEP-20, Ranking.Game, RZ ecosystem participation.',
  'Ranking Platform': 'Competitive gaming platform, not a token, player profiles, teams, PvP matches, digital games, physical games, tournaments, organizers, referees, rankings, leaderboards, match results, gaming communities, gaming centers, sports clubs, Ranking.Game.',
  'Oasis Coin': 'OASIS token, RZOASIS Galaxy, planned metaverse utility, metaverse gaming, virtual worlds, virtual land, digital identity, game assets, marketplaces, energy systems, ranks and levels, BNB Smart Chain, BEP-20, long-term world building.',
  'Jewelry Coin': 'Jewelry Token, Jewellery Game, digital jewelry, virtual gem extraction, jewelry design, NFT minting, in-game marketplace, creator economy, digital collectibles, physical jewelry production, merchant tools, augmented reality try-on, BEP-20, Binance Smart Chain.',
};
let _extractor = null, _brandVecs = null, _initPromise = null;
async function _load() {
  _extractor = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
  _brandVecs = {};
  for (const [brand, text] of Object.entries(PROFILES)) {
    const out = await _extractor(text, { pooling:'mean', normalize:true });
    _brandVecs[brand] = Array.from(out.data);
  }
}
function _cosine(a,b) { let d=0; for(let i=0;i<a.length;i++) d+=a[i]*b[i]; return d; }
const EMBED_CHUNK = 12;
async function embedArticles(articles) {
  if (!_initPromise) _initPromise = _load();
  await _initPromise;
  for (let c = 0; c < articles.length; c += EMBED_CHUNK) {
    const chunk = articles.slice(c, c + EMBED_CHUNK);
    const texts = chunk.map(art => (art.title+' '+art.desc).slice(0,512));
    const out = await _extractor(texts,{pooling:'mean',normalize:true});
    const dim = out.dims[out.dims.length-1];
    const flat = out.data;
    chunk.forEach((art,k) => {
      const vec = flat.slice(k*dim, (k+1)*dim);
      art._semScores = {};
      for (const [brand,bv] of Object.entries(_brandVecs)) {
        art._semScores[brand] = Math.max(0,_cosine(vec,bv))*100;
      }
    });
  }
}
_initPromise = _load().catch(err => { window._semRouterError = err.message; });
window._semRouter = { embedArticles, _initPromise };
  `
  document.head.appendChild(s)
}

export default function MultimediaPage() {
  const { mmReport, setReportOpen, initPlatformLanes, activeCard } = useMmStore()
  const language = useLanguageStore(state => state.language)
  const previewSessionKey = activeCard
    ? `${activeCard.id || ''}|${activeCard.platform || ''}|${activeCard.headline || ''}`
    : 'closed'
  const analyzeAndRoute = useAnalyzeAndRoute()
  const [topics, setTopics] = useState('')
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = Number(window.localStorage.getItem('rzwire-sidebar-width'))
    return Number.isFinite(saved) ? Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, saved)) : SIDEBAR_MIN_WIDTH
  })

  useEffect(() => {
    loadSemRouter()
    initPlatformLanes()
  }, [])

  useEffect(() => {
    window.localStorage.setItem('rzwire-sidebar-width', String(sidebarWidth))
  }, [sidebarWidth])

  function handleAnalyze() {
    analyzeAndRoute(topics)
  }

  function startSidebarResize(event) {
    if (window.innerWidth <= 768) return
    event.preventDefault()
    const startX = event.clientX
    const startWidth = sidebarWidth
    const previousUserSelect = document.body.style.userSelect
    document.body.style.userSelect = 'none'

    const onMove = moveEvent => {
      const dragDistance = moveEvent.clientX - startX
      const width = startWidth + (language === 'fa' ? -dragDistance : dragDistance)
      setSidebarWidth(Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width)))
    }
    const onUp = () => {
      document.body.style.userSelect = previousUserSelect
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  return (
    <>
      <div aria-hidden="true" style={{position:'fixed',inset:0,zIndex:0,pointerEvents:'none',background:'radial-gradient(ellipse 60% 40% at 50% 0%,rgba(0,212,160,.07) 0%,transparent 70%),radial-gradient(ellipse 50% 50% at 80% 80%,rgba(155,114,245,.07) 0%,transparent 70%),radial-gradient(ellipse 40% 30% at 20% 70%,rgba(240,160,64,.05) 0%,transparent 70%)'}}></div>
      <div id="mob-backdrop" className={navOpen?'open':''} onClick={()=>setNavOpen(false)}></div>
      <NavBar onToggleNav={()=>setNavOpen(o=>!o)} navOpen={navOpen} />
      <div id="mm-layout" style={{position:'relative',zIndex:10}}>
        <Sidebar topics={topics} setTopics={setTopics} onAnalyze={handleAnalyze} width={sidebarWidth} />
        <div id="mm-sidebar-resizer" role="separator" aria-orientation="vertical" aria-label="Resize control panel" onMouseDown={startSidebarResize} />
        <MainArea mmReport={mmReport} onOpenReport={() => setReportOpen(true)} />
      </div>
      <PreviewPanel key={previewSessionKey} />
      <FilteringReportModal />
      <ChatWidget activeCard={activeCard} />
    </>
  )
}
