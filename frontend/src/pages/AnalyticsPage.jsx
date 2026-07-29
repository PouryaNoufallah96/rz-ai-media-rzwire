import { useMemo, useState } from 'react'
import { ArrowRight, CalendarDays, Check, ImageIcon, LineChart, Sparkles } from 'lucide-react'
import NavBar from '../components/NavBar'
import ChatWidget from '../components/chat/ChatWidget'
import { API_BASE, IMAGE_MODEL_OPTIONS } from '../store/mmStore'
import mgcLogo from '../assets/brands/mgc-coin-logo.png'
import oasisLogo from '../assets/brands/oasis-coin-logo.png'
import jewelryLogo from '../assets/brands/jewelry-coin-logo.png'
import './AnalyticsPage.css'

const TOKENS = [
  { id:'mgc', name:'MGC Coin', symbol:'MGC', brand:'MGC Coin', logo:mgcLogo, color:'#d9b91d', start:5.92, end:6.42, change:8.45 },
  { id:'oasis', name:'Oasis Coin', symbol:'OASIS', brand:'Oasis Coin', logo:oasisLogo, color:'#87ab9f', start:.702, end:.786, change:11.97 },
  { id:'jewelry', name:'Jewelry Coin', symbol:'JEWELRY', brand:'Jewelry Coin', logo:jewelryLogo, color:'#a89cff', start:33.50, end:41.19, change:22.96 },
]

const COMPARE_TOKENS = [
  { symbol:'BTC', name:'Bitcoin', change:-4.22, price:'$65,089.77' },
  { symbol:'XRP', name:'XRP', change:6.20, price:'$1.374' },
  { symbol:'ETH', name:'Ethereum', change:3.84, price:'$3,412.08' },
  { symbol:'BNB', name:'BNB', change:5.12, price:'$612.64' },
]

const PERIODS = ['24h', '7d', '30d', '90d', '1y', 'Custom']

const TEMPLATES = [
  { id:'phone', name:'Phone comparison', description:'Two indexed price lines inside a mobile market view.', icon:'phone' },
  { id:'laptop', name:'Dashboard frame', description:'Wide chart presentation inside a premium laptop frame.', icon:'laptop' },
  { id:'growth', name:'Growth spotlight', description:'One coin, start and end values, and a bold growth claim.', icon:'growth' },
  { id:'native', name:'Clean RZWire chart', description:'Original chart with no third-party interface or device.', icon:'native' },
]

const SERIES = {
  mgc:[38,40,39,43,45,44,48,51,49,54,57,55,60,64,62,68,70,73,77,76,82,86,91],
  oasis:[32,35,34,39,43,42,47,45,50,53,51,58,61,59,66,70,69,74,79,78,86,89,94],
  jewelry:[26,29,31,30,36,39,43,41,49,52,51,58,60,66,63,71,76,80,78,87,91,95,99],
  compare:[52,50,54,49,51,47,48,44,46,43,45,42,44,40,42,39,41,38,40,37,39,36,35],
}

