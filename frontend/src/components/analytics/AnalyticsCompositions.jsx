import { forwardRef } from 'react'
import { OUTPUT_FORMATS, analyticsTheme, compositionSeries } from './analyticsCompositionConfig'

function formatPrice(value) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return 'Unavailable'
  const digits = amount < 1 ? 6 : amount < 100 ? 4 : 2
  return amount.toLocaleString('en-US', {style:'currency', currency:'USD', maximumFractionDigits:digits})
}

function shortDate(timestamp) {
  return new Date(Number(timestamp) * 1000).toLocaleDateString('en-US', {month:'short', day:'numeric'})
}

function percentValues(points) {
  if (!points?.length) return []
  const start = Number(points[0].close) || 1
  return points.map(point => ((Number(point.close) - start) / start) * 100)
}

function valuesFor(item, scale) {
  return scale === 'absolute' ? item.points.map(point => Number(point.close)) : percentValues(item.points)
}

function chartGeometry(series, scale, width=620, height=220, padding={left:28,right:18,top:22,bottom:34}) {
  const valueSets = series.map(item => valuesFor(item, scale))
  const all = valueSets.flat().filter(Number.isFinite)
  if (scale === 'relative') all.push(0)
  const rawMin = Math.min(...all)
  const rawMax = Math.max(...all)
  const extra = Math.max(scale === 'relative' ? 1 : Math.abs(rawMax || 1) * .02, (rawMax - rawMin) * .08)
  const min = rawMin - extra
  const max = rawMax + extra
  const timestamps = series.flatMap(item => item.points.map(point => Number(point.timestamp))).filter(Number.isFinite)
  const first = Math.min(...timestamps)
  const last = Math.max(...timestamps)
  const x = timestamp => padding.left + ((Number(timestamp) - first) / Math.max(1, last - first)) * (width - padding.left - padding.right)
  const y = value => height - padding.bottom - ((value - min) / Math.max(.000001, max - min)) * (height - padding.top - padding.bottom)
  return {valueSets, min, max, first, last, x, y, width, height, padding}
}

function marketTick(value, scale) {
  if (scale === 'relative') return `${value >= 0 ? '+' : ''}${value.toFixed(0)}%`
  if (Math.abs(value) >= 1000) return `$${(value / 1000).toFixed(1)}k`
  if (Math.abs(value) >= 1) return `$${value.toFixed(2)}`
  return `$${value.toFixed(4)}`
}

function MarketChart({series, scale='relative', compact=false, dark=true, showDates=true, showValues=true}) {
  const g = chartGeometry(series, scale, 620, compact ? 150 : 230, {left:28,right:18,top:18,bottom:showDates ? 34 : 12})
  const ticks = Array.from({length:compact ? 3 : 4}, (_, index) => g.min + index * ((g.max - g.min) / (compact ? 2 : 3)))
  const dates = Array.from({length:5}, (_, index) => g.first + index * ((g.last - g.first) / 4))
  return <svg className={`rz-composition-chart ${dark ? 'dark' : 'light'}`} viewBox={`0 0 ${g.width} ${g.height}`} role="img" aria-label={`${series.map(item => item.symbol).join(', ')} verified market chart`}>
    {ticks.map((tick, index) => <g key={index}><line x1={g.padding.left} x2={g.width-g.padding.right} y1={g.y(tick)} y2={g.y(tick)} />{showValues && <text className="rz-chart-value" x={g.width-g.padding.right} y={g.y(tick)-4} textAnchor="end">{marketTick(tick, scale)}</text>}</g>)}
    {series.map((item, index) => <polyline key={item.id} style={{stroke:item.color}} points={item.points.map((point, pointIndex) => `${g.x(point.timestamp).toFixed(1)},${g.y(g.valueSets[index][pointIndex]).toFixed(1)}`).join(' ')} />)}
    {showDates && dates.map((date, index) => <text key={index} x={g.x(date)} y={g.height-8} textAnchor="middle">{shortDate(date)}</text>)}
  </svg>
}

function TokenBadge({item, detailed=false}) {
  return <span className="rz-token-badge" style={{'--series':item.color}}>
    {item.logo ? <img src={item.logo} alt="" /> : <i>{item.symbol.slice(0, 1)}</i>}
    <b>{item.symbol}</b>
    {detailed && <em>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</em>}
  </span>
}

function BrandFooter({theme, series}) {
  return <footer className="rz-composition-footer">
    <span>{theme.logo ? <img src={theme.logo} alt="" /> : <b>RZWire</b>}</span>
    <span>{series.map(item => item.symbol).join(' · ')}</span>
    <strong>{theme.footer}</strong>
  </footer>
}

