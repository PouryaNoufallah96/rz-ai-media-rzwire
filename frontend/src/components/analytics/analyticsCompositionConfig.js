export const OUTPUT_FORMATS = [
  { id:'portrait', label:'Portrait · 1080 × 1350', width:1080, height:1350 },
  { id:'square', label:'Square · 1080 × 1080', width:1080, height:1080 },
  { id:'story', label:'Story · 1080 × 1920', width:1080, height:1920 },
  { id:'landscape', label:'Landscape · 1600 × 900', width:1600, height:900 },
]

export const EXTERNAL_COLORS = ['#c9877f', '#3978c7', '#b878cf']

export function compositionSeries(marketData, tokens) {
  let comparisonIndex = 0
  return (marketData?.series || []).map(item => {
    const primary = tokens.find(token => token.id === item.tokenId || token.symbol === item.symbol)
    return {...item, logo:primary?.logo || '', color:primary?.color || EXTERNAL_COLORS[comparisonIndex++ % EXTERNAL_COLORS.length]}
  })
}

export function analyticsTheme(themeOwnerTokenId, tokens) {
  const token = tokens.find(item => item.id === themeOwnerTokenId)
  if (!token) return null
  const palette = token.theme || {}
  return {
    id:token.id,
    label:token.name,
    footer:token.footer,
    domain:token.domain,
    logo:token.logo,
    accent:palette.accent || token.color,
    accent2:palette.accentAlt || token.color,
    background:palette.background || '#080a0c',
    backgroundAlt:palette.backgroundAlt || '#20252a',
    surface:palette.surface || '#12161b',
    surfaceAlt:palette.surfaceAlt || '#1b2128',
    text:palette.text || '#f7f5ef',
    muted:palette.muted || '#9ca2a8',
    positive:palette.positive || '#25c58a',
    negative:palette.negative || '#e06361',
    border:palette.border || '#3d454d',
    motifs:token.motifs || [],
  }
}

export function compositionFingerprint({marketData, period, scale, format, headline, chartText, themeOwnerTokenId, templateCategoryId, templateVariantId, direction}) {
  return JSON.stringify({
    templateCategoryId, templateVariantId, themeOwnerTokenId, period, scale, format, headline, chartText, direction,
    series:(marketData?.series || []).map(item => ({
      id:item.id, tokenId:item.tokenId, symbol:item.symbol, start:item.startPrice, end:item.endPrice, change:item.changePercent,
      points:(item.points || []).map(point => [point.timestamp, point.close]),
    })),
  })
}
