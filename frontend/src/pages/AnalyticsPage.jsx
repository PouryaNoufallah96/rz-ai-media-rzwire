import { useMemo, useState } from 'react'
import { ArrowRight, CalendarDays, Check, CircleCheck, Database, ImageIcon, LineChart, RefreshCw, Sparkles } from 'lucide-react'
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

const PERIODS = ['24h', '7d', '30d', '90d', '1y']

const TEMPLATES = [
  { id:'phone', name:'Phone comparison', description:'Two indexed price lines inside a mobile market view.', image:phoneTemplate },
  { id:'laptop', name:'Desktop dashboard', description:'Wide chart presentation inside a premium laptop frame.', image:desktopTemplate },
  { id:'growth', name:'Growth spotlight', description:'One coin, start and end values, and a bold growth claim.', image:growthTemplate },
  { id:'winner', name:'Winner vs loser', description:'A high-contrast comparison that makes the result immediate.', image:winnerLoserTemplate },
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

function percentValues(series) {
  if (!series?.length) return []
  const start = Number(series[0].close) || 1
  return series.map(item => ((Number(item.close) - start) / start) * 100)
}

function domainPoints(values, min, max, width=620, height=220, pad=18) {
  if (!values.length) return ''
  const range = Math.max(.000001, max - min)
  return values.map((value, index) => {
    const x = pad + index * ((width - pad * 2) / Math.max(1, values.length - 1))
    const y = height - pad - ((value - min) / range) * (height - pad * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function formatPrice(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 'Unavailable'
  const digits = amount < 1 ? 6 : amount < 100 ? 4 : 2
  return amount.toLocaleString('en-US', {style:'currency', currency:'USD', maximumFractionDigits:digits})
}

function VerifiedChart({ data, token }) {
  const primary = percentValues(data.primary.points)
  const comparison = data.comparison ? percentValues(data.comparison.points) : []
  const allValues = [...primary, ...comparison, 0]
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const padding = Math.max(1, (rawMax - rawMin) * .12)
  const min = rawMin - padding
  const max = rawMax + padding
  const chart = { left:76, right:654, top:24, bottom:252 }
  const yFor = value => chart.bottom - ((value - min) / Math.max(.000001, max - min)) * (chart.bottom - chart.top)
  const xFor = index => chart.left + index * ((chart.right - chart.left) / Math.max(1, primary.length - 1))
  const lineFor = values => values.map((value, index) => `${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`).join(' ')
  const yTicks = Array.from({length:5}, (_, index) => max - index * ((max - min) / 4))
  const dateIndexes = Array.from(new Set([0, Math.round((primary.length - 1) * .25), Math.round((primary.length - 1) * .5), Math.round((primary.length - 1) * .75), primary.length - 1]))
  const startPrice = Number(data.primary.startPrice) || 0

  return (
    <div className="analytics-verified-chart">
      <div className="analytics-verified-status">
        <span><CircleCheck size={16} />Live extraction verified</span>
        <time>{new Date(data.fetchedAt).toLocaleString()}</time>
      </div>
      <div className="analytics-verified-summary">
        <div><small>{data.primary.symbol} start</small><strong>{formatPrice(data.primary.startPrice)}</strong></div>
        <div><small>{data.primary.symbol} latest</small><strong>{formatPrice(data.primary.endPrice)}</strong></div>
        <div><small>Period change</small><strong className={data.primary.changePercent >= 0 ? 'positive' : 'negative'}>{data.primary.changePercent >= 0 ? '+' : ''}{data.primary.changePercent.toFixed(2)}%</strong></div>
      </div>
      <div className="analytics-axis-title"><span>{data.primary.symbol} price (USD)</span><span>Indexed change</span></div>
      <svg viewBox="0 0 720 292" role="img" aria-label={`Verified ${data.primary.symbol} price chart with USD and percentage axes`}>
        {yTicks.map((tick, index) => {
          const y = yFor(tick)
          const tickPrice = startPrice * (1 + tick / 100)
          return <g key={`y-${index}`}>
            <line className="analytics-chart-grid-line" x1={chart.left} y1={y} x2={chart.right} y2={y} />
            <text className="analytics-axis-text analytics-axis-text--left" x={chart.left - 10} y={y + 4}>{formatPrice(tickPrice)}</text>
            <text className="analytics-axis-text" x={chart.right + 10} y={y + 4}>{tick >= 0 ? '+' : ''}{tick.toFixed(1)}%</text>
          </g>
        })}
        {dateIndexes.map(index => {
          const x = xFor(index)
          const label = new Date(data.primary.points[index].timestamp * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric'})
          return <text key={`x-${index}`} className="analytics-axis-text analytics-axis-text--date" x={x} y="281">{label}</text>
        })}
        <line className="analytics-chart-zero" x1={chart.left} y1={yFor(0)} x2={chart.right} y2={yFor(0)} />
        <polyline className="analytics-series analytics-series--verified" style={{stroke:token.color}} points={lineFor(primary)} />
        {comparison.length > 0 && <polyline className="analytics-series analytics-series--compare" points={lineFor(comparison)} />}
      </svg>
      <div className="analytics-chart-legend">
        <span><i style={{background:token.color}} />{data.primary.symbol}</span>
        {data.comparison && <span><i className="compare-dot" />{data.comparison.symbol}</span>}
      </div>
      <div className="analytics-source-list">
        {data.sources.map(source => <a key={`${source.provider}-${source.poolAddress || source.pair}`} href={source.attributionUrl} target="_blank" rel="noreferrer"><Database size={13} /><span><strong>{source.provider}</strong><small>{source.poolName || source.pair}</small></span></a>)}
      </div>
    </div>
  )
}

function ChartPreview({ token, compare, compareEnabled, period, metric, template, generatedBackground, marketData, headline, chartText }) {
  const livePrimary = marketData ? percentValues(marketData.primary.points) : null
  const liveComparison = marketData?.comparison ? percentValues(marketData.comparison.points) : null
  const primaryPoints = livePrimary ? points(livePrimary) : points(SERIES[token.id])
  const comparisonPoints = liveComparison ? points(liveComparison) : points(SERIES.compare)
  const primaryChange = marketData?.primary.changePercent ?? token.change
  const comparisonChange = marketData?.comparison?.changePercent ?? compare.change
  const startPrice = marketData?.primary.startPrice ?? token.start
  const endPrice = marketData?.primary.endPrice ?? token.end
  const title = compareEnabled ? `${token.symbol} vs ${compare.symbol}` : `${token.symbol} price journey`
  const result = compareEnabled
    ? `${token.symbol} ${primaryChange >= 0 ? 'rose' : 'fell'} ${Math.abs(primaryChange).toFixed(2)}% while ${compare.symbol} ${comparisonChange >= 0 ? 'rose' : 'fell'} ${Math.abs(comparisonChange).toFixed(2)}%`
    : `${token.symbol} moved from ${formatPrice(startPrice)} to ${formatPrice(endPrice)}`

  return (
    <div className={`analytics-poster analytics-poster--${template}`} style={generatedBackground ? {backgroundImage:`linear-gradient(rgba(17,22,31,.68),rgba(17,22,31,.86)),url(data:image/png;base64,${generatedBackground})`} : undefined}>
      <div className="analytics-poster-topline"><span>{marketData ? 'Verified market data' : 'Sample preview'}</span><span>{marketData ? marketData.sources[0]?.provider : 'Live market feed pending'}</span></div>
      <header>
        <div>
          <p>{period === '30d' ? '1 month' : period} {compareEnabled ? 'comparison' : 'movement'}</p>
          <h2>{headline || title}</h2>
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
          <span><i style={{background:token.color}} />{token.symbol} {primaryChange >= 0 ? '+' : ''}{primaryChange.toFixed(2)}%</span>
          {compareEnabled && <span><i className="compare-dot" />{compare.symbol} {comparisonChange >= 0 ? '+' : ''}{comparisonChange.toFixed(2)}%</span>}
        </div>
      </div>

      <div className="analytics-poster-result">{chartText || result}</div>
      <footer><span>RZWire Market Analytics</span><span>{marketData ? 'Verified public market feed' : 'Source added after live connection'}</span></footer>
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
  const [marketData, setMarketData] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState('')
  const [chartApproved, setChartApproved] = useState(false)
  const [headline, setHeadline] = useState('30-day market comparison')
  const [chartText, setChartText] = useState('Verified movement, presented with exact market data.')

  const token = TOKENS.find(item => item.id === tokenId) || TOKENS[0]
  const compare = COMPARE_TOKENS.find(item => item.symbol === compareSymbol) || COMPARE_TOKENS[0]
  const selectedTemplate = TEMPLATES.find(item => item.id === template) || TEMPLATES[0]
  const summary = useMemo(() => compareEnabled
    ? `${token.symbol} versus ${compare.symbol}, ${period}, ${metric.toLowerCase()}`
    : `${token.symbol}, ${period}, ${metric.toLowerCase()}`,
  [token, compare, compareEnabled, period, metric])

  function invalidateMarketData() {
    setMarketData(null)
    setChartApproved(false)
    setVerificationError('')
    setGeneratedBackground('')
  }

  async function verifyMarketData() {
    if (verifying) return
    setVerifying(true)
    setVerificationError('')
    setMarketData(null)
    setChartApproved(false)
    setGeneratedBackground('')
    try {
      const params = new URLSearchParams({token:tokenId, period})
      if (compareEnabled) params.set('compare', compareSymbol)
      const response = await fetch(`${API_BASE}/api/market/history?${params.toString()}`, {credentials:'include'})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.verified || !data.primary?.points?.length) {
        throw new Error(data.error || 'The public market feed did not return a verified chart.')
      }
      setMarketData(data)
      const comparisonText = data.comparison
        ? `${data.primary.symbol} ${data.primary.changePercent >= 0 ? 'rose' : 'fell'} ${Math.abs(data.primary.changePercent).toFixed(2)}% while ${data.comparison.symbol} ${data.comparison.changePercent >= 0 ? 'rose' : 'fell'} ${Math.abs(data.comparison.changePercent).toFixed(2)}%.`
        : `${data.primary.symbol} moved from ${formatPrice(data.primary.startPrice)} to ${formatPrice(data.primary.endPrice)}.`
      setHeadline(data.comparison ? `${data.primary.symbol} vs ${data.comparison.symbol}` : `${data.primary.symbol} price movement`)
      setChartText(comparisonText)
    } catch (err) {
      setVerificationError(err.message || 'Price extraction failed.')
    } finally {
      setVerifying(false)
    }
  }

  async function generateBackground() {
    if (generating) return
    if (!marketData?.verified || !chartApproved) {
      setError('Approve the verified chart and axes before generating the image background.')
      return
    }
    setGenerating(true)
    setError('')
    setGeneratedBackground('')
    try {
      const response = await fetch(`${API_BASE}/api/image/generate`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          article:{title:headline || `${summary}. Template: ${selectedTemplate.name}`},
          platform:'Instagram',
          mediaBrand:token.brand,
          sentiment:token.change >= 0 ? 'Bullish' : 'Bearish',
          model:imageModel,
          copy:`${chartText} Verified market view: ${summary}. Selected publishing style: ${selectedTemplate.name}.`,
          imageDirection:`${direction} Use the visual hierarchy of the selected ${selectedTemplate.name} example, but generate background artwork only. Leave generous uncluttered space for the approved chart, token logo, header, dates, and statistics that will be overlaid later by RZWire. Do not render charts, interfaces, devices, logos, letters, numbers, prices, percentages, tickers, watermarks, or captions.`,
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
            <span className="active"><b>1</b>Market</span><i /><span><b>2</b>Chart</span><i /><span><b>3</b>Copy</span><i /><span><b>4</b>Style</span><i /><span><b>5</b>Generate</span>
          </div>
        </section>

        <div className="analytics-layout analytics-layout--storyboard">
          <aside className="analytics-controls">
            <section className="analytics-control-section analytics-setup-section">
              <div className="analytics-section-heading"><span>01A</span><div><h2>Select a token</h2><p>Three RZWire coins are ready for initial setup.</p></div></div>
              <div className="analytics-token-grid">
                {TOKENS.map(item => (
                  <button key={item.id} type="button" className={tokenId === item.id ? 'selected' : ''} onClick={() => { setTokenId(item.id); invalidateMarketData() }}>
                    <img src={item.logo} alt="" /><span><strong>{item.symbol}</strong><small>{item.name}</small></span>{tokenId === item.id && <Check size={15} />}
                  </button>
                ))}
              </div>
            </section>

            <section className="analytics-control-section analytics-market-section">
              <div className="analytics-section-heading"><span>01B</span><div><h2>Define the market view</h2><p>Choose the period, metric, and optional comparison.</p></div></div>
              <label className="analytics-switch"><input type="checkbox" checked={compareEnabled} onChange={event => { setCompareEnabled(event.target.checked); invalidateMarketData() }} /><span />Compare with another coin</label>
              {compareEnabled && <label>Comparison coin<select value={compareSymbol} onChange={event => { setCompareSymbol(event.target.value); invalidateMarketData() }}>{COMPARE_TOKENS.map(item => <option key={item.symbol} value={item.symbol}>{item.name} · {item.symbol}</option>)}</select></label>}
              <div className="analytics-field-label"><CalendarDays size={15} />Period</div>
              <div className="analytics-periods">{PERIODS.map(item => <button key={item} type="button" className={period === item ? 'selected' : ''} onClick={() => { setPeriod(item); invalidateMarketData() }}>{item}</button>)}</div>
              <div className="analytics-two-fields">
                <label>Metric<select value={metric} onChange={event => { setMetric(event.target.value); invalidateMarketData() }}><option>Price performance</option><option disabled>Market capitalization · coming soon</option><option disabled>Trading volume · coming soon</option><option disabled>OHLC candles · coming soon</option></select></label>
                <label>Output format<select value={format} onChange={event => setFormat(event.target.value)}><option>Portrait · 1080 × 1350</option><option>Square · 1080 × 1080</option><option>Story · 1080 × 1920</option><option>Landscape · 1600 × 900</option></select></label>
              </div>
              <div className="analytics-data-note"><span>Live check</span>The chart step discovers the most liquid verified pool and extracts historical prices from public market APIs.</div>
            </section>

            {chartApproved && <section className="analytics-control-section analytics-copy-section">
              <div className="analytics-section-heading"><span>03</span><div><h2>Write the story</h2><p>Add the header and chart statement that will accompany the approved data.</p></div></div>
              <label>Header<input value={headline} onChange={event => setHeadline(event.target.value)} /></label>
              <label>Chart text<textarea rows="4" value={chartText} onChange={event => setChartText(event.target.value)} /></label>
            </section>}

            {chartApproved && <section className="analytics-control-section analytics-template-section">
              <div className="analytics-section-heading"><span>04</span><div><h2>Choose how to publish it</h2><p>Select one of the approved visual examples. The exact reference image is shown here.</p></div></div>
              <div className="analytics-template-grid analytics-template-grid--exact">
                {TEMPLATES.map(item => (
                  <button key={item.id} type="button" className={template === item.id ? 'selected' : ''} onClick={() => setTemplate(item.id)}>
                    <img src={item.image} alt={`${item.name} publishing example`} />
                    <span><strong>{item.name}</strong><small>{item.description}</small></span>
                    {template === item.id && <Check size={16} />}
                  </button>
                ))}
              </div>
            </section>}

            <section className="analytics-control-section analytics-verification-controls">
              <div className="analytics-section-heading"><span>02</span><div><h2>Approve the white source chart</h2><p>Inspect prices, percentage scale, dates, and both axes before choosing any publishing design.</p></div></div>
              <button type="button" className="analytics-verify" disabled={verifying} onClick={verifyMarketData}>{verifying ? <><span className="analytics-spinner" />Extracting price history…</> : <><RefreshCw size={16} />Fetch and verify chart data</>}</button>
              {verificationError && <p className="analytics-error">{verificationError}</p>}
              {!marketData && !verifying && <div className="analytics-proof-empty"><LineChart size={28} /><strong>Your verified chart will appear here</strong><span>Fetch the public price history to review a clean white chart before continuing.</span></div>}
              {marketData && <>
                <VerifiedChart data={marketData} token={token} />
                <div className="analytics-chart-approval">
                  <div><strong>{chartApproved ? 'Chart approved' : 'Check every label before continuing'}</strong><span>{chartApproved ? 'Copy, publishing examples, and image generation are now unlocked.' : 'Confirm the prices, axes, dates, comparison, and source attribution.'}</span></div>
                  <button type="button" className={chartApproved ? 'approved' : ''} onClick={() => setChartApproved(true)}>{chartApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve chart and axes</>}</button>
                </div>
              </>}
            </section>

            {chartApproved && <section className="analytics-control-section analytics-generation-controls">
              <div className="analytics-section-heading"><span>05</span><div><h2>Generate the art layer</h2><p>The model styles the background around the locked chart, approved header, and chart text.</p></div></div>
              <label>Image model<select value={imageModel} onChange={event => setImageModel(event.target.value)}>{IMAGE_MODEL_OPTIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
              <label>Creative direction<textarea rows="3" value={direction} onChange={event => setDirection(event.target.value)} /></label>
              <button type="button" className="analytics-generate" disabled={generating || !marketData || !chartApproved} onClick={generateBackground}>{generating ? <><span className="analytics-spinner" />Generating art layer…</> : <><Sparkles size={17} />Generate visual background<ArrowRight size={17} /></>}</button>
              {error && <p className="analytics-error">{error}</p>}
            </section>}
          </aside>

          {chartApproved && <section className="analytics-preview-column">
            <div className="analytics-preview-head"><div><p>Publishing preview</p><h2>{selectedTemplate.name}</h2></div><span>{format}</span></div>
            <div className="analytics-reference-sample">
              <div><strong>Exact style reference</strong><span>This is the approved example selected above.</span></div>
              <img src={selectedTemplate.image} alt={`${selectedTemplate.name} exact style reference`} />
            </div>
            <div className="analytics-live-output-label"><span>RZWire composition</span><small>Your approved chart, header, and chart text remain locked.</small></div>
            <ChartPreview token={token} compare={compare} compareEnabled={compareEnabled} period={period} metric={metric} template={template} generatedBackground={generatedBackground} marketData={marketData} headline={headline} chartText={chartText} />
            <div className="analytics-layer-note"><ImageIcon size={17} /><span><strong>Hybrid image composition</strong>The image model cannot change the chart, prices, dates, percentages, logos, or source attribution.</span></div>
          </section>}
        </div>
      </main>
      <ChatWidget />
    </div>
  )
}