function RangeTabs({period}) {
  const periods = ['1h', '24h', '7d', '30d', '90d', '1y']
  return <div className="rz-range-tabs">
    {periods.map(item => item === period ? <b key={item}>{item}</b> : <span key={item}>{item}</span>)}
  </div>
}

function PhoneView({series, period, scale}) {
  return <div className="rz-phone-shell">
    <div className="rz-phone-speaker" />
    <div className="rz-phone-screen">
      <div className="rz-market-brand"><b>CoinMarketCap</b><span>Compare</span></div>
      <div className="rz-phone-assets">{series.map(item => <TokenBadge key={item.id} item={item} />)}</div>
      <RangeTabs period={period} />
      <MarketChart series={series} scale={scale} compact />
      <div className="rz-legend">{series.map(item => <TokenBadge key={item.id} item={item} detailed />)}</div>
      <div className="rz-market-controls"><b>Price</b><span>Market Cap</span><span>Volume</span></div>
      <h4>Market Stats</h4>
      <div className="rz-stat-table">
        <span>Asset</span><b>Price</b><b>Change</b>
        {series.map(item => <span className="row" key={item.id}><TokenBadge item={item} /><b>{formatPrice(item.endPrice)}</b><em className={item.changePercent >= 0 ? 'up' : 'down'}>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</em></span>)}
      </div>
    </div>
  </div>
}

function DesktopView({series, period, scale, neutral}) {
  const compact = series.length > 3
  return <div className={`rz-laptop-shell ${compact ? 'is-dense' : ''}`}>
    <div className="rz-laptop-lid">
      <div className="rz-laptop-camera" />
      <div className="rz-laptop-screen">
        <div className="rz-desktop-top">
          <b>{neutral ? 'RZWire Market' : 'CoinMarketCap'}</b>
          <span>Cryptocurrencies</span><span>Markets</span><span>Community</span>
          <i>Search assets</i><i className="rz-desktop-avatar" />
        </div>
        <div className="rz-desktop-asset-strip" style={{'--asset-count':series.length}}>
          {series.map(item => <article key={item.id}><TokenBadge item={item} /><b>{formatPrice(item.endPrice)}</b><em className={item.changePercent >= 0 ? 'up' : 'down'}>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</em></article>)}
        </div>
        <main className="rz-desktop-market-card">
          <div className="rz-desktop-chart-head"><div><small>Verified comparison</small><b>{series.map(item => item.symbol).join(' · ')}</b></div><span>{period}</span><span>{scale === 'relative' ? 'Relative performance' : 'USD price'}</span></div>
          <RangeTabs period={period} />
          <MarketChart series={series} scale={scale} dark compact={compact} />
          <div className="rz-legend">{series.map(item => <TokenBadge key={item.id} item={item} detailed />)}</div>
        </main>
        <div className="rz-desktop-bottom-row">
          <div><small>Market range</small><b>{shortDate(Math.min(...series.flatMap(item => item.points.map(point => point.timestamp))))} – {shortDate(Math.max(...series.flatMap(item => item.points.map(point => point.timestamp))))}</b></div>
          <div><small>Data integrity</small><b>Verified histories</b></div>
          <div><small>Series</small><b>{series.length} assets</b></div>
        </div>
      </div>
    </div>
    <div className="rz-laptop-deck"><i /></div>
  </div>
}

function GrowthView({series, scale}) {
  const lead = [...series].sort((a,b) => b.changePercent-a.changePercent)[0]
  return <div className="rz-growth-view">
    <div><p>{lead.symbol} moved from</p><h3>{formatPrice(lead.startPrice)} <span>to</span> {formatPrice(lead.endPrice)}</h3><b className={lead.changePercent >= 0 ? 'up' : 'down'}>{lead.changePercent >= 0 ? '+' : ''}{lead.changePercent.toFixed(2)}% over the selected period</b></div>
    <div className="rz-growth-chart"><TokenBadge item={lead} detailed /><MarketChart series={[lead]} scale={scale} dark compact={false} /></div>
  </div>
}

function ContrastView({series, scale}) {
  const ordered = [...series].sort((a,b) => b.changePercent-a.changePercent)
  const winner = ordered[0]
  const loser = ordered[ordered.length-1]
  return <div className="rz-contrast-view">
    <h3>{winner.symbol} led. {winner.id === loser.id ? 'A focused market story.' : `${loser.symbol} trailed.`}</h3>
    <div className="rz-contrast-cards">{ordered.map(item => <article key={item.id} className={item.changePercent >= 0 ? 'positive' : 'negative'}><TokenBadge item={item} /><b>{formatPrice(item.endPrice)}</b><em>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</em><MarketChart series={[item]} scale={scale} dark compact showDates={false} /></article>)}</div>
  </div>
}

