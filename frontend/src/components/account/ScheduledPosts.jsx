import { useEffect, useState } from 'react'
import { useAccountStore } from '../../store/accountStore'
import { MEDIA_COLORS, PLAT_COLORS } from '../../store/mmStore'
import { PLAT_ICONS } from '../../utils/platformIcons'
import SchedulePicker from '../mm/SchedulePicker'

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
function formatScheduled(iso) {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2,'0')
  const ampm = h >= 12 ? 'PM' : 'AM', h12 = h % 12 || 12
  return `${MONTHS[d.getMonth()]} ${d.getDate()} · ${h12}:${m} ${ampm}`
}

function toDateTimeParts(iso) {
  const d = new Date(iso)
  const pad = n => String(n).padStart(2,'0')
  return { date: `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`, time: `${pad(d.getHours())}:${pad(d.getMinutes())}` }
}

const STATUS_LABEL = { pending: 'Pending', posted: 'Posted', failed: 'Failed', cancelled: 'Cancelled' }
const STATUS_CLASS = { pending: 'sb-scheduled', posted: 'sb-published', failed: 'sb-failed', cancelled: 'sb-saved' }

export default function ScheduledPosts() {
  const { scheduledPosts, fetchScheduled, cancelScheduled, rescheduleScheduled } = useAccountStore()
  const [editingId, setEditingId] = useState(null)
  const [editDate, setEditDate] = useState('')
  const [editTime, setEditTime] = useState('')

  useEffect(() => { fetchScheduled() }, [])

  if (!scheduledPosts.length) return <p className="acct-empty">Nothing scheduled — use "Schedule" on a post to queue an auto-post.</p>

  function startEdit(p) {
    const { date, time } = toDateTimeParts(p.scheduled_at)
    setEditingId(p.id); setEditDate(date); setEditTime(time)
  }

  async function confirmEdit() {
    const iso = new Date(`${editDate}T${editTime}`).toISOString()
    if (new Date(iso) <= new Date()) { alert('Please pick a time in the future'); return }
    if (await rescheduleScheduled(editingId, iso)) setEditingId(null)
  }

  return (
    <div className="acct-saved-list">
      {scheduledPosts.map(p => {
        const mc = MEDIA_COLORS[p.brand] || '#a7abb2'
        const pc = PLAT_COLORS[p.platform] || '#a7abb2'
        return (
          <div key={p.id} className="acct-saved-card" style={{cursor:'default'}}>
            <div className="acct-saved-header">
              <span className="acct-brand-tag" style={{background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{p.brand}</span>
              <span style={{width:18,height:18,borderRadius:5,display:'flex',alignItems:'center',justifyContent:'center',background:pc+'1a',color:pc}}>{PLAT_ICONS[p.platform]}</span>
              <span className={`sbadge ${STATUS_CLASS[p.status]}`} style={{marginLeft:'auto'}}>{STATUS_LABEL[p.status]}</span>
            </div>
            <div className="acct-saved-headline">{p.headline}</div>
            <div className="acct-saved-summary">{p.copy}</div>
            <div className="acct-saved-meta">
              <span className="sbadge sb-ready">{formatScheduled(p.scheduled_at)}</span>
              {p.has_image && <span className="sbadge sb-image" style={{fontSize:9.5}}>🖼 Image</span>}
              {p.status === 'failed' && p.error && <span style={{fontSize:10,color:'#ef4455'}}>{p.error}</span>}
              {p.status === 'pending' && (
                <>
                  <button className="btn-ghost" style={{fontSize:10,padding:'3px 8px',marginLeft:'auto'}} onClick={()=>startEdit(p)}>Edit</button>
                  <button className="btn-ghost" style={{fontSize:10,padding:'3px 8px'}} onClick={()=>cancelScheduled(p.id)}>Cancel</button>
                </>
              )}
            </div>
            {editingId === p.id && (
              <div style={{marginTop:10}}>
                <SchedulePicker date={editDate} time={editTime} onDateChange={setEditDate} onTimeChange={setEditTime} onConfirm={confirmEdit} confirmLabel="Save Time" />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
