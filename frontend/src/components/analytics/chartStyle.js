export const FALLBACK_SERIES_COLORS = ['#B8665E', '#3978C7', '#A95EBB', '#2F8066', '#B86414', '#6D74D8']
export const COLORBLIND_SERIES_COLORS = ['#0072B2', '#A56C00', '#007B5A', '#A75085', '#C44E00', '#347F9E']
export const HIGH_CONTRAST_SERIES_COLORS = ['#FFD21F', '#41C7FF', '#FF6B61', '#66E28A', '#D38BFF', '#FFFFFF']

export const CHART_PRESETS = [
  {id:'clean-light', label:'Clean Light'},
  {id:'brand-dark', label:'Brand Dark'},
  {id:'high-contrast', label:'High Contrast'},
  {id:'colorblind-safe', label:'Color-Blind Safe'},
]

export const LEGEND_POSITIONS = [
  {id:'top', label:'Top'},
  {id:'bottom', label:'Bottom'},
  {id:'left', label:'Left'},
  {id:'right', label:'Right'},
  {id:'overlay-top-right', label:'Overlay top'},
  {id:'overlay-bottom-right', label:'Overlay bottom'},
]

export const DEFAULT_CHART_STYLE = {
  version:1,
  presetId:'clean-light',
  backgroundColor:'#FBFAF7',
  seriesColors:{},
  legend:{position:'bottom', format:'symbol-change'},
  lineWidth:4,
  markers:'endpoints',
  gridStrength:'subtle',
}

const HEX_COLOR = /^#[0-9a-f]{6}$/i
const VALID_PRESETS = new Set([...CHART_PRESETS.map(item => item.id), 'custom'])
const VALID_LEGENDS = new Set(LEGEND_POSITIONS.map(item => item.id))
const VALID_FORMATS = new Set(['symbol', 'symbol-change'])
const VALID_WIDTHS = new Set([2, 4, 6])
const VALID_MARKERS = new Set(['none', 'endpoints', 'all'])
const VALID_GRIDS = new Set(['none', 'subtle', 'standard'])

export function normalizeHexColor(value, fallback = '') {
  const color = String(value || '').trim()
  return HEX_COLOR.test(color) ? color.toUpperCase() : fallback
}

function rgb(color) {
  const hex = normalizeHexColor(color, '#000000').slice(1)
  return [0, 2, 4].map(index => parseInt(hex.slice(index, index + 2), 16))
}

function luminance(color) {
  const values = rgb(color).map(value => {
    const channel = value / 255
    return channel <= .03928 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4
  })
  return .2126 * values[0] + .7152 * values[1] + .0722 * values[2]
}

export function contrastRatio(first, second) {
  const high = Math.max(luminance(first), luminance(second))
  const low = Math.min(luminance(first), luminance(second))
  return (high + .05) / (low + .05)
}

export function chartForeground(backgroundColor) {
  return contrastRatio(backgroundColor, '#F7F5EF') >= contrastRatio(backgroundColor, '#1A1D22') ? '#F7F5EF' : '#1A1D22'
}

export function chartGridOpacity(gridStrength) {
  if (gridStrength === 'none') return 0
  return gridStrength === 'standard' ? .28 : .14
}

export function registrySeriesColor(item, index, tokens) {
  const primary = (tokens || []).find(token => token.id === item.tokenId || token.symbol === item.symbol)
  const stableId = String(item.id || item.symbol || index)
  let hash = 0
  for (let position = 0; position < stableId.length; position += 1) hash = ((hash * 31) + stableId.charCodeAt(position)) >>> 0
  return normalizeHexColor(primary?.color, FALLBACK_SERIES_COLORS[hash % FALLBACK_SERIES_COLORS.length])
}

export function resolvedSeriesColor(item, index, tokens, style) {
  return normalizeHexColor(style?.seriesColors?.[item.id], registrySeriesColor(item, index, tokens))
}

