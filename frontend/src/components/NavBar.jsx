import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { useLanguageStore, t } from '../store/languageStore'
import rzwireLogo from '../assets/brands/rzwire-logo-theme-5.png'
import { Link, usePathname } from '../router'
import './NavBar.css'

export default function NavBar({ onToggleNav, navOpen: navOpenProp }) {
  const [internalOpen, setInternalOpen] = useState(false)
  const navOpen = onToggleNav ? navOpenProp : internalOpen
  const toggle  = onToggleNav || (() => setInternalOpen(o => !o))
  const pathname = usePathname()
  const { user } = useAuthStore()
  const { language, toggleLanguage } = useLanguageStore()
  const linkClass = (path) => `nav-link${pathname.startsWith(path) ? ' active' : ''}`
  const initial = user?.username ? user.username[0].toUpperCase() : '?'

  return (
    <nav style={{background:'rgba(6,21,54,0.9)',backdropFilter:'blur(18px)',WebkitBackdropFilter:'blur(18px)',borderBottom:'1px solid rgba(126,161,218,.25)',position:'sticky',top:0,zIndex:50,width:'100%'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',padding:'0 24px',height:56}}>
        <Link to="/multimedia" style={{textDecoration:'none',display:'flex',alignItems:'center',gap:12,flexShrink:0}}>
          <span className="rzwire-nav-logo"><img src={rzwireLogo} alt="RZWire" /></span>
          <div style={{display:'flex',alignItems:'center',gap:5,padding:'3px 9px',borderRadius:100,background:'rgba(87,216,199,.1)',border:'1px solid rgba(87,216,199,.34)'}}>
            <svg width="9" height="9" viewBox="0 0 24 24" fill="#87ab9f"><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M4.22 4.22l2.12 2.12M17.66 17.66l2.12 2.12M2 12h3M19 12h3M4.22 19.78l2.12-2.12M17.66 6.34l2.12-2.12" stroke="#87ab9f" strokeWidth="1.5" strokeLinecap="round" fill="none"/></svg>
            <span style={{fontSize:11,fontWeight:700,color:'#87ab9f',letterSpacing:'.04em'}}>AI</span>
          </div>
        </Link>

        <div id="mob-nav-links" style={{display:'flex',alignItems:'center',gap:2}} className={navOpen?'open':''}>
          <Link to="/multimedia" className={linkClass('/multimedia')}>{t(language, 'Multi Media')}</Link>
          <Link to="/analytics" className={linkClass('/analytics')}>{t(language, 'Market Analytics')}</Link>
          <Link to="/about" className={linkClass('/about')}>{t(language, 'About Us')}</Link>
          <Link to="/account" className={linkClass('/account')}>{t(language, 'Account')}</Link>
        </div>

        <div style={{display:'flex',alignItems:'center',gap:8}}>
          <button type="button" className="language-toggle" onClick={toggleLanguage} title={language === 'fa' ? 'Switch to English' : 'Switch to Persian'}>
            <span aria-hidden="true">◉</span><span>{language === 'fa' ? 'EN' : 'FA'}</span>
          </button>
          <button id="mob-menu-btn" onClick={toggle}
            style={{display:'none',width:36,height:36,borderRadius:8,background:'none',border:'none',cursor:'pointer',color:'#a7abb2',alignItems:'center',justifyContent:'center',transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#eeeae2';e.currentTarget.style.background='rgba(255,255,255,.05)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#a7abb2';e.currentTarget.style.background='none'}}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
          <button style={{width:32,height:32,borderRadius:8,background:'none',border:'none',cursor:'pointer',color:'#a7abb2',display:'flex',alignItems:'center',justifyContent:'center',transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#eeeae2';e.currentTarget.style.background='rgba(255,255,255,.05)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#a7abb2';e.currentTarget.style.background='none'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
          </button>
          <Link to="/account" title={user?.username || 'Account'} style={{width:32,height:32,borderRadius:'50%',background:'linear-gradient(135deg,#c9877f,#d9a29b)',display:'flex',alignItems:'center',justifyContent:'center',color:'#11161f',fontWeight:700,fontSize:13,fontFamily:"'Space Grotesk',sans-serif",textDecoration:'none',flexShrink:0}}>
            {initial}
          </Link>
        </div>
      </div>
    </nav>
  )
}