function SeparatedCards({series, scale}) {
  return <div className="rz-separated-grid">{series.map(item => <article key={item.id}><TokenBadge item={item} /><MarketChart series={[item]} scale={scale} dark compact showDates={false} /><dl><dt>Start</dt><dd>{formatPrice(item.startPrice)}</dd><dt>End</dt><dd>{formatPrice(item.endPrice)}</dd><dt>Move</dt><dd className={item.changePercent >= 0 ? 'up' : 'down'}>{item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%</dd></dl></article>)}</div>
}

function CombinedView({series, scale}) {
  const ordered = [...series].sort((a,b) => b.changePercent-a.changePercent)
  const headline = ordered[0].changePercent < 0 ? 'Markets moved lower together.' : ordered.at(-1).changePercent >= 0 ? `${ordered[0].symbol} led a broad advance.` : `${ordered[0].symbol} rose while ${ordered.at(-1).symbol} fell.`
  return <div className="rz-combined-view"><h3>{headline}</h3><div className="rz-combined-chart"><div className="rz-legend">{series.map(item => <TokenBadge key={item.id} item={item} detailed />)}</div><MarketChart series={series} scale={scale} dark /></div></div>
}

function StaticFrameStage({templateId, series, period}) {
  const marks = <div className="rz-frame-corners" aria-hidden="true"><i /><i /><i /><i /></div>
  if (templateId === 'phone') return <div className="rz-static-phone"><div className="rz-static-phone-notch" /><div className="rz-frame-aperture">{marks}</div><div className="rz-static-frame-meta"><span>{period}</span><span>{series.length} verified {series.length === 1 ? 'asset' : 'assets'}</span></div></div>
  if (templateId === 'laptop') return <div className="rz-static-laptop"><div className="rz-static-laptop-lid"><div className="rz-static-laptop-camera" /><div className="rz-frame-aperture">{marks}</div></div><div className="rz-static-laptop-deck"><i /></div></div>
  if (templateId === 'growth') return <div className="rz-static-growth"><div className="rz-static-growth-copy"><span>VERIFIED PERFORMANCE</span><b>{series[0]?.symbol}</b><i /></div><div className="rz-frame-aperture">{marks}</div></div>
  if (templateId === 'contrast') return <div className="rz-static-contrast"><div className="rz-static-contrast-labels"><i /><i /></div><div className="rz-frame-aperture">{marks}</div></div>
  if (templateId === 'separated') return <div className="rz-static-separated"><div className="rz-frame-aperture">{marks}</div><div className="rz-static-stat-slots">{series.slice(0, 6).map(item => <i key={item.id} style={{'--series':item.color}} />)}</div></div>
  return <div className="rz-static-combined"><div className="rz-static-combined-orbit" /><div className="rz-frame-aperture">{marks}</div></div>
}

const CompositionPreview = forwardRef(function CompositionPreview({marketData, templateId, headline, chartText, period, format, theme, tokens, primaryIds=[], frameOnly=false}, ref) {
  const series = compositionSeries(marketData, tokens)
  const output = OUTPUT_FORMATS.find(item => item.id === format) || OUTPUT_FORMATS[0]
  const primaryCount = series.filter(item => item.role === 'primary').length
  const resolvedTheme = theme || analyticsTheme(primaryIds, tokens)
  return <article ref={ref} className={`rz-composition rz-composition--${templateId} rz-composition--${resolvedTheme.id} rz-composition--${format} ${frameOnly ? 'rz-composition--frame' : ''}`} style={{'--ratio':`${output.width}/${output.height}`, '--accent':resolvedTheme.accent, '--accent-2':resolvedTheme.accent2}}>
    <div className="rz-composition-atmosphere" />
    <div className="rz-composition-content">
      <header className="rz-composition-header"><small>{period} verified market view</small><h2>{headline}</h2><p>{chartText}</p></header>
      <div className="rz-composition-stage">
        {frameOnly ? <StaticFrameStage templateId={templateId} series={series} period={period} /> : <>
          {templateId === 'phone' && <PhoneView series={series} period={period} scale={marketData.scale} />}
          {templateId === 'laptop' && <DesktopView series={series} period={period} scale={marketData.scale} neutral={primaryCount !== 1} />}
          {templateId === 'growth' && <GrowthView series={series} scale={marketData.scale} />}
          {templateId === 'contrast' && <ContrastView series={series} scale={marketData.scale} />}
          {templateId === 'separated' && <SeparatedCards series={series} scale={marketData.scale} />}
          {templateId === 'combined' && <CombinedView series={series} scale={marketData.scale} />}
        </>}
      </div>
      <BrandFooter theme={resolvedTheme} series={series} />
    </div>
  </article>
})

export default CompositionPreview
