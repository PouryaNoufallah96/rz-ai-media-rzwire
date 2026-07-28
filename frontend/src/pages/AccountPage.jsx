import { useEffect } from 'react'
import { useNavigate } from '../router'
import { useAuthStore } from '../store/authStore'
import { useAccountStore } from '../store/accountStore'
import NavBar from '../components/NavBar'
import StatsRow from '../components/account/StatsRow'
import PostsByBrand from '../components/account/PostsByBrand'
import ActivityHistory from '../components/account/ActivityHistory'
import RecentKeywords from '../components/account/RecentKeywords'
import SavedForLater, { SavedCardDetail } from '../components/account/SavedForLater'
import ScheduledPosts from '../components/account/ScheduledPosts'
import ChatWidget from '../components/chat/ChatWidget'
import './AccountPage.css'

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

function formatMemberSince(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return '—'
  return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

export default function AccountPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()
  const { summary, fetchSummary, fetchSaved } = useAccountStore()

  useEffect(() => {
    if (user) {
      fetchSummary()
      fetchSaved()
    }
  }, [user])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  if (!user) return null

  const initial = user.username ? user.username[0].toUpperCase() : '?'

  return (
    <>
      <NavBar />
      <div className="account-page">
        <div aria-hidden="true" className="account-glow"></div>
        <div className="account-grid">
          <div className="account-col-left">
            <div className="account-card glass">
              <div className="account-avatar">{initial}</div>
              <h1 className="account-username">{user.username}</h1>
              <p className="account-email">{user.email}</p>
              <p className="account-member-since">Member since {formatMemberSince(user.createdAt)}</p>
              <button type="button" className="account-logout" onClick={handleLogout}>Log Out</button>
            </div>

            <div className="acct-section">
              <StatsRow stats={summary?.stats} />
            </div>

            <div className="acct-section">
              <h2 className="acct-section-title">Posts by Media Brand</h2>
              <PostsByBrand postsByBrand={summary?.postsByBrand} />
            </div>

            <div className="acct-section">
              <h2 className="acct-section-title">Activity History</h2>
              <div className="acct-activity-list-wrap">
                <ActivityHistory activity={summary?.activity} />
              </div>
            </div>

            <div className="acct-section">
              <h2 className="acct-section-title">Recent Keywords</h2>
              <RecentKeywords keywords={summary?.recentKeywords} />
            </div>

            <div className="acct-section">
              <h2 className="acct-section-title">Scheduled Posts</h2>
              <div className="acct-scheduled-list-wrap">
                <ScheduledPosts />
              </div>
            </div>
          </div>

          <div className="account-col-mid">
            <div className="acct-section">
              <h2 className="acct-section-title">Saved for Later</h2>
              <SavedForLater />
            </div>
          </div>

          <div className="account-col-right">
            <SavedCardDetail />
          </div>
        </div>
      </div>
      <ChatWidget />
    </>
  )
}