function points(values, width=620, height=220, pad=18) {
  const min = Math.min(...values)
  const max = Math.max(...values)
  return values.map((value, index) => {
    const x = pad + index * ((width - pad * 2) / (values.length - 1))
    const y = height - pad - ((value - min) / Math.max(1, max - min)) * (height - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function TemplateMiniature({ type }) {
  return (
    <div className={`analytics-template-mini analytics-template-mini--${type}`} aria-hidden="true">
      <span className="analytics-mini-title" />
      <span className="analytics-mini-device">
        <i /><i /><i />
      </span>
      <span className="analytics-mini-footer" />
    </div>
  )
}

function ChartPreview({ token, compare, compareEnabled, period, metric, template, generatedBackground }) {
  const primaryPoints = points(SERIES[token.id])
  const comparisonPoints = points(SERIES.compare)
  const title = compareEnabled ? `${token.symbol} vs ${compare.symbol}` : `${token.symbol} price journey`
  const result = compareEnabled
    ? `${token.symbol} ${token.change >= 0 ? 'rose' : 'fell'} ${Math.abs(token.change).toFixed(2)}% while ${compare.symbol} ${compare.change >= 0 ? 'rose' : 'fell'} ${Math.abs(compare.change).toFixed(2)}%`
    : `${token.symbol} moved from $${token.start} to $${token.end}`

  return (
    <div className={`analytics-poster analytics-poster--${template}`} style={generatedBackground ? {backgroundImage:`linear-gradient(rgba(17,22,31,.68),rgba(17,22,31,.86)),url(data:image/png;base64,${generatedBackground})`} : undefined}>
      <div className="analytics-poster-topline"><span>Sample preview</span><span>Live market feed pending</span></div>
      <header>
        <div>
          <p>{period === '30d' ? '1 month' : period} {compareEnabled ? 'comparison' : 'movement'}</p>
          <h2>{title}</h2>
        </div>
        <img src={token.logo} alt={`${token.name} logo`} />
      </header>

      <div className={`analytics-chart-device analytics-chart-device--${template}`}>
        <div className="analytics-device-bar"><span /><span /><span /></div>
        <div className="analytics-chart-heading">
          <span><i style={{background:token.color}} />{token.symbol}</span>
          {compareEnabled && <><b>vs</b><span><i className="compare-dot" />{compare.symbol}</span></>}
        </div>
        <div className="analytics-range-tabs"><span>1h</span><span>24h</span><span>7d</span><span className="selected">{period}</span><span>90d</span><span>1y</span></div>
        <svg viewBox="0 0 620 220" role="img" aria-label={`${title} sample ${metric.toLowerCase()} chart`}>
          <path className="analytics-chart-grid" d="M18 40H602M18 95H602M18 150H602M18 202H602" />
          <polyline className="analytics-series analytics-series--primary" style={{stroke:token.color}} points={primaryPoints} />
          {compareEnabled && <polyline className="analytics-series analytics-series--compare" points={comparisonPoints} />}
        </svg>
        <div className="analytics-chart-legend">
          <span><i style={{background:token.color}} />{token.symbol} {token.change >= 0 ? '+' : ''}{token.change.toFixed(2)}%</span>
          {compareEnabled && <span><i className="compare-dot" />{compare.symbol} {compare.change >= 0 ? '+' : ''}{compare.change.toFixed(2)}%</span>}
        </div>
      </div>

      <div className="analytics-poster-result">{result}</div>
      <footer><span>RZWire Market Analytics</span><span>Source added after live connection</span></footer>
    </div>
  )
}

export default function AnalyticsPage() {
  const [tokenId, setTokenId] = useState('mgc')
  const [compareEnabled, setCompareEnabled] = useState(true)
  const [compareSymbol, setCompareSymbol] = useState('XRP')
  const [period, setPeriod] = useState('30d')
  const [metric, setMetric] = useState('Price performance')
  const [format, setFormat] = useState('Portrait · 1080 × 1350')
  const [template, setTemplate] = useState('phone')
  const [imageModel, setImageModel] = useState('openai/gpt-5.4-image-2')
  const [direction, setDirection] = useState('Premium financial editorial background, restrained lighting, clear central chart zone, no text or numbers.')
  const [generatedBackground, setGeneratedBackground] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  const token = TOKENS.find(item => item.id === tokenId) || TOKENS[0]
  const compare = COMPARE_TOKENS.find(item => item.symbol === compareSymbol) || COMPARE_TOKENS[0]
  const selectedTemplate = TEMPLATES.find(item => item.id === template) || TEMPLATES[0]
  const summary = useMemo(() => compareEnabled
    ? `${token.symbol} versus ${compare.symbol}, ${period}, ${metric.toLowerCase()}`
    : `${token.symbol}, ${period}, ${metric.toLowerCase()}`,
  [token, compare, compareEnabled, period, metric])

  async function generateBackground() {
    if (generating) return
    setGenerating(true)
    setError('')
    setGeneratedBackground('')
    try {
      const response = await fetch(`${API_BASE}/api/image/generate`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          article:{title:`${summary}. Template: ${selectedTemplate.name}`},
          platform:'Instagram',
          mediaBrand:token.brand,
          sentiment:token.change >= 0 ? 'Bullish' : 'Bearish',
          model:imageModel,
          copy:`Create the decorative art layer for a verified market analytics post about ${summary}.`,
          imageDirection:`${direction} Generate background artwork only. Leave generous uncluttered space for an exact data chart, token logo, headline, dates, and statistics that will be overlaid later by RZWire. Do not render charts, interfaces, devices, logos, letters, numbers, prices, percentages, tickers, watermarks, or captions.`,
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.imageB64) throw new Error(data.error || 'The image model did not return a background.')
      setGeneratedBackground(data.imageB64)
    } catch (err) {
      setError(err.message || 'Background generation failed.')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="analytics-page">
      <NavBar />
      <main className="analytics-workspace">
        <section className="analytics-intro">
          <div>
            <p className="analytics-eyebrow"><LineChart size={16} /> Market Analytics</p>
            <h1>Turn verified price movement into a visual story.</h1>
            <p>Choose the market data first, select a reusable design, then let an image model create only the decorative art layer around an accurate RZWire chart.</p>
          </div>
          <div className="analytics-steps" aria-label="Analytics post workflow">
            <span className="active"><b>1</b>Data</span><i /><span><b>2</b>Design</span><i /><span><b>3</b>Generate</span>
          </div>
        </section>

        <div className="analytics-layout">
          <aside className="analytics-controls">
            <section className="analytics-control-section">
              <div className="analytics-section-heading"><span>01</span><div><h2>Select a token</h2><p>Three RZWire coins are ready for initial setup.</p></div></div>
              <div className="analytics-token-grid">
                {TOKENS.map(item => (
                  <button key={item.id} type="button" className={tokenId === item.id ? 'selected' : ''} onClick={() => setTokenId(item.id)}>
                    <img src={item.logo} alt="" /><span><strong>{item.symbol}</strong><small>{item.name}</small></span>{tokenId === item.id && <Check size={15} />}
                  </button>
                ))}
              </div>
            </section>

            <section className="analytics-control-section">
              <div className="analytics-section-heading"><span>02</span><div><h2>Define the market view</h2><p>Choose the period, metric, and optional comparison.</p></div></div>
              <label className="analytics-switch"><input type="checkbox" checked={compareEnabled} onChange={event => setCompareEnabled(event.target.checked)} /><span />Compare with another coin</label>
              {compareEnabled && <label>Comparison coin<select value={compareSymbol} onChange={event => setCompareSymbol(event.target.value)}>{COMPARE_TOKENS.map(item => <option key={item.symbol} value={item.symbol}>{item.name} · {item.symbol}</option>)}</select></label>}
              <div className="analytics-field-label"><CalendarDays size={15} />Period</div>
              <div className="analytics-periods">{PERIODS.map(item => <button key={item} type="button" className={period === item ? 'selected' : ''} onClick={() => setPeriod(item)}>{item}</button>)}</div>
              <div className="analytics-two-fields">
                <label>Metric<select value={metric} onChange={event => setMetric(event.target.value)}><option>Price performance</option><option>Market capitalization</option><option>Trading volume</option><option>OHLC candles</option></select></label>
                <label>Output format<select value={format} onChange={event => setFormat(event.target.value)}><option>Portrait · 1080 × 1350</option><option>Square · 1080 × 1080</option><option>Story · 1080 × 1920</option><option>Landscape · 1600 × 900</option></select></label>
              </div>
              <div className="analytics-data-note"><span>Sample mode</span>Contract and pool mappings are still required before these figures become live.</div>
            </section>

            <section className="analytics-control-section">
              <div className="analytics-section-heading"><span>03</span><div><h2>Choose a template</h2><p>These samples preserve exact data as a locked chart layer.</p></div></div>
              <div className="analytics-template-grid">
                {TEMPLATES.map(item => (
                  <button key={item.id} type="button" className={template === item.id ? 'selected' : ''} onClick={() => setTemplate(item.id)}>
                    <TemplateMiniature type={item.icon} /><strong>{item.name}</strong><small>{item.description}</small>
                  </button>
                ))}
              </div>
            </section>

            <section className="analytics-control-section analytics-generation-controls">
              <div className="analytics-section-heading"><span>04</span><div><h2>Generate the art layer</h2><p>The model styles the background; RZWire keeps every number exact.</p></div></div>
              <label>Image model<select value={imageModel} onChange={event => setImageModel(event.target.value)}>{IMAGE_MODEL_OPTIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
              <label>Creative direction<textarea rows="3" value={direction} onChange={event => setDirection(event.target.value)} /></label>
              <button type="button" className="analytics-generate" disabled={generating} onClick={generateBackground}>{generating ? <><span className="analytics-spinner" />Generating art layer…</> : <><Sparkles size={17} />Generate visual background<ArrowRight size={17} /></>}</button>
              {error && <p className="analytics-error">{error}</p>}
            </section>
          </aside>

          <section className="analytics-preview-column">
            <div className="analytics-preview-head"><div><p>Live composition preview</p><h2>{selectedTemplate.name}</h2></div><span>{format}</span></div>
            <ChartPreview token={token} compare={compare} compareEnabled={compareEnabled} period={period} metric={metric} template={template} generatedBackground={generatedBackground} />
            <div className="analytics-layer-note"><ImageIcon size={17} /><span><strong>Hybrid image composition</strong>The image model cannot change the chart, prices, dates, percentages, logos, or source attribution.</span></div>
          </section>
        </div>
      </main>
      <ChatWidget />
    </div>
  )
}
