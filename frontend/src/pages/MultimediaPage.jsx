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
      <div aria-hidden="true" style={{position:'fixed',inset:0,zIndex:0,pointerEvents:'none',background:'radial-gradient(ellipse 60% 40% at 50% 0%,rgba(17,51,115,.34) 0%,transparent 70%),radial-gradient(ellipse 50% 50% at 88% 8%,rgba(255,113,104,.055) 0%,transparent 70%),radial-gradient(ellipse 40% 30% at 18% 82%,rgba(87,216,199,.045) 0%,transparent 70%)'}}></div>
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
