import { useEffect, useRef, useState } from 'react'
import { toPng } from 'html-to-image'
import { AlertTriangle, ArrowRight, CalendarDays, Check, CircleCheck, Database, ImageIcon, LineChart, MessageCircle, Plus, RefreshCw, Search, Send, Sparkles, X } from 'lucide-react'
import NavBar from '../components/NavBar'
import ChatWidget from '../components/chat/ChatWidget'
import { API_BASE, IMAGE_MODEL_OPTIONS } from '../store/mmStore'
import CompositionPreview from '../components/analytics/AnalyticsCompositions'
import { OUTPUT_FORMATS, EXTERNAL_COLORS, analyticsTheme, compositionFingerprint } from '../components/analytics/analyticsCompositionConfig'
import { TEMPLATE_CATEGORIES, TEMPLATE_VARIANTS, findTemplateVariant } from '../components/analytics/analyticsTemplates'
import '../components/analytics/AnalyticsCompositions.css'
import './AnalyticsPage.css'

const POPULAR_COMPARISONS = [
  { id:'binance:BTC', type:'binance', symbol:'BTC', name:'Bitcoin', source:'Binance Public Spot API' },
  { id:'binance:ETH', type:'binance', symbol:'ETH', name:'Ethereum', source:'Binance Public Spot API' },
  { id:'binance:XRP', type:'binance', symbol:'XRP', name:'XRP', source:'Binance Public Spot API' },
  { id:'binance:BNB', type:'binance', symbol:'BNB', name:'BNB', source:'Binance Public Spot API' },
]

const PERIODS = ['24h', '7d', '30d', '90d', '1y']
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

function resizePng(dataUrl, width, height) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const context = canvas.getContext('2d')
      context.drawImage(image, 0, 0, width, height)
      resolve(canvas.toDataURL('image/png'))
    }
    image.onerror = () => reject(new Error('The composition capture could not be resized.'))
    image.src = dataUrl
  })
}

async function imageUrlToDataUrl(url) {
  if (!url) throw new Error('The selected approval sample is unavailable.')
  if (url.startsWith('data:')) return url
  const response = await fetch(url)
  if (!response.ok) throw new Error('The selected approval sample could not be prepared for generation.')
  const blob = await response.blob()
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('The selected approval sample could not be read.'))
    reader.readAsDataURL(blob)
  })
}

async function preloadImage(dataUrl) {
  if (!dataUrl) throw new Error('The generated background is unavailable.')
  const image = new Image()
  image.src = dataUrl
  if (typeof image.decode === 'function') {
    await image.decode()
    return
  }
  await new Promise((resolve, reject) => {
    image.onload = resolve
    image.onerror = () => reject(new Error('The generated background could not be prepared for export.'))
  })
}

function finalImageFingerprint(image, composition) {
  if (!image || !composition) return ''
  return `${composition}:${image.length}:${image.slice(-48)}`
}

async function captureComposition(node, output) {
  if (!node) throw new Error('The approved composition is not ready for capture.')
  const bounds = node.getBoundingClientRect()
  const pixelRatio = Math.min(3, Math.max(1, output.width / Math.max(1, bounds.width)))
  const capture = await toPng(node, {cacheBust:true, pixelRatio, backgroundColor:'#10151c'})
  return resizePng(capture, output.width, output.height)
}

function suggestedCopy(series, period) {
  if (!series?.length) return {headline:'Verified market movement', chartText:''}
  const ranked = [...series].sort((a, b) => Number(b.changePercent) - Number(a.changePercent))
  const best = ranked[0]
  const worst = ranked[ranked.length - 1]
  if (series.length === 1) {
    const direction = best.changePercent >= 0 ? 'gained' : 'fell'
    return {
      headline:`${best.symbol} ${direction} ${Math.abs(best.changePercent).toFixed(2)}%`,
      chartText:`From ${formatPrice(best.startPrice)} to ${formatPrice(best.endPrice)} over ${period}.`,
    }
  }
  if (series.length === 2) {
    return {
      headline:`${series[0].symbol} vs ${series[1].symbol}`,
      chartText:`${best.symbol} led at ${best.changePercent >= 0 ? '+' : ''}${best.changePercent.toFixed(2)}%; ${worst.symbol} finished at ${worst.changePercent >= 0 ? '+' : ''}${worst.changePercent.toFixed(2)}%.`,
    }
  }
  return {
    headline:`${period} market comparison`,
    chartText:`${best.symbol} led the selected assets; ${worst.symbol} had the weakest performance.`,
  }
}

