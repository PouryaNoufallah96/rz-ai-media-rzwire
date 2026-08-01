import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowRight, CalendarDays, Check, CircleCheck, Database, ImageIcon, LineChart, Plus, RefreshCw, Search, Sparkles, X } from 'lucide-react'
import NavBar from '../components/NavBar'
import ChatWidget from '../components/chat/ChatWidget'
import { API_BASE, IMAGE_MODEL_OPTIONS } from '../store/mmStore'
import mgcLogo from '../assets/brands/mgc-coin-logo.png'
import oasisLogo from '../assets/brands/oasis-coin-logo.png'
import jewelryLogo from '../assets/brands/jewelry-coin-logo.png'
import phoneTemplate from '../assets/analytics-templates/phone-comparison.png'
import desktopTemplate from '../assets/analytics-templates/desktop-dashboard.png'
import growthTemplate from '../assets/analytics-templates/growth-spotlight.png'
import winnerLoserTemplate from '../assets/analytics-templates/winner-loser.png'
import './AnalyticsPage.css'

const TOKENS = [
  { id:'mgc', name:'MGC Coin', symbol:'MGC', brand:'MGC Coin', logo:mgcLogo, color:'#d9b91d' },
  { id:'oasis', name:'Oasis Coin', symbol:'OASIS', brand:'Oasis Coin', logo:oasisLogo, color:'#739e90' },
  { id:'jewelry', name:'Jewelry Coin', symbol:'JEWELRY', brand:'Jewelry Coin', logo:jewelryLogo, color:'#8f82e8' },
]

const POPULAR_COMPARISONS = [
  { id:'binance:BTC', type:'binance', symbol:'BTC', name:'Bitcoin', source:'Binance Public Spot API' },
  { id:'binance:ETH', type:'binance', symbol:'ETH', name:'Ethereum', source:'Binance Public Spot API' },
  { id:'binance:XRP', type:'binance', symbol:'XRP', name:'XRP', source:'Binance Public Spot API' },
  { id:'binance:BNB', type:'binance', symbol:'BNB', name:'BNB', source:'Binance Public Spot API' },
]

const PERIODS = ['24h', '7d', '30d', '90d', '1y']
const EXTERNAL_COLORS = ['#c9877f', '#3978c7', '#b878cf']
const TEMPLATES = [
  { id:'phone', name:'Phone comparison', description:'Two verified series inside a mobile market view.', image:phoneTemplate, min:2, max:2 },
  { id:'laptop', name:'Desktop dashboard', description:'One to six verified series inside a premium laptop frame.', image:desktopTemplate, min:1, max:6 },
  { id:'growth', name:'Growth spotlight', description:'One token with its exact start, end, and movement.', image:growthTemplate, min:1, max:1 },
  { id:'winner', name:'Winner vs loser', description:'A high-contrast comparison for exactly two tokens.', image:winnerLoserTemplate, min:2, max:2 },
]

function formatPrice(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 'Unavailable'
  const digits = amount < 1 ? 6 : amount < 100 ? 4 : 2
  return amount.toLocaleString('en-US', {style:'currency', currency:'USD', maximumFractionDigits:digits})
}

function formatDate(timestamp) {
  if (!Number.isFinite(Number(timestamp))) return 'Unavailable'
  return new Date(Number(timestamp) * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric', year:'numeric'})
}

function percentValues(points) {
  if (!points?.length) return []
  const start = Number(points[0].close) || 1
  return points.map(point => ((Number(point.close) - start) / start) * 100)
}

function chartValues(series, scale) {
  return scale === 'absolute' ? series.points.map(point => Number(point.close)) : percentValues(series.points)
}

function assetToDataUrl(url) {
  return fetch(url).then(response => {
    if (!response.ok) throw new Error('The selected reference image could not be loaded.')
    return response.blob()
  }).then(blob => new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('The selected reference image could not be prepared.'))
    reader.readAsDataURL(blob)
  }))
}

