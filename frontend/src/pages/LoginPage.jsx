import { useEffect, useState } from 'react'
import { useNavigate } from '../router'
import { useAuthStore } from '../store/authStore'
import rzwireLogo from '../assets/brands/rzwire-logo-theme-5.png'
import './AuthPage.css'

const FEATURES = [
  {
    title: 'Smart Analytics',
    desc: 'Track performance and get actionable insights.',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 17l6-6 4 4 8-8" />
        <path d="M21 7v6h-6" />
      </svg>
    ),
  },
  {
    title: 'Multi-Platform',
    desc: 'Manage all your social platforms in one place.',
    color: 'violet',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </svg>
    ),
  },
  {
    title: 'AI Automation',
    desc: 'Let AI handle the heavy lifting for you.',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="10" width="18" height="10" rx="2" />
        <path d="M12 10V6" />
        <circle cx="12" cy="4" r="1.5" />
        <line x1="8" y1="15" x2="8" y2="15" />
        <line x1="16" y1="15" x2="16" y2="15" />
      </svg>
    ),
  },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, authError } = useAuthStore()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showForgotNote, setShowForgotNote] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const root = document.documentElement
    const previous = { lang: root.lang, dir: root.dir }
    root.lang = 'en'
    root.dir = 'ltr'
    return () => {
      root.lang = previous.lang
      root.dir = previous.dir
    }
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!identifier || !password || submitting) return
    setSubmitting(true)
    const ok = await login(identifier, password, rememberMe)
    setSubmitting(false)
    if (ok) navigate('/multimedia')
  }

  return (
    <div className="auth-page" data-no-localize="true">
      <div aria-hidden="true" className="auth-glow"></div>

      <div className="auth-wrap">
      <div className="auth-left">
        <div className="auth-logo">
          <span className="auth-logo-crop"><img src={rzwireLogo} alt="RZWire" className="auth-logo-image" /></span>
        </div>

        <div>
          <h1 className="auth-headline">
            <span className="auth-headline-accent">AI-</span>Powered<br />
            Multi-Brand Publishing
          </h1>
          <p className="auth-subtitle">Automate your content creation, scheduling, and analytics across multiple platforms with intelligent insights.</p>
        </div>

        <div className="auth-features">
          {FEATURES.map(f => (
            <div className="auth-feature" key={f.title}>
              <div className={`auth-feature-icon ${f.color === 'violet' ? 'auth-feature-icon--violet' : ''}`}>{f.icon}</div>
              <div>
                <p className="auth-feature-title">{f.title}</p>
                <p className="auth-feature-desc">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="auth-left-footer">© 2026 RZWire. All rights reserved.</p>
      </div>

      <div className="auth-right">
        <div className="auth-card glass">
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtext">Sign in to your account to continue</p>

          <form onSubmit={handleSubmit}>
            <label className="auth-label" htmlFor="auth-identifier">Username</label>
            <div className="auth-input-wrap">
              <svg className="auth-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input
                id="auth-identifier"
                className="cr-input auth-input"
                type="text"
                autoComplete="username"
                value={identifier}
                onChange={e => setIdentifier(e.target.value)}
                placeholder="Enter your username"
              />
            </div>

            <label className="auth-label" htmlFor="auth-password">Password</label>
            <div className="auth-input-wrap">
              <svg className="auth-input-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                id="auth-password"
                className="cr-input auth-input"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
              />
              <button
                type="button"
                className="auth-eye-btn"
                onClick={() => setShowPassword(s => !s)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/>
                    <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 11 7 11 7a13.16 13.16 0 0 1-1.67 2.68"/>
                    <path d="M6.61 6.61A13.526 13.526 0 0 0 1 12s4 7 11 7a9.74 9.74 0 0 0 5.39-1.61"/>
                    <line x1="2" y1="2" x2="22" y2="22"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7Z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>

            <div className="auth-options-row">
              <label className="auth-remember">
                <input type="checkbox" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} />
                Remember me
              </label>
              <button type="button" className="auth-forgot-link" onClick={() => setShowForgotNote(s => !s)}>
                Forgot password?
              </button>
            </div>
            {showForgotNote && (
              <p className="auth-forgot-note">Contact an admin to reset your password.</p>
            )}

            {authError && <div className="auth-error">{authError}</div>}

            <button type="submit" className="btn-mint auth-submit" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
      </div>
    </div>
  )
}
