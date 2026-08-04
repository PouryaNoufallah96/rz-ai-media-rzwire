import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowRight, CalendarDays, Check, CircleCheck, Database, ImageIcon, LineChart, MessageCircle, Pencil, Plus, RefreshCw, Search, Send, Sparkles, X } from 'lucide-react'
import NavBar from '../components/NavBar'
import ChatWidget from '../components/chat/ChatWidget'
import { API_BASE, EDITORIAL_MODEL_META, IMAGE_MODEL_OPTIONS } from '../store/mmStore'
import ChartDesigner from '../components/analytics/ChartDesigner'
import CompositionPreview from '../components/analytics/AnalyticsCompositions'
import { OUTPUT_FORMATS, EXTERNAL_COLORS, analyticsTheme, compositionFingerprint } from '../components/analytics/analyticsCompositionConfig'
import {
  DEFAULT_CHART_STYLE,
  chartForeground,
  chartGridOpacity,
  chartStyleIssues,
  colorisedChartSeries,
  materializeCurrentSeriesColors,
  normalizeChartStyle,
  presetChartStyle,
} from '../components/analytics/chartStyle'
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
const CAPTION_PLATFORMS = [
  {id:'telegram', label:'Telegram', apiName:'Telegram', description:'Detailed editorial caption · 300–600 characters · 3–5 hashtags'},
  {id:'x', label:'X', apiName:'X', description:'Concise post · maximum 280 characters · no emoji'},
]
const EDITORIAL_MODELS = Object.entries(EDITORIAL_MODEL_META).map(([id, meta]) => ({id, ...meta}))
const ANALYTICS_IMAGE_MODEL_OPTIONS = IMAGE_MODEL_OPTIONS.filter(model => (model.maxReferences || 0) >= 2)
const WORKFLOW_STEPS = [
  {id:1, label:'Market', target:'analytics-step-market'},
  {id:2, label:'Chart', target:'analytics-step-chart'},
  {id:3, label:'Story', target:'analytics-step-story'},
  {id:4, label:'Design', target:'analytics-step-design'},
  {id:5, label:'Create & publish', target:'analytics-step-create'},
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

function chartToPngDataUrl(svgElement) {
  if (!svgElement) return Promise.reject(new Error('The approved chart is not available for composition.'))
  const clone = svgElement.cloneNode(true)
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  style.textContent = 'text{font-family:Inter,Arial,sans-serif}'
  clone.prepend(style)
  const source = new XMLSerializer().serializeToString(clone)
  const viewBox = (clone.getAttribute('viewBox') || '0 0 900 460').split(/\s+/).map(Number)
  const aspectWidth = Number.isFinite(viewBox[2]) && viewBox[2] > 0 ? viewBox[2] : 900
  const aspectHeight = Number.isFinite(viewBox[3]) && viewBox[3] > 0 ? viewBox[3] : 460
  const blobUrl = URL.createObjectURL(new Blob([source], {type:'image/svg+xml;charset=utf-8'}))
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = 1800
      canvas.height = Math.round(canvas.width * (aspectHeight / aspectWidth))
      const context = canvas.getContext('2d')
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

function legendGeometry(position, count) {
  if (position === 'left') return {left:258, right:858, top:34, bottom:378, x:22, y:72, columns:1, columnWidth:205, rowHeight:42}
  if (position === 'right') return {left:92, right:650, top:34, bottom:378, x:684, y:72, columns:1, columnWidth:190, rowHeight:42}
  if (position === 'top') return {left:92, right:858, top:104, bottom:388, x:100, y:30, columns:Math.min(3, count), columnWidth:250, rowHeight:34}
  if (position === 'bottom') return {left:92, right:858, top:34, bottom:326, x:100, y:374, columns:Math.min(3, count), columnWidth:250, rowHeight:34}
  return {left:92, right:858, top:34, bottom:388, x:0, y:0, columns:1, columnWidth:190, rowHeight:36}
}

function markerIndexes(pointCount, markerMode) {
  if (markerMode === 'all') return Array.from({length:pointCount}, (_, index) => index)
  if (markerMode === 'endpoints' && pointCount > 1) return [0, pointCount - 1]
  if (markerMode === 'endpoints' && pointCount === 1) return [0]
  return []
}

function SvgLegend({ series, chartStyle, geometry, foreground }) {
  const position = chartStyle.legend.position
  const overlay = position.startsWith('overlay-')
  const columns = geometry.columns
  const itemWidth = overlay ? 190 : geometry.columnWidth
  const rows = Math.ceil(series.length / columns)
  const panelWidth = overlay ? 204 : 0
  const panelHeight = overlay ? rows * geometry.rowHeight + 18 : 0
  const overlayX = geometry.right - panelWidth - 12
  const overlayY = position === 'overlay-top-right' ? geometry.top + 12 : geometry.bottom - panelHeight - 12
  const originX = overlay ? overlayX + 12 : geometry.x
  const originY = overlay ? overlayY + 10 : geometry.y
  return <g className="analytics-svg-legend">
    {overlay && <rect x={overlayX} y={overlayY} width={panelWidth} height={panelHeight} rx="10" fill={chartStyle.backgroundColor} fillOpacity=".94" stroke={foreground} strokeOpacity=".18" />}
    {series.map((item, index) => {
      const column = overlay ? 0 : index % columns
      const row = overlay ? index : Math.floor(index / columns)
      const x = originX + column * itemWidth
      const y = originY + row * geometry.rowHeight + 12
      const change = `${item.changePercent >= 0 ? '+' : ''}${Number(item.changePercent).toFixed(2)}%`
      return <g key={item.id} transform={`translate(${x} ${y})`}><circle cx="6" cy="0" r="6" fill={item.color} /><text x="19" y="4" fill={foreground} fontSize="15" fontWeight="750">{item.symbol}{chartStyle.legend.format === 'symbol-change' ? `  ${change}` : ''}</text></g>
    })}
  </g>
}

function VerifiedChart({ data, chartRef, tokens, chartStyle }) {
  const series = colorisedChartSeries(data, tokens, chartStyle)
  const scale = data.scale || 'relative'
  const valueSets = series.map(item => chartValues(item, scale))
  const allValues = valueSets.flat().filter(Number.isFinite)
  if (scale === 'relative') allValues.push(0)
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const padding = Math.max(scale === 'relative' ? 1 : Math.abs(rawMax || 1) * .02, (rawMax - rawMin) * .1)
  const min = rawMin - padding
  const max = rawMax + padding
  const chart = legendGeometry(chartStyle.legend.position, series.length)
  const timestamps = series.flatMap(item => item.points.map(point => Number(point.timestamp))).filter(Number.isFinite)
  const firstTimestamp = Math.min(...timestamps)
  const lastTimestamp = Math.max(...timestamps)
  const xFor = timestamp => chart.left + ((Number(timestamp) - firstTimestamp) / Math.max(1, lastTimestamp - firstTimestamp)) * (chart.right - chart.left)
  const yFor = value => chart.bottom - ((value - min) / Math.max(.000001, max - min)) * (chart.bottom - chart.top)
  const lineFor = (item, values) => item.points.map((point, index) => `${xFor(point.timestamp).toFixed(1)},${yFor(values[index]).toFixed(1)}`).join(' ')
  const yTicks = Array.from({length:6}, (_, index) => max - index * ((max - min) / 5))
  const dateTicks = Array.from({length:6}, (_, index) => firstTimestamp + index * ((lastTimestamp - firstTimestamp) / 5))

  const foreground = chartForeground(chartStyle.backgroundColor)
  const gridOpacity = chartGridOpacity(chartStyle.gridStrength)
  const dateLabelY = chart.bottom + 32

  return <div className="analytics-verified-chart">
    <div className="analytics-proof-title"><div><strong>{series.map(item => item.symbol).join(' / ')}</strong><span>{data.period} verified price history</span></div><b>{scale === 'relative' ? 'Relative %' : 'Absolute USD'}</b></div>
    <svg ref={chartRef} className="analytics-proof-svg" viewBox="0 0 900 460" role="img" aria-label={`${series.map(item => item.symbol).join(', ')} complete ${data.period} price chart`}>
      <rect width="900" height="460" fill={chartStyle.backgroundColor} />
      {yTicks.map((tick, index) => {
        const y = yFor(tick)
        const label = scale === 'absolute' ? formatPrice(tick) : `${tick >= 0 ? '+' : ''}${tick.toFixed(1)}%`
        return <g key={`y-${index}`}><line className="analytics-chart-grid-line" x1={chart.left} y1={y} x2={chart.right} y2={y} stroke={foreground} strokeOpacity={gridOpacity} strokeWidth="1" /><text className="analytics-axis-text analytics-axis-text--left" x={chart.left - 12} y={y + 4} fill={foreground} fillOpacity=".7" fontSize="12" textAnchor="end">{label}</text></g>
      })}
      {dateTicks.map((timestamp, index) => <text key={`x-${index}`} className="analytics-axis-text analytics-axis-text--date" x={xFor(timestamp)} y={dateLabelY} fill={foreground} fillOpacity=".7" fontSize="12" textAnchor="middle">{new Date(timestamp * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric'})}</text>)}
      {scale === 'relative' && min <= 0 && max >= 0 && <line className="analytics-chart-zero" x1={chart.left} y1={yFor(0)} x2={chart.right} y2={yFor(0)} stroke={foreground} strokeOpacity=".42" strokeWidth="1" strokeDasharray="5 4" />}
      {series.map((item, index) => <g key={item.id}>
        <polyline className="analytics-series analytics-series--verified" fill="none" stroke={item.color} strokeWidth={chartStyle.lineWidth} strokeLinecap="round" strokeLinejoin="round" points={lineFor(item, valueSets[index])} />
        {markerIndexes(item.points.length, chartStyle.markers).map(pointIndex => <circle key={pointIndex} cx={xFor(item.points[pointIndex].timestamp)} cy={yFor(valueSets[index][pointIndex])} r={Math.max(4, chartStyle.lineWidth + 1)} fill={chartStyle.backgroundColor} stroke={item.color} strokeWidth={Math.max(2, chartStyle.lineWidth / 2)} />)}
      </g>)}
      <SvgLegend series={series} chartStyle={chartStyle} geometry={chart} foreground={foreground} />
    </svg>
    <div className="analytics-series-status-grid">{series.map(item => <article key={item.id}><div><i style={{background:item.color}} /><strong>{item.symbol}</strong><span>{item.role === 'primary' ? 'RZWire' : item.type === 'dex' ? 'DEX' : 'Binance'}</span></div><dl><dt>Start</dt><dd>{formatPrice(item.startPrice)}</dd><dt>End</dt><dd>{formatPrice(item.endPrice)}</dd><dt>Coverage</dt><dd>{formatDate(item.coverageStart)} - {formatDate(item.coverageEnd)}</dd></dl></article>)}</div>
    {!!data.warnings?.length && <div className="analytics-warning-list">{data.warnings.map(warning => <p key={warning}><AlertTriangle size={14} />{warning}</p>)}</div>}
    <div className="analytics-source-list"><strong>Verified sources</strong>{series.map(item => <a key={item.id} href={item.source?.attributionUrl} target="_blank" rel="noreferrer">{item.symbol} - {item.source?.provider}</a>)}</div>
  </div>
}

export default function AnalyticsPage() {
  const chartSvgRef = useRef(null)
  const latestCompositionFingerprint = useRef('')
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
  const [captionModelKey, setCaptionModelKey] = useState('')
  const [captionVariants, setCaptionVariants] = useState([])
  const [selectedCaptionIndex, setSelectedCaptionIndex] = useState(-1)
  const [editingCaptionIndex, setEditingCaptionIndex] = useState(-1)
  const [captionEditDraft, setCaptionEditDraft] = useState({copy:'', hashtags:''})
  const [generatingCaptions, setGeneratingCaptions] = useState(false)
  const [captionError, setCaptionError] = useState('')
  const [publishing, setPublishing] = useState(false)
  const [publishResult, setPublishResult] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generatingTemplateId, setGeneratingTemplateId] = useState('')
  const [error, setError] = useState('')
  const [marketData, setMarketData] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [verificationError, setVerificationError] = useState('')
  const [chartApproved, setChartApproved] = useState(false)
  const [chartStyle, setChartStyle] = useState(DEFAULT_CHART_STYLE)
  const [chartDefaultLoading, setChartDefaultLoading] = useState(false)
  const [chartDefaultSaving, setChartDefaultSaving] = useState(false)
  const [chartDefaultMessage, setChartDefaultMessage] = useState(null)
  const [headline, setHeadline] = useState('30-day market comparison')
  const [chartText, setChartText] = useState('Verified movement, presented with exact market data.')
  const [activeWorkflowStep, setActiveWorkflowStep] = useState(1)

  const selectedPrimary = tokens.filter(token => primaryIds.includes(token.id))
  const allSelectedSymbols = [...selectedPrimary.map(token => token.symbol), ...comparisonAssets.map(asset => asset.symbol)]
  const seriesCount = allSelectedSymbols.length
  const selectedTemplate = findTemplateVariant(templateVariantId) || TEMPLATE_VARIANTS[3]
  const selectedTemplateCategory = TEMPLATE_CATEGORIES.find(category => category.id === selectedTemplate.categoryId) || TEMPLATE_CATEGORIES[0]
  const themeOwnerValid = selectedPrimary.some(token => token.id === themeOwnerTokenId)
  const themeOwner = tokens.find(token => token.id === themeOwnerTokenId)
  const brandTheme = themeOwnerValid ? analyticsTheme(themeOwnerTokenId, tokens) : null
  const styledSeries = colorisedChartSeries(marketData, tokens, chartStyle)
  const chartIssues = marketData ? chartStyleIssues(chartStyle, styledSeries) : []
  const outputFormat = OUTPUT_FORMATS.find(item => item.id === format) || OUTPUT_FORMATS[0]
  const generatedPost = generatedPosts[selectedTemplate.id] || ''
  const selectedFingerprint = marketData && brandTheme ? compositionFingerprint({templateCategoryId:selectedTemplate.categoryId, templateVariantId:selectedTemplate.id, themeOwnerTokenId, marketData, period, scale, format, headline, chartText, direction, chartStyle}) : ''
  latestCompositionFingerprint.current = selectedFingerprint
  const selectedCompositionApproved = Boolean(selectedFingerprint && compositionApprovals[selectedTemplate.id] === selectedFingerprint)
  const generatedFingerprint = finalImageFingerprint(generatedPost, selectedFingerprint)
  const finalImageApproved = Boolean(generatedFingerprint && finalApprovals[selectedTemplate.id] === generatedFingerprint)
  const summary = `${allSelectedSymbols.join(' versus ')}, ${period}, ${scale === 'relative' ? 'relative performance' : 'absolute USD price'}`
  const visibleAssetResults = assetQuery.trim() ? assetResults : POPULAR_COMPARISONS
  const workflowCompleted = {
    1:Boolean(marketData),
    2:chartApproved,
    3:chartApproved,
    4:selectedCompositionApproved,
    5:Boolean(publishResult),
  }

  function navigateWorkflow(step) {
    const locked = step.id >= 3 && !chartApproved
    if (locked) return
    setActiveWorkflowStep(step.id)
    document.getElementById(step.target)?.scrollIntoView({behavior:'smooth', block:'start'})
  }

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
    if (!themeOwnerTokenId || !tokens.some(token => token.id === themeOwnerTokenId)) return undefined
    const controller = new AbortController()
    setChartDefaultLoading(true)
    setChartDefaultMessage(null)
    fetch(`${API_BASE}/api/account/analytics-chart-default?brandId=${encodeURIComponent(themeOwnerTokenId)}`, {credentials:'include', signal:controller.signal})
      .then(async response => {
        const data = await response.json().catch(() => ({}))
        if (!response.ok) throw new Error(data.error || 'The saved chart default could not be loaded.')
        const next = normalizeChartStyle(data.style || DEFAULT_CHART_STYLE, analyticsTheme(themeOwnerTokenId, tokens), null, tokens)
        setChartStyle(next)
        setChartApproved(false)
        setCompositionApprovals({})
        setGeneratedPosts({})
        setFinalApprovals({})
        resetCaptionFlow()
        if (data.style) setChartDefaultMessage({type:'success', text:'Your private brand chart default is loaded.'})
      })
      .catch(err => {
        if (err.name !== 'AbortError') setChartDefaultMessage({type:'warning', text:err.message || 'The saved chart default could not be loaded. The current chart remains usable.'})
      })
      .finally(() => { if (!controller.signal.aborted) setChartDefaultLoading(false) })
    return () => controller.abort()
  }, [themeOwnerTokenId, tokens])

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

  function resetCaptionFlow({keepDestination=false, keepModel=false}={}) {
    if (!keepDestination) setPublishDestination('')
    if (!keepModel) setCaptionModelKey('')
    setCaptionVariants([])
    setSelectedCaptionIndex(-1)
    setEditingCaptionIndex(-1)
    setCaptionEditDraft({copy:'', hashtags:''})
    setCaptionError('')
    setPublishResult('')
  }

  function invalidateMarketData() {
    setActiveWorkflowStep(1)
    setMarketData(null)
    setChartApproved(false)
    setVerificationError('')
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    resetCaptionFlow()
    setError('')
  }

  function invalidateCompositions() {
    setGeneratedPosts({})
    setFinalApprovals({})
    resetCaptionFlow()
    setError('')
  }

  function invalidateChartStyleApprovals() {
    setActiveWorkflowStep(2)
    setChartApproved(false)
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    resetCaptionFlow()
    setError('')
  }

  function commitChartStyle(next) {
    setChartStyle(normalizeChartStyle(next, brandTheme, marketData, tokens))
    setChartDefaultMessage(null)
    invalidateChartStyleApprovals()
  }

  function applyChartPreset(presetId) {
    commitChartStyle(presetChartStyle(presetId, brandTheme, marketData, tokens))
  }

  function updateChartStyle(path, value) {
    if (path.startsWith('legend.')) {
      const legendKey = path.split('.')[1]
      commitChartStyle({...chartStyle, presetId:'custom', legend:{...chartStyle.legend, [legendKey]:value}})
      return
    }
    commitChartStyle({...chartStyle, presetId:'custom', [path]:value})
  }

  function updateSeriesColor(seriesId, color) {
    commitChartStyle({...chartStyle, presetId:'custom', seriesColors:{...chartStyle.seriesColors, [seriesId]:color}})
  }

  function resetSeriesColor(seriesId) {
    const seriesColors = {...chartStyle.seriesColors}
    delete seriesColors[seriesId]
    commitChartStyle({...chartStyle, presetId:'custom', seriesColors})
  }

  async function saveChartDefault() {
    if (!themeOwnerValid || chartDefaultSaving || chartIssues.length) return
    setChartDefaultSaving(true)
    setChartDefaultMessage(null)
    const completeStyle = materializeCurrentSeriesColors(chartStyle, marketData, tokens)
    try {
      const response = await fetch(`${API_BASE}/api/account/analytics-chart-default`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({brandId:themeOwnerTokenId, style:completeStyle})})
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.ok) throw new Error(data.error || 'The chart default could not be saved.')
      setChartDefaultMessage({type:'success', text:`Saved as your ${themeOwner?.symbol || ''} chart default.`})
    } catch (err) {
      setChartDefaultMessage({type:'warning', text:err.message || 'The chart default could not be saved. The current chart remains usable.'})
    } finally {
      setChartDefaultSaving(false)
    }
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
    setChartApproved(false)
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    resetCaptionFlow()
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
    setActiveWorkflowStep(2)
    setVerifying(true)
    setVerificationError('')
    setMarketData(null)
    setChartApproved(false)
    setCompositionApprovals({})
    setGeneratedPosts({})
    setFinalApprovals({})
    resetCaptionFlow()
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
    setActiveWorkflowStep(4)
    setTemplateVariantId(id)
    if (id.startsWith('phone-')) setFormat('story')
    resetCaptionFlow()
  }

  async function generatePost() {
    if (generating) return
    setActiveWorkflowStep(5)
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
    const requestedFingerprint = selectedFingerprint
    setGeneratingTemplateId(selectedTemplate.id)
    setFinalApprovals(previous => ({...previous, [selectedTemplate.id]:''}))
    resetCaptionFlow()
    setError('')
    try {
      const approvedChart = await chartToPngDataUrl(chartSvgRef.current)
      const approvalSample = await imageUrlToDataUrl(selectedTemplate.image)
      const approvedStyle = materializeCurrentSeriesColors(chartStyle, marketData, tokens)
      const approvedSeries = colorisedChartSeries(marketData, tokens, approvedStyle)
      const movement = marketData.series.reduce((total, item) => total + item.changePercent, 0) / marketData.series.length
      const response = await fetch(`${API_BASE}/api/image/generate-async`, {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({
            article:{title:headline || summary}, platform:'Instagram', mediaBrand:themeOwner.brand, sentiment:movement >= 0 ? 'Bullish' : 'Bearish', model:imageModel, compositionMode:'analytics_art_directed', copy:chartText,
            templateId:selectedTemplate.id,
            templateCategoryId:selectedTemplate.categoryId,
            templateVariantId:selectedTemplate.id,
            themeOwnerTokenId,
            brandTheme:brandTheme.id,
            outputDimensions:{width:outputFormat.width, height:outputFormat.height, ratio:format},
            seriesMetadata:approvedSeries.map(item => ({id:item.id, tokenId:item.tokenId, symbol:item.symbol, name:item.name, role:item.role, color:item.color, startPrice:item.startPrice, endPrice:item.endPrice, changePercent:item.changePercent, coverageStart:item.coverageStart, coverageEnd:item.coverageEnd})),
            chartStyle:approvedStyle,
            referenceImages:[approvalSample, approvedChart],
            imageDirection:`Treat the approved ${selectedTemplate.name} sample as a binding publishing family. Recreate that same premium composition for ${brandTheme.label}; adapt its palette, identity, exact supplied copy, and verified market content. Keep the complete approved chart sharp and physically inside the sample's reserved chart aperture or device screen. The Art Director brief must fully specify the card's geometry, module proportions, hierarchy, typography, spacing, materials, lighting, logo and footer placement, and forbidden changes. ${direction}`,
          })})
      const started = await response.json().catch(() => ({}))
      if (!response.ok || !started.jobId) throw new Error(started.error || 'The Analytics Art Director could not start the image job.')

      const deadline = Date.now() + (10 * 60 * 1000)
      let data = null
      while (Date.now() < deadline) {
        await new Promise(resolve => setTimeout(resolve, 2000))
        const statusResponse = await fetch(`${API_BASE}/api/image/generation-status?jobId=${encodeURIComponent(started.jobId)}`, {credentials:'include'})
        const job = await statusResponse.json().catch(() => ({}))
        if (!statusResponse.ok) throw new Error(job.error || 'The Analytics Art Director job could not be checked.')
        if (job.status === 'failed') throw new Error(job.error || 'The Analytics Art Director could not generate the finished post.')
        if (job.status === 'complete') {
          data = job.result || {}
          break
        }
      }
      if (!data) throw new Error('The Analytics Art Director is taking longer than expected. Please try again.')
      if (!data.imageB64) throw new Error(data.error || 'The Analytics Art Director did not return a finished post.')
      const finishedPost = data.imageB64.startsWith('data:') ? data.imageB64 : `data:image/png;base64,${data.imageB64}`
      await preloadImage(finishedPost)
      if (latestCompositionFingerprint.current !== requestedFingerprint) {
        throw new Error('The chart or composition changed during generation. Approve the current version and generate it again.')
      }
      setGeneratedPosts(previous => ({...previous, [selectedTemplate.id]:finishedPost}))
    } catch (err) {
      setError(err.message || 'Post generation failed.')
    } finally {
      setGenerating(false)
      setGeneratingTemplateId('')
    }
  }

  function chooseCaptionPlatform(destination) {
    setPublishDestination(destination)
    resetCaptionFlow({keepDestination:true})
  }

  function chooseCaptionModel(modelKey) {
    setCaptionModelKey(modelKey)
    resetCaptionFlow({keepDestination:true, keepModel:true})
  }

  function captionPostText(variant) {
    if (!variant) return ''
    return [variant.copy, (variant.hashtags || []).join(' ')].filter(Boolean).join('\n\n')
  }

  function parseCaptionHashtags(value) {
    return value.split(/[\s,]+/).map(tag => tag.trim()).filter(Boolean).map(tag => tag.startsWith('#') ? tag : `#${tag}`)
  }

  function beginCaptionEdit(index) {
    const variant = captionVariants[index]
    if (!variant) return
    setEditingCaptionIndex(index)
    setCaptionEditDraft({copy:variant.copy || '', hashtags:(variant.hashtags || []).join(' ')})
    setSelectedCaptionIndex(index)
    setCaptionError('')
    setPublishResult('')
  }

  function cancelCaptionEdit() {
    setEditingCaptionIndex(-1)
    setCaptionEditDraft({copy:'', hashtags:''})
    setCaptionError('')
  }

  function saveCaptionEdit(index) {
    const copy = captionEditDraft.copy.trim()
    const hashtags = parseCaptionHashtags(captionEditDraft.hashtags)
    const postLength = captionPostText({copy, hashtags}).length
    if (!copy) {
      setCaptionError('Caption text cannot be empty.')
      return
    }
    if (publishDestination === 'x' && postLength > 280) {
      setCaptionError('The edited X post must be 280 characters or fewer, including hashtags.')
      return
    }
    setCaptionVariants(previous => previous.map((variant, variantIndex) => variantIndex === index ? {...variant, copy, hashtags} : variant))
    setEditingCaptionIndex(-1)
    setCaptionEditDraft({copy:'', hashtags:''})
    setCaptionError('')
    setPublishResult('')
  }

  async function generateCaptionOptions() {
    if (generatingCaptions || !finalImageApproved || !publishDestination || !captionModelKey || !marketData?.series?.length) return
    setGeneratingCaptions(true)
    setCaptionError('')
    setCaptionVariants([])
    setSelectedCaptionIndex(-1)
    setEditingCaptionIndex(-1)
    setCaptionEditDraft({copy:'', hashtags:''})
    setPublishResult('')
    const platform = CAPTION_PLATFORMS.find(item => item.id === publishDestination)
    const marketFacts = marketData.series.map(item => {
      const movement = `${item.changePercent >= 0 ? '+' : ''}${Number(item.changePercent).toFixed(2)}%`
      return `${item.symbol}: ${formatPrice(item.startPrice)} to ${formatPrice(item.endPrice)} (${movement}), ${formatDate(item.coverageStart)} to ${formatDate(item.coverageEnd)}, source ${item.source?.provider || 'verified market feed'}`
    }).join('; ')
    const averageMovement = marketData.series.reduce((sum, item) => sum + Number(item.changePercent || 0), 0) / marketData.series.length
    try {
      const response = await fetch(`${API_BASE}/api/copy/generate`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          article:{
            title:headline,
            source:'RZWire verified Market Analytics',
            desc:`${chartText}\nRequested period: ${period}. Chart scale: ${scale === 'relative' ? 'relative percentage performance' : 'absolute USD price'}. Verified facts: ${marketFacts}`,
            matchedKeywords:allSelectedSymbols,
          },
          platform:platform?.apiName || 'Telegram',
          mediaBrand:themeOwner.brand,
          sentiment:averageMovement > 0.25 ? 'Bullish' : averageMovement < -0.25 ? 'Bearish' : 'Neutral',
          modelKey:captionModelKey,
          language:'en',
          promoMode:false,
          variantCount:3,
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || data.variants?.length < 3) throw new Error(data.error || 'The editorial model did not return all three caption options.')
      setCaptionVariants(data.variants.slice(0, 3))
    } catch (err) {
      setCaptionError(err.message || 'Caption generation failed.')
    } finally {
      setGeneratingCaptions(false)
    }
  }

  async function publishFinalImage() {
    const selectedCaption = captionVariants[selectedCaptionIndex]
    if (publishing || !finalImageApproved || !generatedPost || !publishDestination || !selectedCaption) return
    setPublishing(true)
    setPublishResult('')
    setError('')
    try {
      const isTelegram = publishDestination === 'telegram'
      const response = await fetch(`${API_BASE}${isTelegram ? '/api/telegram/post' : '/api/twitter/post'}`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body:JSON.stringify(isTelegram
          ? {imageB64:generatedPost, headline, copy:selectedCaption.copy, hashtags:selectedCaption.hashtags || [], link:'', mediaBrand:themeOwner.brand}
          : {imageB64:generatedPost, copy:selectedCaption.copy, hashtags:selectedCaption.hashtags || [], platform:'X', mediaBrand:themeOwner.brand}),
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
      <section className="analytics-intro"><div><p className="analytics-eyebrow"><LineChart size={16} /> Market Analytics</p><h1>Compare the complete RZWire market.</h1><p>Select up to three RZWire tokens and three outside assets, approve one exact chart, then turn it into a branded visual story.</p></div></section>
      <nav className="analytics-steps" aria-label="Analytics post workflow">{WORKFLOW_STEPS.map((step, index) => <span key={step.id} className={`${activeWorkflowStep === step.id ? 'active' : ''} ${workflowCompleted[step.id] ? 'completed' : ''}`}><button type="button" disabled={step.id >= 3 && !chartApproved} aria-current={activeWorkflowStep === step.id ? 'step' : undefined} onClick={() => navigateWorkflow(step)}><b>{workflowCompleted[step.id] ? <Check size={13} /> : step.id}</b>{step.label}</button>{index < WORKFLOW_STEPS.length - 1 && <i />}</span>)}</nav>
      <div className="analytics-layout analytics-layout--storyboard">
        <aside className="analytics-controls">
          <section id="analytics-step-market" className="analytics-control-section analytics-setup-section">
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
          <section id="analytics-step-chart" className="analytics-control-section analytics-verification-controls">
            <div className="analytics-section-heading"><span>02</span><div><h2>Customize and approve the verified chart</h2><p>Style the presentation while every selected price, date, axis, movement, and line remains locked.</p></div></div>
            <button type="button" className="analytics-verify" disabled={verifying || !primaryIds.length} onClick={verifyMarketData}>{verifying ? <><span className="analytics-spinner" />Extracting {seriesCount} price histories…</> : <><RefreshCw size={16} />Fetch and verify {seriesCount} chart {seriesCount === 1 ? 'line' : 'lines'}</>}</button>
            {verificationError && <p className="analytics-error">{verificationError}</p>}
            {!marketData && !verifying && <div className="analytics-proof-empty"><LineChart size={28} /><strong>Your complete verified chart will appear here</strong><span>RZWire will fetch every selected history concurrently and keep available lines if another provider fails.</span></div>}
            {marketData && <>
              <ChartDesigner
                style={chartStyle}
                series={styledSeries}
                tokens={tokens}
                ownerSelected={themeOwnerValid}
                loading={chartDefaultLoading}
                saving={chartDefaultSaving}
                message={chartDefaultMessage}
                issues={chartIssues}
                onPreset={applyChartPreset}
                onBackground={color => updateChartStyle('backgroundColor', color)}
                onSeriesColor={updateSeriesColor}
                onResetSeries={resetSeriesColor}
                onOption={updateChartStyle}
                onReset={() => commitChartStyle(presetChartStyle('clean-light', brandTheme, marketData, tokens))}
                onSave={saveChartDefault}
              />
              <VerifiedChart data={marketData} chartRef={chartSvgRef} tokens={tokens} chartStyle={chartStyle} />
              {!!marketData.failures?.length && <div className="analytics-failure-summary"><AlertTriangle size={16} /><span><strong>{marketData.failures.length} selected {marketData.failures.length === 1 ? 'asset was' : 'assets were'} unavailable.</strong>{marketData.failures.map(item => <small key={item.id}>{item.symbol} — {item.error}</small>)}<small>The verified lines above can still be approved.</small></span></div>}
              <div className="analytics-chart-approval"><div><strong>{chartApproved ? 'Chart approved' : chartIssues.length ? 'Resolve the chart color warnings' : 'Check every line and label before continuing'}</strong><span>{chartApproved ? 'Story and publishing choices are unlocked.' : chartIssues.length ? 'Approval is blocked until every series is distinct and readable.' : 'Confirm the prices, axes, dates, warnings, source attribution, and styling.'}</span></div><button type="button" disabled={!!chartIssues.length} className={chartApproved ? 'approved' : ''} onClick={() => { if (!chartIssues.length) { setChartApproved(true); setActiveWorkflowStep(3) } }}>{chartApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve complete chart</>}</button></div>
            </>}
          </section>
          {chartApproved && <section id="analytics-step-story" className="analytics-control-section analytics-copy-section"><div className="analytics-section-heading"><span>03</span><div><h2>Write the story</h2><p>Set the header and supporting statement that guide every publishing design.</p></div></div><div className="analytics-copy-fields"><label>Header<input value={headline} onFocus={() => setActiveWorkflowStep(3)} onChange={event => { setHeadline(event.target.value); invalidateCompositions() }} /></label><label>Chart text<textarea rows="2" value={chartText} onFocus={() => setActiveWorkflowStep(3)} onChange={event => { setChartText(event.target.value); invalidateCompositions() }} /></label></div></section>}
          {chartApproved && <section id="analytics-step-design" className={`analytics-control-section analytics-template-section ${!themeOwnerValid ? 'is-locked' : ''}`}>
            <div className="analytics-section-heading"><span>04</span><div><h2>Choose how to publish it</h2><p>Choose exactly one permanent concept. Its image becomes the primary visual reference for your finished post.</p></div></div>
            {!themeOwnerValid && <p className="analytics-generation-lock">Choose which selected RZWire coin owns the visual theme first.</p>}
            <div className="analytics-family-tabs" role="tablist" aria-label="Publishing families">{TEMPLATE_CATEGORIES.map(category => <button key={category.id} type="button" role="tab" aria-selected={selectedTemplateCategory.id === category.id} disabled={!themeOwnerValid} className={selectedTemplateCategory.id === category.id ? 'selected' : ''} onClick={() => chooseTemplate(category.variants[0].id)}><strong>{category.name}</strong><span>{category.description}</span></button>)}</div>
            <div className="analytics-template-category analytics-template-category--active" role="tabpanel">
              <div><strong>{selectedTemplateCategory.name}</strong><span>Compare its three permanent concepts across the full page width.</span></div>
              <div className="analytics-template-grid analytics-template-grid--exact">{selectedTemplateCategory.variants.map(variant => {
                const selected = templateVariantId === variant.id
                const approved = compositionApprovals[variant.id] === compositionFingerprint({templateCategoryId:selectedTemplateCategory.id, templateVariantId:variant.id, themeOwnerTokenId, marketData, period, scale, format, headline, chartText, direction, chartStyle})
                return <button key={variant.id} type="button" disabled={!themeOwnerValid} className={selected ? 'selected' : ''} onClick={() => chooseTemplate(variant.id)}><img src={variant.image} alt={`${variant.name} publishing concept ${variant.conceptLabel}`} /><span><b>Concept {variant.conceptLabel}</b><strong>{variant.name}</strong><small>{variant.description}</small>{selected && <em className={approved ? 'approved' : ''}>{approved ? 'Approved' : 'Needs approval'}</em>}</span>{selected && <Check size={18} />}</button>
              })}</div>
            </div>
            <div className="analytics-template-selection-note"><strong>1 sample selected</strong><span>{selectedCompositionApproved ? 'This composition is approved and ready for generation.' : 'Review and approve this exact composition before generation.'}</span></div>
          </section>}
          {chartApproved && <section id="analytics-step-create" className="analytics-control-section analytics-generation-controls"><div className="analytics-section-heading"><span>05</span><div><h2>Create and publish</h2><p>Generate the visual, approve it, prepare a caption, and publish only when everything is ready.</p></div></div><label>Image model<select value={imageModel} onChange={event => setImageModel(event.target.value)}>{ANALYTICS_IMAGE_MODEL_OPTIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label><label>Creative direction<textarea rows="3" value={direction} onChange={event => { setDirection(event.target.value); invalidateCompositions() }} /></label><button type="button" className="analytics-generate" disabled={generating || !marketData || !themeOwnerValid || !selectedCompositionApproved} onClick={generatePost}>{generating ? <><span className="analytics-spinner" />Creating {findTemplateVariant(generatingTemplateId)?.name || 'selected version'}…</> : <><Sparkles size={17} />Generate one finished post<ArrowRight size={17} /></>}</button>{!selectedCompositionApproved && <p className="analytics-generation-lock">Approve the selected composition in the preview panel to unlock generation.</p>}{error && <p className="analytics-error">{error}</p>}</section>}
        </aside>
        {chartApproved && themeOwnerValid && <section className="analytics-preview-column">
          <div className="analytics-preview-head"><div><p>Final composition preview</p><h2>{selectedTemplate.name}</h2><small>{themeOwner.name} visual system</small></div><span>{outputFormat.label}</span></div>
          <div className="analytics-reference-sample"><div><strong>Exact approved concept {selectedTemplate.conceptLabel}</strong><span>This image is the primary style target. The selected coin owner supplies its palette, logo, and footer while the verified chart replaces the sample market data.</span></div><img src={selectedTemplate.image} alt={`${selectedTemplate.name} exact approval concept`} /></div>
          <div className="analytics-live-output-label"><span>{generatedPost ? 'Finished Art Director PNG' : 'Approved composition specification'}</span><small>The approved sample defines the visual family. The detailed Art Director brief defines the complete card, while the approved chart supplies its factual market content.</small></div>
          {generatedPost ? <img className="analytics-generated-post" src={generatedPost} alt={`Generated ${selectedTemplate.name} RZWire analytics post`} /> : <CompositionPreview templateCategoryId={selectedTemplate.categoryId} templateVariantId={selectedTemplate.id} themeOwnerTokenId={themeOwnerTokenId} theme={brandTheme} marketData={marketData} tokens={tokens} period={period} scale={scale} format={format} headline={headline} chartText={chartText} chartStyle={chartStyle} />}
          <div className={`analytics-composition-approval ${selectedCompositionApproved ? 'approved' : ''}`}><div><strong>{selectedCompositionApproved ? 'Composition approved' : 'Approve this composition'}</strong><span>{selectedCompositionApproved ? 'Its exact state is ready for generation.' : 'Check hierarchy, palette, logo, footer, chart, and copy.'}</span></div><button type="button" onClick={() => { setCompositionApprovals(previous => ({...previous, [selectedTemplate.id]:selectedFingerprint})); setActiveWorkflowStep(5) }}>{selectedCompositionApproved ? <><CircleCheck size={17} />Approved</> : <><Check size={17} />Approve {selectedTemplate.name}</>}</button></div>
          {generatedPost && <div className={`analytics-final-approval ${finalImageApproved ? 'approved' : ''}`}><div><strong>{finalImageApproved ? 'Final image approved' : 'Approve the final image'}</strong><span>{finalImageApproved ? 'The caption and publishing workflow is now unlocked.' : 'Inspect the finished image before creating any external post copy.'}</span></div><button type="button" onClick={() => { setFinalApprovals(previous => ({...previous, [selectedTemplate.id]:generatedFingerprint})); resetCaptionFlow() }}>{finalImageApproved ? <><CircleCheck size={17} />Final approved</> : <><Check size={17} />Approve final image</>}</button></div>}
          {generatedPost && finalImageApproved && <div className="analytics-caption-workflow">
            <div className="analytics-caption-heading"><span>06</span><div><strong>Create the post caption</strong><small>Use the same platform rules and editorial models as Multimedia. Nothing is published until the final step.</small></div></div>
            <div className="analytics-caption-stage"><div><b>1</b><span><strong>Choose the platform</strong><small>The editorial rules change automatically for Telegram or X.</small></span></div><div className="analytics-publish-destinations">{CAPTION_PLATFORMS.map(item => <button type="button" key={item.id} className={publishDestination === item.id ? 'selected' : ''} onClick={() => chooseCaptionPlatform(item.id)}>{item.id === 'telegram' ? <Send size={18} /> : <MessageCircle size={18} />}<span><strong>{item.label}</strong><small>{item.description}</small></span>{publishDestination === item.id && <Check size={16} />}</button>)}</div></div>
            {publishDestination && <div className="analytics-caption-stage"><div><b>2</b><span><strong>Choose the AI editorial model</strong><small>This model writes three captions from the verified chart facts.</small></span></div><div className="analytics-editorial-models">{EDITORIAL_MODELS.map(model => <button type="button" key={model.id} className={captionModelKey === model.id ? 'selected' : ''} style={{'--model-color':model.color}} onClick={() => chooseCaptionModel(model.id)}><i>{model.badge}</i><span><strong>{model.display}</strong><small>{model.desc}</small></span>{captionModelKey === model.id && <Check size={15} />}</button>)}</div></div>}
            {publishDestination && captionModelKey && <button type="button" className="analytics-generate-captions" disabled={generatingCaptions} onClick={generateCaptionOptions}>{generatingCaptions ? <><span className="analytics-spinner" />Writing three {publishDestination === 'x' ? 'X posts' : 'Telegram captions'}…</> : <><Sparkles size={16} />Generate 3 caption options<ArrowRight size={16} /></>}</button>}
            {captionError && <p className="analytics-error">{captionError}</p>}
            {!!captionVariants.length && <div className="analytics-caption-stage">
              <div><b>3</b><span><strong>Select and edit one caption</strong><small>Edit any option, then select the version that should be published with the approved image.</small></span></div>
              <div className="analytics-caption-options">{captionVariants.map((variant, index) => {
                const selected = selectedCaptionIndex === index
                const editingCaption = editingCaptionIndex === index
                const text = captionPostText(variant)
                const draftHashtags = editingCaption ? parseCaptionHashtags(captionEditDraft.hashtags) : []
                const draftLength = editingCaption ? captionPostText({copy:captionEditDraft.copy, hashtags:draftHashtags}).length : 0
                const draftInvalid = editingCaption && (!captionEditDraft.copy.trim() || (publishDestination === 'x' && draftLength > 280))
                return <article key={`${variant.label}-${index}`} className={`analytics-caption-option ${selected ? 'selected' : ''} ${editingCaption ? 'editing' : ''}`}>
                  <div className="analytics-caption-option-head">
                    <span><b>Option {index + 1}</b><em>{variant.label}</em></span>
                    <span>
                      {!editingCaption && <button type="button" className="analytics-caption-edit" onClick={() => beginCaptionEdit(index)}><Pencil size={12} />Edit</button>}
                      {selected && <Check size={15} />}
                    </span>
                  </div>
                  {editingCaption ? <>
                    <label className="analytics-caption-edit-field">Caption<textarea autoFocus rows="6" value={captionEditDraft.copy} onChange={event => { setCaptionEditDraft(previous => ({...previous, copy:event.target.value})); setCaptionError('') }} /></label>
                    <label className="analytics-caption-edit-field">Hashtags<input value={captionEditDraft.hashtags} onChange={event => { setCaptionEditDraft(previous => ({...previous, hashtags:event.target.value})); setCaptionError('') }} placeholder="#MGC #CryptoMarkets" /></label>
                    <div className="analytics-caption-edit-footer">
                      <i className={draftInvalid ? 'invalid' : ''}>{draftLength} characters{publishDestination === 'x' ? ' / 280' : ''}</i>
                      <span><button type="button" onClick={cancelCaptionEdit}>Cancel</button><button type="button" className="save" disabled={draftInvalid} onClick={() => saveCaptionEdit(index)}>Save changes</button></span>
                    </div>
                  </> : <button type="button" className="analytics-caption-choice" onClick={() => { setSelectedCaptionIndex(index); setPublishResult('') }}>
                    <p>{variant.copy}</p>
                    {!!variant.hashtags?.length && <small>{variant.hashtags.join(' ')}</small>}
                    <i>{text.length} characters{publishDestination === 'x' ? ' / 280' : ''}</i>
                  </button>}
                </article>
              })}</div>
            </div>}
            {!!captionVariants.length && <div className="analytics-caption-stage analytics-caption-publish"><div><b>4</b><span><strong>Publish the approved image and selected caption</strong><small>{editingCaptionIndex >= 0 ? 'Save or cancel the open caption edit before publishing.' : `RZWire sends both together to the configured ${publishDestination === 'telegram' ? 'Telegram channel' : 'X account'}.`}</small></span></div><button type="button" className="analytics-publish-final" disabled={selectedCaptionIndex < 0 || editingCaptionIndex >= 0 || publishing} onClick={publishFinalImage}>{publishing ? <><span className="analytics-spinner" />Publishing…</> : <>Publish to {publishDestination === 'telegram' ? 'Telegram' : 'X'}<ArrowRight size={17} /></>}</button>{publishResult && <p className="analytics-publish-success"><CircleCheck size={16} />{publishResult}</p>}</div>}
          </div>}
          <div className="analytics-layer-note"><ImageIcon size={17} /><span><strong>Two-reference Art Director pipeline</strong>The image model receives only the approved publishing sample and approved factual chart. A fully detailed production brief specifies the card structure, copy, branding, chart placement, and finish.</span></div>
        </section>}
      </div>
    </main>
    <ChatWidget />
  </div>
}
