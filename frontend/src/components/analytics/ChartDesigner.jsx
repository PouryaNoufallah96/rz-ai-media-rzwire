import { useEffect, useState } from 'react'
import { Check, RotateCcw, Save } from 'lucide-react'
import {
  CHART_PRESETS,
  COLORBLIND_SERIES_COLORS,
  FALLBACK_SERIES_COLORS,
  HIGH_CONTRAST_SERIES_COLORS,
  LEGEND_POSITIONS,
  normalizeHexColor,
  registrySeriesColor,
} from './chartStyle'

const SWATCHES = [...new Set([...FALLBACK_SERIES_COLORS, ...COLORBLIND_SERIES_COLORS, ...HIGH_CONTRAST_SERIES_COLORS])]

function HexField({ value, label, onCommit }) {
  const [draft, setDraft] = useState(value)
  const [invalid, setInvalid] = useState(false)

  useEffect(() => {
    setDraft(value)
    setInvalid(false)
  }, [value])

  function commit() {
    const color = normalizeHexColor(draft)
    if (!color) {
      setInvalid(true)
      return
    }
    setInvalid(false)
    setDraft(color)
    onCommit(color)
  }

  return <input
    className={invalid ? 'invalid' : ''}
    value={draft}
    aria-label={label}
    spellCheck="false"
    maxLength="7"
    onChange={event => setDraft(event.target.value)}
    onBlur={commit}
    onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); commit() } }}
  />
}

function ChoiceGroup({ label, value, options, onChange }) {
  return <div className="analytics-designer-choice"><strong>{label}</strong><div>{options.map(option => <button key={option.id} type="button" className={value === option.id ? 'selected' : ''} onClick={() => onChange(option.id)}>{option.label}{value === option.id && <Check size={12} />}</button>)}</div></div>
}

export default function ChartDesigner({
  style,
  series,
  tokens,
  ownerSelected,
  loading,
  saving,
  message,
  issues,
  onPreset,
  onBackground,
  onSeriesColor,
  onResetSeries,
  onOption,
  onReset,
  onSave,
}) {
  return <div className="analytics-chart-designer">
    <div className="analytics-designer-head"><div><strong>Chart Designer</strong><span>Style only. Verified prices, dates, axes, and line geometry stay locked.</span></div>{style.presetId === 'custom' && <em>Custom</em>}</div>

    <div className="analytics-designer-presets" aria-label="Chart style presets">{CHART_PRESETS.map(preset => <button key={preset.id} type="button" className={style.presetId === preset.id ? 'selected' : ''} onClick={() => onPreset(preset.id)}>{preset.label}{style.presetId === preset.id && <Check size={13} />}</button>)}</div>

    <div className="analytics-designer-color-section">
      <div className="analytics-background-control"><strong>Solid background</strong><div><input type="color" value={style.backgroundColor} aria-label="Chart background color" onChange={event => onBackground(event.target.value)} /><HexField value={style.backgroundColor} label="Chart background hex color" onCommit={onBackground} /></div></div>
      <div className="analytics-series-color-list">{series.map((item, index) => <article key={item.id}>
        <div className="analytics-series-color-title"><i style={{background:item.color}} /><span><strong>{item.symbol}</strong><small>{item.name}</small></span><button type="button" onClick={() => onResetSeries(item.id, registrySeriesColor(item, index, tokens))}>Reset</button></div>
        <div className="analytics-series-color-controls"><input type="color" value={item.color} aria-label={`${item.symbol} series color`} onChange={event => onSeriesColor(item.id, event.target.value)} /><HexField value={item.color} label={`${item.symbol} series hex color`} onCommit={color => onSeriesColor(item.id, color)} /><div className="analytics-color-swatches">{SWATCHES.map(color => <button key={color} type="button" className={item.color === color ? 'selected' : ''} style={{background:color}} onClick={() => onSeriesColor(item.id, color)} aria-label={`Use ${color} for ${item.symbol}`} />)}</div></div>
      </article>)}</div>
    </div>

    <details className="analytics-designer-advanced">
      <summary>Advanced styling <span>Legend, line, markers, and grid</span></summary>
      <div className="analytics-designer-options">
        <ChoiceGroup label="Legend location" value={style.legend.position} options={LEGEND_POSITIONS} onChange={value => onOption('legend.position', value)} />
        <ChoiceGroup label="Legend format" value={style.legend.format} options={[{id:'symbol', label:'Symbol only'}, {id:'symbol-change', label:'Symbol + change'}]} onChange={value => onOption('legend.format', value)} />
        <ChoiceGroup label="Line thickness" value={style.lineWidth} options={[{id:2, label:'2 px'}, {id:4, label:'4 px'}, {id:6, label:'6 px'}]} onChange={value => onOption('lineWidth', value)} />
        <ChoiceGroup label="Markers" value={style.markers} options={[{id:'none', label:'None'}, {id:'endpoints', label:'Endpoints'}, {id:'all', label:'Every point'}]} onChange={value => onOption('markers', value)} />
        <ChoiceGroup label="Grid strength" value={style.gridStrength} options={[{id:'none', label:'None'}, {id:'subtle', label:'Subtle'}, {id:'standard', label:'Standard'}]} onChange={value => onOption('gridStrength', value)} />
      </div>
    </details>

    {!!issues.length && <div className="analytics-designer-issues">{issues.map(issue => <p key={issue}>{issue}</p>)}</div>}
    {message && <p className={`analytics-designer-message ${message.type || ''}`}>{message.text}</p>}
    <div className="analytics-designer-actions"><button type="button" onClick={onReset}><RotateCcw size={14} />Reset to Clean Light</button><button type="button" className="save" disabled={!ownerSelected || loading || saving || !!issues.length} onClick={onSave}><Save size={14} />{saving ? 'Saving…' : loading ? 'Loading default…' : 'Save as Brand Default'}</button></div>
    {!ownerSelected && <small className="analytics-designer-owner-note">Choose a visual owner to save a private brand default.</small>}
  </div>
}
