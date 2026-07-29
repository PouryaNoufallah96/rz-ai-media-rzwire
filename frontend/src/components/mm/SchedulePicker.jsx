import { PLAT_COLORS } from '../../store/mmStore'
import { PLAT_ICONS } from '../../utils/platformIcons'

// Platform selector + date/time inputs for the scheduler.
//
// `platformOptions` lets the parent restrict which platforms are offered
// (e.g. only ['X','Telegram'] since Instagram can't auto-post). `platform` is
// controlled by the parent so it can enforce a selection before confirming.
export default function SchedulePicker({
  date, time, onDateChange, onTimeChange, onConfirm, confirmLabel = 'Confirm Schedule',
  platform = '', onPlatformChange, platformOptions = ['X', 'Telegram'],
}) {
  return (
    <div style={{display:'flex',flexDirection:'column',gap:8}}>
      {/* Platform picker — required before Confirm */}
      <div>
        <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:5,letterSpacing:'.06em',textTransform:'uppercase'}}>
          Post to <span style={{fontWeight:400,textTransform:'none',letterSpacing:0,color:'#777e88'}}>(choose one)</span>
        </p>
        <div style={{display:'flex',gap:6}}>
          {platformOptions.map(p => {
            const on = platform === p
            const c = PLAT_COLORS[p] || '#a7abb2'
            return (
              <button key={p} type="button" onClick={() => onPlatformChange?.(p)}
                className={`plat-pick${on ? ' on' : ''}`}
                style={{
                  flex:1, display:'flex', alignItems:'center', justifyContent:'center', gap:5,
                  padding:'8px 6px', fontSize:11, fontWeight:700,
                  color: on ? c : '#a7abb2', borderColor: on ? c+'70' : 'rgba(255,255,255,.1)',
                  background: on ? c+'14' : 'rgba(255,255,255,.03)',
                }}>
                <span style={{display:'inline-flex',alignItems:'center'}}>{PLAT_ICONS[p]}</span>
                {p}
              </button>
            )
          })}
        </div>
      </div>

      {/* Date / time */}
      <div style={{display:'flex',gap:6}}>
        <input type="date" value={date} onChange={e=>onDateChange(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
        <input type="time" value={time} onChange={e=>onTimeChange(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
      </div>
      <button onClick={onConfirm}
        style={{width:'100%',padding:9,fontSize:11,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',border:'none',borderRadius:9,cursor:'pointer',background:'linear-gradient(135deg,#f0a040,#e08030)',color:'#171c26',transition:'opacity .18s'}}
        onMouseEnter={e=>e.currentTarget.style.opacity='.85'} onMouseLeave={e=>e.currentTarget.style.opacity='1'}>
        {confirmLabel}
      </button>
    </div>
  )
}
