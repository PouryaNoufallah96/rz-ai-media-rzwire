import { useEffect } from 'react'
import MultimediaPage from './pages/MultimediaPage'
import AboutPage from './pages/AboutPage'
import LoginPage from './pages/LoginPage'
import AccountPage from './pages/AccountPage'
import AnalyticsPage from './pages/AnalyticsPage'
import { RequireAuth, GuestOnly } from './components/RequireAuth'
import { useAuthStore } from './store/authStore'
import { useLanguageStore, localizeDocument } from './store/languageStore'
import { Redirect, usePathname } from './router'
import './theme.css'

export default function App() {
  const language = useLanguageStore(s => s.language)
  const pathname = usePathname()
  const interfaceLanguage = pathname === '/login' ? 'en' : language

  useEffect(() => {
    useAuthStore.getState().checkAuth()
  }, [])

  useEffect(() => {
    document.documentElement.lang = interfaceLanguage === 'fa' ? 'fa' : 'en'
    document.documentElement.dir = interfaceLanguage === 'fa' ? 'rtl' : 'ltr'
    return localizeDocument(interfaceLanguage)
  }, [interfaceLanguage])

  let page
  if (pathname === '/login') page = <GuestOnly><LoginPage /></GuestOnly>
  else if (pathname === '/multimedia') page = <RequireAuth><MultimediaPage /></RequireAuth>
  else if (pathname === '/analytics') page = <RequireAuth><AnalyticsPage /></RequireAuth>
  else if (pathname === '/about') page = <RequireAuth><AboutPage /></RequireAuth>
  else if (pathname === '/account') page = <RequireAuth><AccountPage /></RequireAuth>
  else page = <RequireAuth><Redirect to="/multimedia" replace /></RequireAuth>

  return <div className={interfaceLanguage === 'fa' ? 'app-fa' : 'app-en'}>{page}</div>
}