export function colorisedChartSeries(data, tokens, style) {
  const used = new Set()
  return (data?.series || []).map((item, index) => {
    const primary = (tokens || []).some(token => token.id === item.tokenId || token.symbol === item.symbol)
    const explicit = normalizeHexColor(style?.seriesColors?.[item.id])
    let color = explicit || registrySeriesColor(item, index, tokens)
    if (!explicit && !primary && used.has(color)) {
      const start = FALLBACK_SERIES_COLORS.indexOf(color)
      for (let offset = 1; offset < FALLBACK_SERIES_COLORS.length; offset += 1) {
        const candidate = FALLBACK_SERIES_COLORS[((start >= 0 ? start : index) + offset) % FALLBACK_SERIES_COLORS.length]
        if (!used.has(candidate)) { color = candidate; break }
      }
    }
    used.add(color)
    return {...item, color}
  })
}

export function presetChartStyle(presetId, theme, data, tokens) {
  const id = VALID_PRESETS.has(presetId) && presetId !== 'custom' ? presetId : 'clean-light'
  const backgroundColor = id === 'brand-dark'
    ? normalizeHexColor(theme?.background, '#080A0C')
    : id === 'high-contrast' ? '#050505' : '#FBFAF7'
  const palette = id === 'colorblind-safe'
    ? COLORBLIND_SERIES_COLORS
    : id === 'high-contrast' ? HIGH_CONTRAST_SERIES_COLORS : null
  const seriesColors = {}
  if (palette) {
    ;(data?.series || []).forEach((item, index) => { seriesColors[item.id] = palette[index % palette.length] })
  }
  return {
    ...DEFAULT_CHART_STYLE,
    presetId:id,
    backgroundColor,
    seriesColors,
  }
}

export function normalizeChartStyle(raw, theme, data, tokens) {
  const base = presetChartStyle(raw?.presetId, theme, data, tokens)
  const colors = {}
  Object.entries(raw?.seriesColors || {}).forEach(([key, value]) => {
    const color = normalizeHexColor(value)
    if (color) colors[key] = color
  })
  const lineWidth = Number(raw?.lineWidth)
  return {
    version:1,
    presetId:VALID_PRESETS.has(raw?.presetId) ? raw.presetId : base.presetId,
    backgroundColor:normalizeHexColor(raw?.backgroundColor, base.backgroundColor),
    seriesColors:{...base.seriesColors, ...colors},
    legend:{
      position:VALID_LEGENDS.has(raw?.legend?.position) ? raw.legend.position : 'bottom',
      format:VALID_FORMATS.has(raw?.legend?.format) ? raw.legend.format : 'symbol-change',
    },
    lineWidth:VALID_WIDTHS.has(lineWidth) ? lineWidth : 4,
    markers:VALID_MARKERS.has(raw?.markers) ? raw.markers : 'endpoints',
    gridStrength:VALID_GRIDS.has(raw?.gridStrength) ? raw.gridStrength : 'subtle',
  }
}

export function materializeCurrentSeriesColors(style, data, tokens) {
  const next = {...style.seriesColors}
  colorisedChartSeries(data, tokens, style).forEach(item => {
    next[item.id] = item.color
  })
  return {...style, seriesColors:next}
}

export function chartStyleIssues(style, series) {
  const colors = (series || []).map(item => normalizeHexColor(item.color)).filter(Boolean)
  const issues = []
  if (new Set(colors).size !== colors.length) issues.push('Every series must use a different color.')
  const lowContrast = (series || []).filter(item => contrastRatio(item.color, style.backgroundColor) < 3)
  if (lowContrast.length) issues.push(`${lowContrast.map(item => item.symbol).join(', ')} need more contrast against the background.`)
  return issues
}

export function chartStyleFingerprint(style) {
  return JSON.stringify({
    version:style.version,
    presetId:style.presetId,
    backgroundColor:style.backgroundColor,
    seriesColors:Object.fromEntries(Object.entries(style.seriesColors || {}).sort(([a], [b]) => a.localeCompare(b))),
    legend:style.legend,
    lineWidth:style.lineWidth,
    markers:style.markers,
    gridStrength:style.gridStrength,
  })
}
