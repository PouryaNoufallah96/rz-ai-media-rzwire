export const OUTPUT_FORMATS = [
  { id:'portrait', label:'Portrait · 1080 × 1350', width:1080, height:1350 },
  { id:'square', label:'Square · 1080 × 1080', width:1080, height:1080 },
  { id:'story', label:'Story · 1080 × 1920', width:1080, height:1920 },
  { id:'landscape', label:'Landscape · 1600 × 900', width:1600, height:900 },
]

const EXTERNAL_COLORS = ['#ef8f7e', '#4f83ff', '#c487e8']

export function compositionSeries(marketData, tokens) {
  let comparisonIndex = 0
  return (marketData?.series || []).map(item => {
    const primary = tokens.find(token => token.symbol === item.symbol)
    return {...item, logo:primary?.logo || '', color:primary?.color || EXTERNAL_COLORS[comparisonIndex++ % EXTERNAL_COLORS.length]}
  })
}

export function analyticsTheme(primaryIds, tokens) {
  const selected = tokens.filter(token => primaryIds.includes(token.id))
  if (selected.length !== 1) return {id:'rzwire', label:'RZWire', footer:'RZWire', logo:'', accent:'#8eb2a5', accent2:'#e78679'}
  const token = selected[0]
  if (token.id === 'mgc') return {id:'mgc', label:'MGC Coin', footer:'metagamescoin.io', logo:token.logo, accent:'#f1ca19', accent2:'#aa8e18'}
  if (token.id === 'oasis') return {id:'oasis', label:'Oasis Coin', footer:'rzoasis.tech', logo:token.logo, accent:'#aeb8b7', accent2:'#37b98b'}
  return {id:'jewelry', label:'Jewelry Coin', footer:'Jewelry.Game', logo:token.logo, accent:'#a78cf3', accent2:'#ded1ff'}
}

export function compositionFingerprint({marketData, period, scale, format, headline, chartText, themeId, templateId}) {
  return JSON.stringify({
    templateId, period, scale, format, headline, chartText, themeId,
    series:(marketData?.series || []).map(item => ({
      id:item.id, symbol:item.symbol, start:item.startPrice, end:item.endPrice, change:item.changePercent,
      points:(item.points || []).map(point => [point.timestamp, point.close]),
    })),
  })
}
