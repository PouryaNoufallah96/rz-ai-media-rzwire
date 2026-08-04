function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('The approved style sample could not be loaded.'))
    image.src = source
  })
}

export function styleReferenceDimensions(width, height, maxEdge = 96) {
  const safeWidth = Math.max(1, Number(width) || 1)
  const safeHeight = Math.max(1, Number(height) || 1)
  const scale = Math.min(1, maxEdge / Math.max(safeWidth, safeHeight))
  return {
    width:Math.max(1, Math.round(safeWidth * scale)),
    height:Math.max(1, Math.round(safeHeight * scale)),
  }
}

/**
 * Convert the approved publishing sample into a deliberately low-resolution
 * style map. Composition, palette, spacing, and silhouettes remain visible,
 * while sample tickers, prices, percentages, dates, legends, and chart data
 * become unreadable and therefore cannot be reused as market facts.
 */
export async function createAnalyticsStyleReference(imageDataUrl) {
  if (!imageDataUrl || typeof document === 'undefined') {
    throw new Error('The approved sample could not be converted into a style-only reference.')
  }
  const image = await loadImage(imageDataUrl)
  const dimensions = styleReferenceDimensions(image.naturalWidth || image.width, image.naturalHeight || image.height)
  const canvas = document.createElement('canvas')
  canvas.width = dimensions.width
  canvas.height = dimensions.height
  const context = canvas.getContext('2d')
  if (!context) throw new Error('The approved sample could not be sanitized for generation.')
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(image, 0, 0, canvas.width, canvas.height)
  return canvas.toDataURL('image/png')
}
