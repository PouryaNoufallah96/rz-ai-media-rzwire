import assert from 'node:assert/strict'
import test from 'node:test'

import { applyOfficialAnalyticsLogo, resolveAnalyticsLogoLayout } from './analyticsBrandLogo.js'

test('leaves the source unchanged outside a browser canvas', async () => {
  const source = 'data:image/png;base64,source'
  assert.equal(await applyOfficialAnalyticsLogo(source, {logoUrl:'/brands/mgc-coin-logo.png'}), source)
})

test('keeps every family logo inside the protected lower footer rail', () => {
  for (const categoryId of ['phone', 'laptop', 'growth', 'contrast', 'separated', 'combined']) {
    const layout = resolveAnalyticsLogoLayout({canvasWidth:1080, canvasHeight:1350, logoWidth:640, logoHeight:640, categoryId})
    assert.ok(layout.y >= 1180, `${categoryId} logo must remain in the bottom footer rail`)
    assert.ok(layout.x + layout.width < 216, `${categoryId} logo must remain in the left logo slot`)
    assert.ok(layout.y + layout.height <= 1350)
  }
})

test('preserves the official logo aspect ratio instead of forcing a square', () => {
  const layout = resolveAnalyticsLogoLayout({canvasWidth:1080, canvasHeight:1350, logoWidth:232, logoHeight:192, categoryId:'growth'})
  assert.ok(Math.abs((layout.width / layout.height) - (232 / 192)) < .02)
})
