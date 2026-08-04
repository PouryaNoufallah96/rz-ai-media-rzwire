function loadImage(source) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('The official brand logo could not be loaded.'))
    image.src = source
  })
}

/**
 * Add the supplied official mark in the reserved lower-left safe zone.
 * The image model is explicitly told to leave this area clear, so the final
 * exported PNG contains the exact registry asset rather than a generated logo.
 */
export async function applyOfficialAnalyticsLogo(imageDataUrl, {logoUrl, sizeRatio = .09} = {}) {
  if (!imageDataUrl || !logoUrl || typeof document === 'undefined') return imageDataUrl
  try {
    const [image, logo] = await Promise.all([loadImage(imageDataUrl), loadImage(logoUrl)])
    const canvas = document.createElement('canvas')
    canvas.width = image.naturalWidth || image.width
    canvas.height = image.naturalHeight || image.height
    const context = canvas.getContext('2d')
    if (!context || !canvas.width || !canvas.height) return imageDataUrl

    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const size = Math.max(48, Math.round(Math.min(canvas.width, canvas.height) * sizeRatio))
    const x = Math.round(canvas.width * .07)
    const y = canvas.height - size - Math.round(canvas.height * .065)
    context.drawImage(logo, x, y, size, size)
    return canvas.toDataURL('image/png')
  } catch {
    // Logo compositing should never discard an otherwise valid generated post.
    return imageDataUrl
  }
}