function chartToPngDataUrl(svgElement) {
  if (!svgElement) return Promise.reject(new Error('The approved chart is not available for composition.'))
  const clone = svgElement.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  style.textContent = `text{font-family:Inter,Arial,sans-serif}.analytics-chart-grid-line{stroke:#dcd9d2;stroke-width:1}.analytics-axis-text{fill:#626870;font-size:12px}.analytics-axis-text--left{text-anchor:end}.analytics-axis-text--date{text-anchor:middle}.analytics-chart-zero{stroke:#969a9f;stroke-width:1;stroke-dasharray:5 4}.analytics-series{fill:none;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}`
  clone.prepend(style)
  const source = new XMLSerializer().serializeToString(clone)
  const blobUrl = URL.createObjectURL(new Blob([source], {type:'image/svg+xml;charset=utf-8'}))
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 1800
      canvas.height = 820
      const context = canvas.getContext('2d')
      context.fillStyle = '#fbfaf7'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.drawImage(image, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(blobUrl)
      resolve(canvas.toDataURL('image/png'))
    }
    image.onerror = () => {
      URL.revokeObjectURL(blobUrl)
      reject(new Error('The approved chart could not be prepared for image generation.'))
    }
    image.src = blobUrl
  })
}

function colorisedSeries(data) {
  let comparisonIndex = 0
  return (data?.series || []).map(item => {
    const primary = TOKENS.find(token => token.symbol === item.symbol)
    const color = primary?.color || EXTERNAL_COLORS[comparisonIndex++ % EXTERNAL_COLORS.length]
    return {...item, color}
  })
}

