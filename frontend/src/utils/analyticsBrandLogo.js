function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('The official brand logo could not be loaded.'))
    image.src = source
  })
}

const FAMILY_LOGO_PLACEMENTS = {
  phone: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
  laptop: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
  growth: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
  contrast: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
  separated: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
  combined: {bottomRatio:.025, maxWidthRatio:.22, maxHeightRatio:.05},
}

export function resolveAnalyticsLogoLayout({canvasWidth, canvasHeight, logoWidth, logoHeight, categoryId}) {
  const placement = FAMILY_LOGO_PLACEMENTS[categoryId] || FAMILY_LOGO_PLACEMENTS.combined
  const safeLogoWidth = Math.max(1, Number(logoWidth) || 1)
  const safeLogoHeight = Math.max(1, Number(logoHeight) || 1)
  const maxWidth = canvasWidth * placement.maxWidthRatio
  const maxHeight = Math.min(canvasWidth, canvasHeight) * placement.maxHeightRatio
  const scale = Math.min(maxWidth / safeLogoWidth, maxHeight / safeLogoHeight)
  const width = Math.max(1, Math.round(safeLogoWidth * scale))
  const height = Math.max(1, Math.round(safeLogoHeight * scale))
  return {
    x:Math.round((canvasWidth - width) / 2),
    y:Math.round(canvasHeight - (canvasHeight * placement.bottomRatio) - height),
    width,
    height,
  }
}

/**
 * Add the supplied official footer lockup to the family's protected footer rail. The
 * generated composition reserves this rail, while this deterministic pass keeps
 * the exact registry artwork and its original aspect ratio.
 */
export async function applyOfficialAnalyticsLogo(imageDataUrl, {logoUrl, categoryId} = {}) {
  if (!imageDataUrl || !logoUrl || typeof document === 'undefined') return imageDataUrl
  try {
    const [image, logo] = await Promise.all([loadImage(imageDataUrl), loadImage(logoUrl)])
    const canvas = document.createElement('canvas')
    canvas.width = image.naturalWidth || image.width
    canvas.height = image.naturalHeight || image.height
    const context = canvas.getContext('2d')
    if (!context || !canvas.width || !canvas.height) return imageDataUrl

    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const layout = resolveAnalyticsLogoLayout({
      canvasWidth:canvas.width,
      canvasHeight:canvas.height,
      logoWidth:logo.naturalWidth || logo.width,
      logoHeight:logo.naturalHeight || logo.height,
      categoryId,
    })
    context.drawImage(logo, layout.x, layout.y, layout.width, layout.height)
    return canvas.toDataURL('image/png')
  } catch {
    // Logo compositing should never discard an otherwise valid generated post.
    return imageDataUrl
  }
}