function colorisedSeries(data, tokens) {
  let comparisonIndex = 0
  return (data?.series || []).map(item => {
    const primary = tokens.find(token => token.id === item.tokenId || token.symbol === item.symbol)
    const color = primary?.color || EXTERNAL_COLORS[comparisonIndex++ % EXTERNAL_COLORS.length]
    return {...item, color}
  })
}

function VerifiedChart({ data, chartRef, tokens }) {
  const series = colorisedSeries(data, tokens)
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

export default function AnalyticsPage() {
  const chartSvgRef = useRef(null)
  const frameRefs = useRef({})
  const [tokens, setTokens] = useState([])
  const [brandsLoading, setBrandsLoading] = useState(true)
  const [brandsError, setBrandsError] = useState('')
  const [primaryIds, setPrimaryIds] = useState([])
  const [themeOwnerTokenId, setThemeOwnerTokenId] = useState('')
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
  const [format, setFormat] = useState('portrait')
  const [templateVariantId, setTemplateVariantId] = useState('laptop-cinematic')
  const [imageModel, setImageModel] = useState('openai/gpt-5.4-image-2')
  const [direction, setDirection] = useState('Premium financial editorial composition with refined lighting, elegant hierarchy, generous spacing, a beautiful header, and a dominant readable chart.')
  const [compositionApprovals, setCompositionApprovals] = useState({})
  const [generatedPosts, setGeneratedPosts] = useState({})
  const [finalApprovals, setFinalApprovals] = useState({})
  const [publishDestination, setPublishDestination] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishResult, setPublishResult] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatingTemplateId, setGeneratingTemplateId] = useState('')
  const [error, setError] = useState('')
  const [marketData, setMarketData] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState('')
  const [chartApproved, setChartApproved] = useState(false)
  const [headline, setHeadline] = useState('30-day market comparison')
  const [chartText, setChartText] = useState('Verified movement, presented with exact market data.')

  const selectedPrimary = tokens.filter(token => primaryIds.includes(token.id))
  const allSelectedSymbols = [...selectedPrimary.map(token => token.symbol), ...comparisonAssets.map(asset => asset.symbol)]
  const seriesCount = allSelectedSymbols.length
  const selectedTemplate = findTemplateVariant(templateVariantId) || TEMPLATE_VARIANTS[3]
  const themeOwnerValid = selectedPrimary.some(token => token.id === themeOwnerTokenId)
  const themeOwner = tokens.find(token => token.id === themeOwnerTokenId)
  const brandTheme = themeOwnerValid ? analyticsTheme(themeOwnerTokenId, tokens) : null
  const outputFormat = OUTPUT_FORMATS.find(item => item.id === format) || OUTPUT_FORMATS[0]
  const generatedPost = generatedPosts[selectedTemplate.id] || ''
  const selectedFingerprint = marketData && brandTheme ? compositionFingerprint({templateCategoryId:selectedTemplate.categoryId, templateVariantId:selectedTemplate.id, themeOwnerTokenId, marketData, period, scale, format, headline, chartText, direction}) : ''
  const selectedCompositionApproved = Boolean(selectedFingerprint && compositionApprovals[selectedTemplate.id] === selectedFingerprint)
  const generatedFingerprint = finalImageFingerprint(generatedPost, selectedFingerprint)
  const finalImageApproved = Boolean(generatedFingerprint && finalApprovals[selectedTemplate.id] === generatedFingerprint)
  const summary = `${allSelectedSymbols.join(' versus ')}, ${period}, ${scale === 'relative' ? 'relative performance' : 'absolute USD price'}`
  const visibleAssetResults = assetQuery.trim() ? assetResults : POPULAR_COMPARISONS

  useEffect(() => {
    let active = true
    async function loadBrands() {
      setBrandsLoading(true)
      try {
        const response = await fetch(`${API_BASE}/api/market/brands`, {credentials:'include'})
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.error || 'RZWire brands could not be loaded.')
        const next = (data.brands || []).map(brand => ({...brand, brand:brand.name, logo:brand.logoUrl, color:brand.chartColor}))
        if (!next.length) throw new Error('No approved analytics brands are enabled.')
        if (!active) return
        setTokens(next)
        setPrimaryIds(previous => previous.length ? previous.filter(id => next.some(item => item.id === id)) : [next[0].id])
        setThemeOwnerTokenId(previous => next.some(item => item.id === previous) ? previous : next[0].id)
        setBrandsError('')
      } catch (err) {
        if (active) setBrandsError(err.message || 'RZWire brands could not be loaded.')
      } finally {
        if (active) setBrandsLoading(false)
      }
    }
    loadBrands()
    return () => { active = false }
  }, [])

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
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    setPublishDestination('')
    setPublishResult('')
    setError('')
  }

  function invalidateCompositions() {
    setGeneratedPosts({})
    setFinalApprovals({})
    setPublishDestination('')
    setPublishResult('')
    setError('')
  }

  function togglePrimary(id) {
    setSelectionError('')
    const selected = primaryIds.includes(id)
    const token = tokens.find(item => item.id === id)
    if (selected && primaryIds.length === 1) {
      setSelectionError('At least one RZWire token must remain selected.')
      return
    }
    if (!selected && comparisonAssets.some(item => item.symbol === token?.symbol)) {
      setSelectionError(`${token.symbol} is already selected as a comparison asset.`)
      return
    }
    const next = selected ? primaryIds.filter(item => item !== id) : [...primaryIds, id]
    setPrimaryIds(next)
    if (next.length === 1) setThemeOwnerTokenId(next[0])
    else if (primaryIds.length === 1 || !next.includes(themeOwnerTokenId)) setThemeOwnerTokenId('')
    invalidateMarketData()
  }

  function chooseThemeOwner(id) {
    if (!primaryIds.includes(id)) return
    setThemeOwnerTokenId(id)
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    setPublishDestination('')
    setPublishResult('')
    setError('')
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
    invalidateMarketData()
  }

  function removeComparison(id) {
    setComparisonAssets(comparisonAssets.filter(item => item.id !== id))
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
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    setPublishDestination('')
    setPublishResult('')
    try {
      const response = await fetch(`${API_BASE}/api/market/history/batch`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({primaryTokens:primaryIds, comparisonAssets, period, scale})})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.verified || !data.series?.length) throw new Error(data.error || 'The public market feeds did not return a verified RZWire chart.')
      setMarketData(data)
      const copy = suggestedCopy(data.series, period)
      setHeadline(copy.headline)
      setChartText(copy.chartText)
    } catch (err) {
      setVerificationError(err.message || 'Price extraction failed.')
    } finally {
      setVerifying(false)
    }
  }

  function chooseTemplate(id) {
    setError('')
    if (!themeOwnerValid) {
      setError('Choose which selected RZWire coin owns the post theme first.')
      return
    }
    setTemplateVariantId(id)
    setPublishDestination('')
    setPublishResult('')
  }

  async function generatePost() {
    if (generating) return
    if (!marketData?.verified || !chartApproved) {
      setError('Approve the verified chart and axes before generating the finished post.')
      return
    }
    if (!themeOwnerValid || !brandTheme) {
      setError('Choose one selected RZWire coin to own the post theme.')
      return
    }
    if (seriesCount < selectedTemplate.min || seriesCount > selectedTemplate.max) {
      setError(`${selectedTemplate.name} supports ${selectedTemplate.min}-${selectedTemplate.max} chart series.`)
      return
    }
    if (!selectedCompositionApproved) {
      setError('Approve the selected publishing composition before generating the finished post.')
      return
    }
    setGenerating(true)
    setGeneratingTemplateId(selectedTemplate.id)
    setFinalApprovals(previous => ({...previous, [selectedTemplate.id]:''}))
    setPublishDestination('')
    setPublishResult('')
    setError('')
    const lockedNode = frameRefs.current[selectedTemplate.id]
    try {
      if (!lockedNode) throw new Error('The approved composition is not ready for export yet. Please try again.')
      const approvedChart = await chartToPngDataUrl(chartSvgRef.current)
      const approvalSample = await imageUrlToDataUrl(selectedTemplate.image)
      const movement = marketData.series.reduce((total, item) => total + item.changePercent, 0) / marketData.series.length
      const lockedComposition = await captureComposition(lockedNode, outputFormat)
      const response = await fetch(`${API_BASE}/api/image/generate`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
            article:{title:headline || summary}, platform:'Instagram', mediaBrand:themeOwner.brand, sentiment:movement >= 0 ? 'Bullish' : 'Bearish', model:imageModel, compositionMode:'analytics_background', copy:chartText,
            templateId:selectedTemplate.id,
            templateCategoryId:selectedTemplate.categoryId,
            templateVariantId:selectedTemplate.id,
            themeOwnerTokenId,
            brandTheme:brandTheme.id,
            outputDimensions:{width:outputFormat.width, height:outputFormat.height, ratio:format},
            seriesMetadata:marketData.series.map(item => ({id:item.id, tokenId:item.tokenId, symbol:item.symbol, name:item.name, role:item.role, startPrice:item.startPrice, endPrice:item.endPrice, changePercent:item.changePercent, coverageStart:item.coverageStart, coverageEnd:item.coverageEnd})),
            referenceImages:[approvalSample, lockedComposition, approvedChart],
            imageDirection:`Generate ONLY the full-bleed decorative background atmosphere for this ${selectedTemplate.name} post. REFERENCE 1 supplies the approved mood, lighting, texture, and ${brandTheme.label} palette. REFERENCE 2 is the protected final composition; use it only to understand where calm negative space and contrast are needed. REFERENCE 3 is the factual chart; use it only as placement context. Do not render a phone, laptop, device, chart, graph, financial data, text, typography, token name, logo, footer, UI panel, card, border, or mockup. RZWire will place the already-approved phone, verified chart, headline, logo, and footer over your background after generation. ${direction}`,
          })})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.imageB64) throw new Error(data.error || 'The image model did not return a decorative background.')
      const background = data.imageB64.startsWith('data:') ? data.imageB64 : `data:image/png;base64,${data.imageB64}`
      await preloadImage(background)
      lockedNode.style.setProperty('--generated-background', `url(${JSON.stringify(background)})`)
      lockedNode.classList.add('rz-composition--generated-bg')
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
      const finishedPost = await captureComposition(lockedNode, outputFormat)
      setGeneratedPosts(previous => ({...previous, [selectedTemplate.id]:finishedPost}))
    } catch (err) {
      setError(err.message || 'Post generation failed.')
    } finally {
      lockedNode?.classList.remove('rz-composition--generated-bg')
      lockedNode?.style.removeProperty('--generated-background')
      setGenerating(false)
      setGeneratingTemplateId('')
    }
  }

  async function publishFinalImage() {
    if (publishing || !finalImageApproved || !generatedPost || !publishDestination) return
    setPublishing(true)
    setPublishResult('')
    setError('')
    const copy = [headline, chartText].filter(Boolean).join('\n\n')
    try {
      const isTelegram = publishDestination === 'telegram'
      const response = await fetch(`${API_BASE}${isTelegram ? '/api/telegram/post' : '/api/twitter/post'}`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(isTelegram
          ? {imageB64:generatedPost, headline, copy:chartText, hashtags:[], link:'', mediaBrand:themeOwner.brand}
          : {imageB64:generatedPost, copy, hashtags:[], platform:'X', mediaBrand:themeOwner.brand}),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || (isTelegram ? !data.ok : !data.success)) throw new Error(data.error || `The post could not be published to ${isTelegram ? 'Telegram' : 'X'}.`)
      setPublishResult(`Published successfully to ${isTelegram ? 'Telegram' : 'X'}.`)
    } catch (err) {
      setError(err.message || 'Publishing failed.')
    } finally {
      setPublishing(false)
    }
  }

  return <div className="analytics-page">
    <NavBar />
    <main className="analytics-workspace">
      <section className="analytics-intro"><div><p className="analytics-eyebrow"><LineChart size={16} /> Market Analytics</p><h1>Compare the complete RZWire market.</h1><p>Select up to three RZWire tokens and three outside assets, approve one exact chart, then turn it into a branded visual story.</p></div><div className="analytics-steps" aria-label="Analytics post workflow"><span className="active"><b>1</b>Market</span><i /><span><b>2</b>Chart</span><i /><span><b>3</b>Copy</span><i /><span><b>4</b>Style</span><i /><span><b>5</b>Generate</span></div></section>
      <div className="analytics-layout analytics-layout--storyboard">
        <aside className="analytics-controls">
          <section className="analytics-control-section analytics-setup-section">
            <div className="analytics-section-heading"><span>01A</span><div><h2>Select RZWire tokens</h2><p>Choose up to three enabled brands from the central RZWire coin registry.</p></div></div>
            {brandsLoading && <div className="analytics-proof-empty"><span className="analytics-spinner" /><strong>Loading approved brands…</strong></div>}
            {brandsError && <p className="analytics-error">{brandsError}</p>}
            <div className="analytics-token-grid">{tokens.map(item => <button key={item.id} type="button" className={primaryIds.includes(item.id) ? 'selected' : ''} onClick={() => togglePrimary(item.id)}><img src={item.logo} alt="" /><span><strong>{item.symbol}</strong><small>{item.name}</small></span>{primaryIds.includes(item.id) && <Check size={15} />}</button>)}</div>
            {selectedPrimary.length === 1 && themeOwner && <div className="analytics-theme-owner-note"><img src={themeOwner.logo} alt="" /><span><strong>{themeOwner.name} owns this post</strong><small>Palette, logo, footer, motifs, and Art Director are automatic.</small></span></div>}
            {selectedPrimary.length > 1 && <div className="analytics-theme-owner-picker"><div><strong>Choose the visual owner</strong><span>One selected RZWire coin must own the post theme. Comparison coins cannot own it.</span></div><div>{selectedPrimary.map(item => <button type="button" key={item.id} className={themeOwnerTokenId === item.id ? 'selected' : ''} onClick={() => chooseThemeOwner(item.id)}><img src={item.logo} alt="" /><span>{item.symbol}</span>{themeOwnerTokenId === item.id && <Check size={14} />}</button>)}</div>{!themeOwnerValid && <small>Select a visual owner to unlock publishing designs.</small>}</div>}
            <div className="analytics-selected-summary"><strong>{seriesCount}/6 chart lines</strong><div>{selectedPrimary.map(item => <span key={item.id}><i style={{background:item.color}} />{item.symbol}</span>)}{comparisonAssets.map((item, index) => <span key={item.id}><i style={{background:EXTERNAL_COLORS[index % EXTERNAL_COLORS.length]}} />{item.symbol}<button type="button" onClick={() => removeComparison(item.id)} aria-label={`Remove ${item.symbol}`}><X size={12} /></button></span>)}</div></div>
          </section>
          <section className="analytics-control-section analytics-market-section">
            <div className="analytics-section-heading"><span>01B</span><div><h2>Add comparison coins</h2><p>Search active Binance USDT markets or verify a DEX contract.</p></div></div>
            <label className="analytics-search-field">Search Binance assets<div><Search size={15} /><input value={assetQuery} onChange={event => { setAssetQuery(event.target.value); setSelectionError('') }} placeholder="Search BTC, SOL, DOGE…" />{searchingAssets && <span className="analytics-small-spinner" />}</div></label>
            <div className="analytics-asset-results">{visibleAssetResults.slice(0, 12).map(asset => { const selected = comparisonAssets.some(item => item.id === asset.id); return <button key={asset.id} type="button" disabled={selected} onClick={() => addComparison(asset)}><span><strong>{asset.symbol}</strong><small>{asset.name}</small></span>{selected ? <Check size={14} /> : <Plus size={14} />}</button> })}</div>
            <details className="analytics-custom-dex"><summary><Database size={15} />Add an unlisted DEX token</summary><div className="analytics-custom-dex-fields"><label>GeckoTerminal network<input value={customNetwork} onChange={event => setCustomNetwork(event.target.value)} placeholder="bsc" /></label><label>Token contract<input value={customContract} onChange={event => setCustomContract(event.target.value)} placeholder="0x…" /></label><button type="button" disabled={resolvingCustom || !customContract.trim()} onClick={resolveCustomAsset}>{resolvingCustom ? 'Verifying…' : 'Verify and add token'}</button></div></details>
            {selectionError && <p className="analytics-error">{selectionError}</p>}
            <div className="analytics-field-label"><CalendarDays size={15} />Period</div><div className="analytics-periods">{PERIODS.map(item => <button key={item} type="button" className={period === item ? 'selected' : ''} onClick={() => { setPeriod(item); invalidateMarketData() }}>{item}</button>)}</div>
            <div className="analytics-two-fields"><label>Chart scale<select value={scale} onChange={event => { setScale(event.target.value); invalidateMarketData() }}><option value="relative">Relative performance (%)</option><option value="absolute">Absolute price (USD)</option></select></label><label>Output format<select value={format} onChange={event => { setFormat(event.target.value); invalidateCompositions() }}>{OUTPUT_FORMATS.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label></div>
            <div className="analytics-data-note"><span>Live check</span>RZWire and custom contracts use verified GeckoTerminal pools. Search comparisons use Binance public spot history.</div>
          </section>
          <section className="analytics-control-section analytics-verification-controls">
            <div className="analytics-section-heading"><span>02</span><div><h2>Approve the complete white chart</h2><p>Inspect every selected series, date, scale, price, movement, and source before choosing a publishing design.</p></div></div>
            <button type="button" className="analytics-verify" disabled={verifying || !primaryIds.length} onClick={verifyMarketData}>{verifying ? <><span className="analytics-spinner" />Extracting {seriesCount} price histories…</> : <><RefreshCw size={16} />Fetch and verify {seriesCount} chart {seriesCount === 1 ? 'line' : 'lines'}</>}</button>
            {verificationError && <p className="analytics-error">{verificationError}</p>}
            {!marketData && !verifying && <div className="analytics-proof-empty"><LineChart size={28} /><strong>Your complete verified chart will appear here</strong><span>RZWire will fetch every selected history concurrently and keep available lines if another provider fails.</span></div>}
            {marketData && <><VerifiedChart data={marketData} chartRef={chartSvgRef} tokens={tokens} />{!!marketData.failures?.length && <div className="analytics-failure-summary"><AlertTriangle size={16} /><span><strong>{marketData.failures.length} selected {marketData.failures.length === 1 ? 'asset was' : 'assets were'} unavailable.</strong>{marketData.failures.map(item => <small key={item.id}>{item.symbol} — {item.error}</small>)}<small>The verified lines above can still be approved.</small></span></div>}<div className="analytics-chart-approval"><div><strong>{chartApproved ? 'Chart approved' : 'Check every line and label before continuing'}</strong><span>{chartApproved ? 'Story and publishing choices are unlocked.' : 'Confirm the prices, axes, dates, warnings, and source attribution.'}</span></div><button type="button" className={chartApproved ? 'approved' : ''} onClick={() => setChartApproved(true)}>{chartApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve complete chart</>}</button></div></>}
          </section>
          {chartApproved && <section className="analytics-control-section analytics-copy-section"><div className="analytics-section-heading"><span>03</span><div><h2>Write the story</h2><p>Set the beautiful header and supporting statement that guide every static publishing frame.</p></div></div><label>Header<input value={headline} onChange={event => { setHeadline(event.target.value); invalidateCompositions() }} /></label><label>Chart text<textarea rows="4" value={chartText} onChange={event => { setChartText(event.target.value); invalidateCompositions() }} /></label></section>}
          {chartApproved && <section className={`analytics-control-section analytics-template-section ${!themeOwnerValid ? 'is-locked' : ''}`}>
            <div className="analytics-section-heading"><span>04</span><div><h2>Choose how to publish it</h2><p>Choose exactly one permanent concept. Its image becomes the primary visual reference for your finished post.</p></div></div>
            {!themeOwnerValid && <p className="analytics-generation-lock">Choose which selected RZWire coin owns the visual theme first.</p>}
            {TEMPLATE_CATEGORIES.map(category => <div className="analytics-template-category" key={category.id}>
              <div><strong>{category.name}</strong><span>{category.description}</span></div>
              <div className="analytics-template-grid analytics-template-grid--exact">{category.variants.map(variant => {
                const selected = templateVariantId === variant.id
                const approved = compositionApprovals[variant.id] === compositionFingerprint({templateCategoryId:category.id, templateVariantId:variant.id, themeOwnerTokenId, marketData, period, scale, format, headline, chartText, direction})
                return <button key={variant.id} type="button" disabled={!themeOwnerValid} className={selected ? 'selected' : ''} onClick={() => chooseTemplate(variant.id)}><img src={variant.image} alt={`${variant.name} publishing concept ${variant.conceptLabel}`} /><span><b>Concept {variant.conceptLabel}</b><strong>{variant.name}</strong><small>{variant.description}</small>{selected && <em className={approved ? 'approved' : ''}>{approved ? 'Approved' : 'Needs approval'}</em>}</span>{selected && <Check size={18} />}</button>
              })}</div>
            </div>)}
            <div className="analytics-template-selection-note"><strong>1 sample selected</strong><span>{selectedCompositionApproved ? 'This composition is approved and ready for generation.' : 'Review and approve this exact composition before generation.'}</span></div>
          </section>}
          {chartApproved && <section className="analytics-control-section analytics-generation-controls"><div className="analytics-section-heading"><span>05</span><div><h2>Generate the finished post</h2><p>AI creates only the decorative atmosphere. RZWire exports the approved layout, device, copy, logo, and verified chart as protected foreground.</p></div></div><label>Image model<select value={imageModel} onChange={event => setImageModel(event.target.value)}>{IMAGE_MODEL_OPTIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label>Creative direction<textarea rows="3" value={direction} onChange={event => { setDirection(event.target.value); invalidateCompositions() }} /></label><button type="button" className="analytics-generate" disabled={generating || !marketData || !themeOwnerValid || !selectedCompositionApproved} onClick={generatePost}>{generating ? <><span className="analytics-spinner" />Creating {findTemplateVariant(generatingTemplateId)?.name || 'selected version'}…</> : <><Sparkles size={17} />Generate one finished post<ArrowRight size={17} /></>}</button>{!selectedCompositionApproved && <p className="analytics-generation-lock">Approve the selected composition in the preview panel to unlock generation.</p>}{error && <p className="analytics-error">{error}</p>}</section>}
        </aside>
        {chartApproved && themeOwnerValid && <section className="analytics-preview-column">
          <div className="analytics-preview-head"><div><p>Final composition preview</p><h2>{selectedTemplate.name}</h2><small>{themeOwner.name} visual system</small></div><span>{outputFormat.label}</span></div>
          <div className="analytics-reference-sample"><div><strong>Exact approved concept {selectedTemplate.conceptLabel}</strong><span>This image is the primary style target. The selected coin owner supplies its palette, logo, and footer while the verified chart replaces the sample market data.</span></div><img src={selectedTemplate.image} alt={`${selectedTemplate.name} exact approval concept`} /></div>
          <div className="analytics-live-output-label"><span>{generatedPost ? 'Finished protected PNG' : 'Locked final composition'}</span><small>The exact device, chart, copy, logo, and footer shown here remain fixed. Only the atmosphere behind them may change.</small></div>
          {generatedPost ? <img className="analytics-generated-post" src={generatedPost} alt={`Generated ${selectedTemplate.name} RZWire analytics post`} /> : <CompositionPreview templateCategoryId={selectedTemplate.categoryId} templateVariantId={selectedTemplate.id} themeOwnerTokenId={themeOwnerTokenId} theme={brandTheme} marketData={marketData} tokens={tokens} period={period} scale={scale} format={format} headline={headline} chartText={chartText} />}
          <div className={`analytics-composition-approval ${selectedCompositionApproved ? 'approved' : ''}`}><div><strong>{selectedCompositionApproved ? 'Composition approved' : 'Approve this composition'}</strong><span>{selectedCompositionApproved ? 'Its exact state is ready for generation.' : 'Check hierarchy, palette, logo, footer, chart, and copy.'}</span></div><button type="button" onClick={() => setCompositionApprovals(previous => ({...previous, [selectedTemplate.id]:selectedFingerprint}))}>{selectedCompositionApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve {selectedTemplate.name}</>}</button></div>
          {generatedPost && <div className={`analytics-final-approval ${finalImageApproved ? 'approved' : ''}`}><div><strong>{finalImageApproved ? 'Final image approved' : 'Approve the final image'}</strong><span>{finalImageApproved ? 'Publishing destinations are now unlocked.' : 'Inspect the finished image before any external publishing action becomes available.'}</span></div><button type="button" onClick={() => { setFinalApprovals(previous => ({...previous, [selectedTemplate.id]:generatedFingerprint})); setPublishResult('') }}>{finalImageApproved ? <><CircleCheck size={17} />Final approved</> : <><Check size={17} />Approve final image</>}</button></div>}
          {generatedPost && finalImageApproved && <div className="analytics-publish-choice"><div><strong>Where do you want to publish it?</strong><span>Choose one destination. Nothing is posted until you press the final publish button.</span></div><div className="analytics-publish-destinations"><button type="button" className={publishDestination === 'telegram' ? 'selected' : ''} onClick={() => { setPublishDestination('telegram'); setPublishResult('') }}><Send size={18} /><span><strong>Telegram</strong><small>Publish to the configured RZWire channel</small></span>{publishDestination === 'telegram' && <Check size={16} />}</button><button type="button" className={publishDestination === 'x' ? 'selected' : ''} onClick={() => { setPublishDestination('x'); setPublishResult('') }}><MessageCircle size={18} /><span><strong>X</strong><small>Publish with the approved market copy</small></span>{publishDestination === 'x' && <Check size={16} />}</button></div><button type="button" className="analytics-publish-final" disabled={!publishDestination || publishing} onClick={publishFinalImage}>{publishing ? <><span className="analytics-spinner" />Publishing…</> : <>Publish final image to {publishDestination === 'telegram' ? 'Telegram' : publishDestination === 'x' ? 'X' : 'selected destination'}<ArrowRight size={17} /></>}</button>{publishResult && <p className="analytics-publish-success"><CircleCheck size={16} />{publishResult}</p>}</div>}
          <div className="analytics-layer-note"><ImageIcon size={17} /><span><strong>Protected composition</strong>The selected concept guides only the atmosphere. RZWire deterministically locks the device, chart, financial facts, copy, logo, and footer into the final export.</span></div>
        </section>}
      </div>
    </main>
    {chartApproved && themeOwnerValid && <div className="analytics-export-renders" aria-hidden="true"><div key={`capture-${selectedTemplate.id}`} style={{width:`${outputFormat.width}px`}}><CompositionPreview ref={node => { frameRefs.current[selectedTemplate.id] = node }} templateCategoryId={selectedTemplate.categoryId} templateVariantId={selectedTemplate.id} themeOwnerTokenId={themeOwnerTokenId} theme={brandTheme} marketData={marketData} tokens={tokens} period={period} scale={scale} format={format} headline={headline} chartText={chartText} /></div></div>}
    <ChatWidget />
  </div>
}