function VerifiedChart({ data, chartRef }) {
  const series = colorisedSeries(data)
  const scale = data.scale || 'relative'
  const valueSets = series.map(item => chartValues(item, scale))
  const allValues = valueSets.flat().filter(Number.isFinite)
  if (scale === 'relative') allValues.push(0)
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const padding = Math.max(scale === 'relative' ? 1 : Math.abs(rawMax || 1) * .02, (rawMax - rawMin) * .1)
  const min = rawMin - padding
  const max = rawMax + padding
  const chart = {left:132, right:790, top:34, bottom:330}
  const timestamps = series.flatMap(item => item.points.map(point => Number(point.timestamp))).filter(Number.isFinite)
  const firstTimestamp = Math.min(...timestamps)
  const lastTimestamp = Math.max(...timestamps)
  const xFor = timestamp => chart.left + ((Number(timestamp) - firstTimestamp) / Math.max(1, lastTimestamp - firstTimestamp)) * (chart.right - chart.left)
  const yFor = value => chart.bottom - ((value - min) / Math.max(.000001, max - min)) * (chart.bottom - chart.top)
  const lineFor = (item, values) => item.points.map((point, index) => `${xFor(point.timestamp).toFixed(1)},${yFor(values[index]).toFixed(1)}`).join(' ')
  const yTicks = Array.from({length:6}, (_, index) => max - index * ((max - min) / 5))
  const dateTicks = Array.from({length:6}, (_, index) => firstTimestamp + index * ((lastTimestamp - firstTimestamp) / 5))

  return <div className="analytics-verified-chart">
    <div className="analytics-proof-title"><div><strong>{series.map(item => item.symbol).join(' / ')}</strong><span>{data.period} verified price history</span></div><b>{scale === 'relative' ? 'Relative %' : 'Absolute USD'}</b></div>
    <svg ref={chartRef} className="analytics-proof-svg" viewBox="0 0 900 410" role="img" aria-label={`${series.map(item => item.symbol).join(', ')} complete ${data.period} price chart`}>
      {yTicks.map((tick, index) => {
        const y = yFor(tick)
        const label = scale === 'absolute' ? formatPrice(tick) : `${tick >= 0 ? '+' : ''}${tick.toFixed(1)}%`
        return <g key={`y-${index}`}><line className="analytics-chart-grid-line" x1={chart.left} y1={y} x2={chart.right} y2={y} /><text className="analytics-axis-text analytics-axis-text--left" x={chart.left - 12} y={y + 4}>{label}</text></g>
      })}
      {dateTicks.map((timestamp, index) => <text key={`x-${index}`} className="analytics-axis-text analytics-axis-text--date" x={xFor(timestamp)} y="382">{new Date(timestamp * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric'})}</text>)}
      {scale === 'relative' && min <= 0 && max >= 0 && <line className="analytics-chart-zero" x1={chart.left} y1={yFor(0)} x2={chart.right} y2={yFor(0)} />}
      {series.map((item, index) => <polyline key={item.id} className="analytics-series analytics-series--verified" style={{stroke:item.color}} points={lineFor(item, valueSets[index])} />)}
    </svg>
    <div className="analytics-chart-legend analytics-chart-legend--multi">{series.map(item => <span key={item.id}><i style={{background:item.color}} />{item.symbol} <b>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</b></span>)}</div>
    <div className="analytics-series-status-grid">{series.map(item => <article key={item.id}><div><i style={{background:item.color}} /><strong>{item.symbol}</strong><span>{item.role === 'primary' ? 'RZWire' : item.type === 'dex' ? 'DEX' : 'Binance'}</span></div><dl><dt>Start</dt><dd>{formatPrice(item.startPrice)}</dd><dt>End</dt><dd>{formatPrice(item.endPrice)}</dd><dt>Coverage</dt><dd>{formatDate(item.coverageStart)} - {formatDate(item.coverageEnd)}</dd></dl></article>)}</div>
    {!!data.warnings?.length && <div className="analytics-warning-list">{data.warnings.map(warning => <p key={warning}><AlertTriangle size={14} />{warning}</p>)}</div>}
    <div className="analytics-source-list"><strong>Verified sources</strong>{series.map(item => <a key={item.id} href={item.source?.attributionUrl} target="_blank" rel="noreferrer">{item.symbol} - {item.source?.provider}</a>)}</div>
  </div>
}

function ChartPreview({ marketData, period, template, headline, chartText, primaryToken }) {
  const series = colorisedSeries(marketData)
  const values = series.map(item => marketData.scale === 'absolute' ? chartValues(item, 'absolute') : percentValues(item.points))
  const flat = values.flat().filter(Number.isFinite)
  const min = Math.min(...flat)
  const max = Math.max(...flat)
  const pointString = (item, itemValues) => itemValues.map((value, index) => {
    const x = 18 + index * (584 / Math.max(1, itemValues.length - 1))
    const y = 202 - ((value - min) / Math.max(.000001, max - min)) * 164
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
  return <div className={`analytics-poster analytics-poster--${template}`}>
    <div className="analytics-poster-topline"><span>Verified market data</span><span>{series.length} exact series</span></div>
    <header><div><p>{period} market view</p><h2>{headline}</h2></div><img src={primaryToken.logo} alt={`${primaryToken.name} logo`} /></header>
    <div className={`analytics-chart-device analytics-chart-device--${template}`}>
      <div className="analytics-device-bar"><span /><span /><span /></div>
      <div className="analytics-chart-heading analytics-chart-heading--multi">{series.map(item => <span key={item.id}><i style={{background:item.color}} />{item.symbol}</span>)}</div>
      <div className="analytics-range-tabs"><span>1h</span><span>24h</span><span>7d</span><span className="selected">{period}</span><span>90d</span><span>1y</span></div>
      <svg viewBox="0 0 620 220" role="img" aria-label="Approved multi-token chart preview"><path className="analytics-chart-grid" d="M18 40H602M18 95H602M18 150H602M18 202H602" />{series.map((item, index) => <polyline key={item.id} className="analytics-series" style={{stroke:item.color}} points={pointString(item, values[index])} />)}</svg>
      <div className="analytics-chart-legend analytics-chart-legend--multi">{series.map(item => <span key={item.id}><i style={{background:item.color}} />{item.symbol} {item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</span>)}</div>
    </div>
    <div className="analytics-poster-result">{chartText}</div>
    <footer><span>RZWire Market Analytics</span><span>Verified public market feeds</span></footer>
  </div>
}

export default function AnalyticsPage() {
  const chartSvgRef = useRef(null)
  const [primaryIds, setPrimaryIds] = useState(['mgc'])
  const [comparisonAssets, setComparisonAssets] = useState([POPULAR_COMPARISONS[2]])
  const [assetQuery, setAssetQuery] = useState('')
  const [assetResults, setAssetResults] = useState(POPULAR_COMPARISONS)
  const [searchingAssets, setSearchingAssets] = useState(false)
  const [selectionError, setSelectionError] = useState('')
  const [customNetwork, setCustomNetwork] = useState('bsc')
  const [customContract, setCustomContract] = useState('')
  const [resolvingCustom, setResolvingCustom] = useState(false)
  const [period, setPeriod] = useState('30d')
  const [scale, setScale] = useState('relative')
  const [format, setFormat] = useState('Portrait · 1080 × 1350')
  const [template, setTemplate] = useState('laptop')
  const [imageModel, setImageModel] = useState('openai/gpt-5.4-image-2')
  const [direction, setDirection] = useState('Premium financial editorial composition with restrained lighting, a centered laptop, generous spacing, and a clearly readable chart screen.')
  const [generatedBackground, setGeneratedBackground] = useState('')
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [marketData, setMarketData] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState('')
  const [chartApproved, setChartApproved] = useState(false)
  const [headline, setHeadline] = useState('30-day market comparison')
  const [chartText, setChartText] = useState('Verified movement, presented with exact market data.')

  const selectedPrimary = TOKENS.filter(token => primaryIds.includes(token.id))
  const allSelectedSymbols = [...selectedPrimary.map(token => token.symbol), ...comparisonAssets.map(asset => asset.symbol)]
  const seriesCount = allSelectedSymbols.length
  const primaryToken = selectedPrimary[0] || TOKENS[0]
  const selectedTemplate = TEMPLATES.find(item => item.id === template) || TEMPLATES[1]
  const summary = `${allSelectedSymbols.join(' versus ')}, ${period}, ${scale === 'relative' ? 'relative performance' : 'absolute USD price'}`
  const visibleAssetResults = assetQuery.trim() ? assetResults : POPULAR_COMPARISONS

  useEffect(() => {
    const query = assetQuery.trim()
    if (!query) return undefined
    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setSearchingAssets(true)
      try {
        const response = await fetch(`${API_BASE}/api/market/assets?query=${encodeURIComponent(query)}&limit=30`, {credentials:'include', signal:controller.signal})
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.error || 'Token search failed.')
        setAssetResults(data.assets || [])
      } catch (err) {
        if (err.name !== 'AbortError') setSelectionError(err.message || 'Token search failed.')
      } finally {
        setSearchingAssets(false)
      }
    }, 250)
    return () => { clearTimeout(timer); controller.abort() }
  }, [assetQuery])

  function invalidateMarketData() {
    setMarketData(null)
    setChartApproved(false)
    setVerificationError('')
    setGeneratedBackground('')
    setError('')
  }

  function togglePrimary(id) {
    setSelectionError('')
    const selected = primaryIds.includes(id)
    const token = TOKENS.find(item => item.id === id)
    if (selected && primaryIds.length === 1) {
      setSelectionError('At least one RZWire token must remain selected.')
      return
    }
    if (!selected && comparisonAssets.some(item => item.symbol === token?.symbol)) {
      setSelectionError(`${token.symbol} is already selected as a comparison asset.`)
      return
    }
    setPrimaryIds(selected ? primaryIds.filter(item => item !== id) : [...primaryIds, id])
    setTemplate('laptop')
    invalidateMarketData()
  }

  function addComparison(asset) {
    setSelectionError('')
    if (comparisonAssets.some(item => item.id === asset.id) || selectedPrimary.some(item => item.symbol === asset.symbol)) {
      setSelectionError(`${asset.symbol} is already selected.`)
      return
    }
    if (comparisonAssets.length >= 3 || seriesCount >= 6) {
      setSelectionError('You can select up to three comparison coins and six total chart lines.')
      return
    }
    setComparisonAssets([...comparisonAssets, asset])
    setAssetQuery('')
    setTemplate('laptop')
    invalidateMarketData()
  }

  function removeComparison(id) {
    setComparisonAssets(comparisonAssets.filter(item => item.id !== id))
    setTemplate('laptop')
    invalidateMarketData()
  }

  async function resolveCustomAsset() {
    if (!customNetwork.trim() || !customContract.trim() || resolvingCustom) return
    setResolvingCustom(true)
    setSelectionError('')
    try {
      const response = await fetch(`${API_BASE}/api/market/assets/resolve`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({network:customNetwork, contract:customContract})})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.asset) throw new Error(data.error || 'The DEX contract could not be verified.')
      addComparison(data.asset)
      setCustomContract('')
    } catch (err) {
      setSelectionError(err.message || 'The DEX contract could not be verified.')
    } finally {
      setResolvingCustom(false)
    }
  }

  async function verifyMarketData() {
    if (verifying) return
    setVerifying(true)
    setVerificationError('')
    setMarketData(null)
    setChartApproved(false)
    setGeneratedBackground('')
    try {
      const response = await fetch(`${API_BASE}/api/market/history/batch`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({primaryTokens:primaryIds, comparisonAssets, period, scale})})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.verified || !data.series?.length) throw new Error(data.error || 'The public market feeds did not return a verified RZWire chart.')
      setMarketData(data)
      const symbols = data.series.map(item => item.symbol)
      setHeadline(symbols.length === 1 ? `${symbols[0]} price movement` : `${symbols.join(' · ')} market comparison`)
      setChartText(data.series.map(item => `${item.symbol} ${item.changePercent >= 0 ? 'rose' : 'fell'} ${Math.abs(item.changePercent).toFixed(2)}%`).join(', ') + '.')
    } catch (err) {
      setVerificationError(err.message || 'Price extraction failed.')
    } finally {
      setVerifying(false)
    }
  }

  async function generatePost() {
    if (generating) return
    if (!marketData?.verified || !chartApproved) {
      setError('Approve the verified chart and axes before generating the finished post.')
      return
    }
    if (seriesCount < selectedTemplate.min || seriesCount > selectedTemplate.max) {
      setError(`${selectedTemplate.name} supports ${selectedTemplate.min === selectedTemplate.max ? `exactly ${selectedTemplate.min}` : `${selectedTemplate.min}-${selectedTemplate.max}`} chart series.`)
      return
    }
    setGenerating(true)
    setError('')
    setGeneratedBackground('')
    try {
      const [referenceImage, approvedChart] = await Promise.all([assetToDataUrl(selectedTemplate.image), chartToPngDataUrl(chartSvgRef.current)])
      const movement = marketData.series.reduce((total, item) => total + item.changePercent, 0) / marketData.series.length
      const response = await fetch(`${API_BASE}/api/image/generate`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
        article:{title:headline || summary}, platform:'Instagram', mediaBrand:primaryToken.brand, sentiment:movement >= 0 ? 'Bullish' : 'Bearish', model:imageModel, compositionMode:'analytics_post', copy:chartText, referenceImages:[referenceImage, approvedChart],
        imageDirection:`Create one finished ${format} financial social post. REFERENCE IMAGE 1 is the exact visual composition and device style to follow. REFERENCE IMAGE 2 is the approved factual multi-token chart containing ${marketData.series.map(item => item.symbol).join(', ')}. Place REFERENCE IMAGE 2 clearly and completely inside the device screen from REFERENCE IMAGE 1. Keep every chart line, color, date, axis, price, percentage, ticker, legend, and relative position from REFERENCE IMAGE 2 unchanged and readable. Use this exact header: "${headline}". Use this supporting text: "${chartText}". RZWire brands represented: ${selectedPrimary.map(item => item.brand).join(', ')}. ${direction} Do not add invented prices, percentages, dates, logos, charts, watermarks, UI panels, or unrelated copy.`,
      })})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.imageB64) throw new Error(data.error || 'The image model did not return a finished post.')
      setGeneratedBackground(data.imageB64)
    } catch (err) {
      setError(err.message || 'Post generation failed.')
    } finally {
      setGenerating(false)
    }
  }

  return <div className="analytics-page">
    <NavBar />
    <main className="analytics-workspace">
      <section className="analytics-intro"><div><p className="analytics-eyebrow"><LineChart size={16} /> Market Analytics</p><h1>Compare the complete RZWire market.</h1><p>Select up to three RZWire tokens and three outside assets, approve one exact chart, then turn it into a branded visual story.</p></div><div className="analytics-steps" aria-label="Analytics post workflow"><span className="active"><b>1</b>Market</span><i /><span><b>2</b>Chart</span><i /><span><b>3</b>Copy</span><i /><span><b>4</b>Style</span><i /><span><b>5</b>Generate</span></div></section>
      <div className="analytics-layout analytics-layout--storyboard">
        <aside className="analytics-controls">
          <section className="analytics-control-section analytics-setup-section">
            <div className="analytics-section-heading"><span>01A</span><div><h2>Select RZWire tokens</h2><p>Choose one, two, or all three primary brand tokens.</p></div></div>
            <div className="analytics-token-grid">{TOKENS.map(item => <button key={item.id} type="button" className={primaryIds.includes(item.id) ? 'selected' : ''} onClick={() => togglePrimary(item.id)}><img src={item.logo} alt="" /><span><strong>{item.symbol}</strong><small>{item.name}</small></span>{primaryIds.includes(item.id) && <Check size={15} />}</button>)}</div>
            <div className="analytics-selected-summary"><strong>{seriesCount}/6 chart lines</strong><div>{selectedPrimary.map(item => <span key={item.id}><i style={{background:item.color}} />{item.symbol}</span>)}{comparisonAssets.map((item, index) => <span key={item.id}><i style={{background:EXTERNAL_COLORS[index % EXTERNAL_COLORS.length]}} />{item.symbol}<button type="button" onClick={() => removeComparison(item.id)} aria-label={`Remove ${item.symbol}`}><X size={12} /></button></span>)}</div></div>
          </section>
          <section className="analytics-control-section analytics-market-section">
            <div className="analytics-section-heading"><span>01B</span><div><h2>Add comparison coins</h2><p>Search active Binance USDT markets or verify a DEX contract.</p></div></div>
            <label className="analytics-search-field">Search Binance assets<div><Search size={15} /><input value={assetQuery} onChange={event => { setAssetQuery(event.target.value); setSelectionError('') }} placeholder="Search BTC, SOL, DOGE…" />{searchingAssets && <span className="analytics-small-spinner" />}</div></label>
            <div className="analytics-asset-results">{visibleAssetResults.slice(0, 12).map(asset => { const selected = comparisonAssets.some(item => item.id === asset.id); return <button key={asset.id} type="button" disabled={selected} onClick={() => addComparison(asset)}><span><strong>{asset.symbol}</strong><small>{asset.name}</small></span>{selected ? <Check size={14} /> : <Plus size={14} />}</button> })}</div>
            <details className="analytics-custom-dex"><summary><Database size={15} />Add an unlisted DEX token</summary><div className="analytics-custom-dex-fields"><label>GeckoTerminal network<input value={customNetwork} onChange={event => setCustomNetwork(event.target.value)} placeholder="bsc" /></label><label>Token contract<input value={customContract} onChange={event => setCustomContract(event.target.value)} placeholder="0x…" /></label><button type="button" disabled={resolvingCustom || !customContract.trim()} onClick={resolveCustomAsset}>{resolvingCustom ? 'Verifying…' : 'Verify and add token'}</button></div></details>
            {selectionError && <p className="analytics-error">{selectionError}</p>}
            <div className="analytics-field-label"><CalendarDays size={15} />Period</div><div className="analytics-periods">{PERIODS.map(item => <button key={item} type="button" className={period === item ? 'selected' : ''} onClick={() => { setPeriod(item); invalidateMarketData() }}>{item}</button>)}</div>
            <div className="analytics-two-fields"><label>Chart scale<select value={scale} onChange={event => { setScale(event.target.value); invalidateMarketData() }}><option value="relative">Relative performance (%)</option><option value="absolute">Absolute price (USD)</option></select></label><label>Output format<select value={format} onChange={event => setFormat(event.target.value)}><option>Portrait · 1080 × 1350</option><option>Square · 1080 × 1080</option><option>Story · 1080 × 1920</option><option>Landscape · 1600 × 900</option></select></label></div>
            <div className="analytics-data-note"><span>Live check</span>RZWire and custom contracts use verified GeckoTerminal pools. Search comparisons use Binance public spot history.</div>
          </section>
          <section className="analytics-control-section analytics-verification-controls">
            <div className="analytics-section-heading"><span>02</span><div><h2>Approve the complete white chart</h2><p>Inspect every selected series, date, scale, price, movement, and source before choosing a publishing design.</p></div></div>
            <button type="button" className="analytics-verify" disabled={verifying || !primaryIds.length} onClick={verifyMarketData}>{verifying ? <><span className="analytics-spinner" />Extracting {seriesCount} price histories…</> : <><RefreshCw size={16} />Fetch and verify {seriesCount} chart {seriesCount === 1 ? 'line' : 'lines'}</>}</button>
            {verificationError && <p className="analytics-error">{verificationError}</p>}
            {!marketData && !verifying && <div className="analytics-proof-empty"><LineChart size={28} /><strong>Your complete verified chart will appear here</strong><span>RZWire will fetch every selected history concurrently and keep available lines if another provider fails.</span></div>}
            {marketData && <><VerifiedChart data={marketData} chartRef={chartSvgRef} />{!!marketData.failures?.length && <div className="analytics-failure-summary"><AlertTriangle size={16} /><span><strong>{marketData.failures.length} selected {marketData.failures.length === 1 ? 'asset was' : 'assets were'} unavailable.</strong>{marketData.failures.map(item => <small key={item.id}>{item.symbol} - unavailable from {item.type === 'binance' ? 'Binance' : 'GeckoTerminal'}: {item.error}</small>)}<small>The verified lines above can still be approved.</small></span></div>}<div className="analytics-chart-approval"><div><strong>{chartApproved ? 'Chart approved' : 'Check every line and label before continuing'}</strong><span>{chartApproved ? 'Copy, compatible examples, and image generation are unlocked.' : 'Confirm the prices, axes, dates, warnings, and source attribution.'}</span></div><button type="button" className={chartApproved ? 'approved' : ''} onClick={() => setChartApproved(true)}>{chartApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve complete chart</>}</button></div></>}
          </section>
          {chartApproved && <section className="analytics-control-section analytics-copy-section"><div className="analytics-section-heading"><span>03</span><div><h2>Write the story</h2><p>Add the header and statement that accompany every verified series.</p></div></div><label>Header<input value={headline} onChange={event => setHeadline(event.target.value)} /></label><label>Chart text<textarea rows="4" value={chartText} onChange={event => setChartText(event.target.value)} /></label></section>}
          {chartApproved && <section className="analytics-control-section analytics-template-section"><div className="analytics-section-heading"><span>04</span><div><h2>Choose how to publish it</h2><p>Only references compatible with {marketData.series.length} verified chart lines can be selected.</p></div></div><div className="analytics-template-grid analytics-template-grid--exact">{TEMPLATES.map(item => { const compatible = marketData.series.length >= item.min && marketData.series.length <= item.max; return <button key={item.id} type="button" disabled={!compatible} className={template === item.id ? 'selected' : ''} onClick={() => setTemplate(item.id)}><img src={item.image} alt={`${item.name} publishing example`} /><span><strong>{item.name}</strong><small>{compatible ? item.description : `Requires ${item.min === item.max ? `${item.min} lines` : `${item.min}-${item.max} lines`}`}</small></span>{template === item.id && compatible && <Check size={16} />}</button> })}</div></section>}
          {chartApproved && <section className="analytics-control-section analytics-generation-controls"><div className="analytics-section-heading"><span>05</span><div><h2>Generate the finished post</h2><p>The image model receives the selected reference and the complete approved chart as separate images.</p></div></div><label>Image model<select value={imageModel} onChange={event => setImageModel(event.target.value)}>{IMAGE_MODEL_OPTIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label>Creative direction<textarea rows="3" value={direction} onChange={event => setDirection(event.target.value)} /></label><button type="button" className="analytics-generate" disabled={generating || !marketData || !chartApproved} onClick={generatePost}>{generating ? <><span className="analytics-spinner" />Composing finished post…</> : <><Sparkles size={17} />Generate finished post<ArrowRight size={17} /></>}</button>{error && <p className="analytics-error">{error}</p>}</section>}
        </aside>
        {chartApproved && <section className="analytics-preview-column"><div className="analytics-preview-head"><div><p>Publishing preview</p><h2>{selectedTemplate.name}</h2></div><span>{format}</span></div><div className="analytics-reference-sample"><div><strong>Exact style reference</strong><span>The complete approved chart will replace the sample chart inside this device.</span></div><img src={selectedTemplate.image} alt={`${selectedTemplate.name} exact style reference`} /></div><div className="analytics-live-output-label"><span>{generatedBackground ? 'Generated finished post' : 'RZWire composition preview'}</span><small>The reference and complete approved chart are supplied separately.</small></div>{generatedBackground ? <img className="analytics-generated-post" src={`data:image/png;base64,${generatedBackground}`} alt="Generated RZWire multi-token analytics post" /> : <ChartPreview marketData={marketData} period={period} template={template} headline={headline} chartText={chartText} primaryToken={primaryToken} />}<div className="analytics-layer-note"><ImageIcon size={17} /><span><strong>Locked factual layer</strong>All {marketData.series.length} verified chart lines remain together as one approved image inside the selected reference composition.</span></div></section>}
      </div>
    </main>
    <ChatWidget />
  </div>
}
