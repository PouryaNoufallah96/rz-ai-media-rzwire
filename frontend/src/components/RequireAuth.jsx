import { useAuthStore } from '../store/authStore'
import rzwireLogo from '../assets/brands/rzwire-logo-theme-5.png'
import { Redirect } from '../router'

function LoadingScreen() {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:18, alignItems:'center', justifyContent:'center', width:'100%', height:'100vh', background:'radial-gradient(circle at 50% 45%,#102b36,#070919 42%)' }}>
      <style>{'@keyframes rzwire-pulse{50%{transform:scale(1.04);filter:drop-shadow(0 0 24px rgba(76,226,207,.48))}}'}</style>
      <span style={{ width:190, animation:'rzwire-pulse 1.8s ease-in-out infinite' }}><img src={rzwireLogo} alt="RZWire is loading" style={{display:'block',width:'100%'}} /></span>
      <span style={{color:'#7ee8db',fontSize:11,fontWeight:800,letterSpacing:'.18em',textTransform:'uppercase'}}>Loading workspace</span>
    </div>
  )
}

export function RequireAuth({ children }) {
  const { user, authChecked } = useAuthStore()
  if (!authChecked) return <LoadingScreen />
  if (!user) return <Redirect to="/login" replace />
  return children
}

export function GuestOnly({ children }) {
  const { user, authChecked } = useAuthStore()
  if (!authChecked) return <LoadingScreen />
  if (user) return <Redirect to="/multimedia" replace />
  return children
}
