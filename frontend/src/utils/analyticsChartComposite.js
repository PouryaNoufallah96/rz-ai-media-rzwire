function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('The approved Analytics chart could not be loaded.'))
    image.src = source
  })
}

// These protected slots match the chart aperture requested from the image model.
// The chart is always drawn as a flat, front-facing asset so no model can alter its
// dates, values, axes, legend, line geometry, or colors.
const FAMILY_CHART_SLOTS = {
  phone: {centerX:.5, top:.33, maxWidth:.52, maxHeight:.31},
  laptop: {centerX:.5, top:.31, maxWidth:.72, maxHeight:.34},
  growth: {centerX:.5, top:.39, maxWidth:.84, maxHeight:.37},
  contrast: {centerX:.5, top:.35, maxWidth:.84, maxHeight:.39},
  separated: {centerX:.5, top:.37, maxWidth:.84, maxHeight:.38},
  combined: {centerX:.5, top:.34, maxWidth:.84, maxHeight:.43},
}

export function resolveApprovedChartLayout({canvasWidth, canvasHeight, chartWidth, chartHeight, categoryId}) {
  const slot = FAMILY_CHART_SLOTS[categoryId] || FAMILY_CHART_SLOTS.combined
  const safeChartWidth = Math.max(1, Number(chartWidth) || 1)
  const safeChartHeight = Math.max(1, Number(chartHeight) || 1)
  const maxWidth = canvasWidth * slot.maxWidth
  const maxHeight = canvasHeight * slot.maxHeight
  const scale = Math.min(maxWidth / safeChartWidth, maxHeight / safeChartHeight)
  const width = Math.max(1, Math.round(safeChartWidth * scale))
  const height = Math.max(1, Math.round(safeChartHeight * scale))
  return {
    x:Math.round((canvasWidth * slot.centerX) - (width / 2)),
    y:Math.round(canvasHeight * slot.top),
    width,
    height,
  }
}

export function approvedChartPlacementInstruction(categoryId) {
  const slot = FAMILY_CHART_SLOTS[categoryId] || FAMILY_CHART_SLOTS.combined
  const left = Math.round((slot.centerX - (slot.maxWidth / 2)) * 100)
  return `Reserve one flat, front-facing chart aperture beginning about ${left}% from the left and ${Math.round(slot.top * 100)}% from the top, with up to ${Math.round(slot.maxWidth * 100)}% canvas width and ${Math.round(slot.maxHeight * 100)}% canvas height.`
}

/**
 * Place the exact user-approved chart over the generated art. This final pass is
 * deliberately deterministic: the style sample and image model never provide the
 * pixels used for the visible market chart.
 */
export async function applyApprovedAnalyticsChart(imageDataUrl, {chartDataUrl, categoryId} = {}) {
  if (!imageDataUrl || !chartDataUrl || typeof document === 'undefined') return imageDataUrl
  const [image, chart] = await Promise.all([loadImage(imageDataUrl), loadImage(chartDataUrl)])
  const canvas = document.createElement('canvas')
  canvas.width = image.naturalWidth || image.width
  canvas.height = image.naturalHeight || image.height
  const context = canvas.getContext('2d')
  if (!context || !canvas.width || !canvas.height) throw new Error('The approved Analytics chart could not be composited.')

  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  const layout = resolveApprovedChartLayout({
    canvasWidth:canvas.width,
    canvasHeight:canvas.height,
    chartWidth:chart.naturalWidth || chart.width,
    chartHeight:chart.naturalHeight || chart.height,
    categoryId,
  })
  const border = Math.max(1, Math.round(Math.min(canvas.width, canvas.height) * .0015))
  context.fillStyle = 'rgba(5, 7, 10, .96)'
  context.fillRect(layout.x - border, layout.y - border, layout.width + (border * 2), layout.height + (border * 2))
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(chart, layout.x, layout.y, layout.width, layout.height)
  return canvas.toDataURL('image/png')
}
