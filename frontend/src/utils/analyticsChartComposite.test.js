import assert from 'node:assert/strict'
import test from 'node:test'

import {
  applyApprovedAnalyticsChart,
  approvedChartPlacementInstruction,
  resolveApprovedChartLayout,
} from './analyticsChartComposite.js'

test('leaves the source unchanged outside a browser canvas', async () => {
  const source = 'data:image/png;base64,source'
  assert.equal(await applyApprovedAnalyticsChart(source, {chartDataUrl:'data:image/png;base64,chart'}), source)
})

test('keeps the complete approved chart inside every protected family slot', () => {
  for (const categoryId of ['phone', 'laptop', 'growth', 'contrast', 'separated', 'combined']) {
    const layout = resolveApprovedChartLayout({canvasWidth:1080, canvasHeight:1350, chartWidth:900, chartHeight:460, categoryId})
    assert.ok(layout.x >= 0)
    assert.ok(layout.y >= 0)
    assert.ok(layout.x + layout.width <= 1080)
    assert.ok(layout.y + layout.height <= 1215, `${categoryId} chart must remain above the protected footer rail`)
    assert.ok(Math.abs((layout.width / layout.height) - (900 / 460)) < .02)
  }
})

test('describes the same protected slot to the image prompt', () => {
  const instruction = approvedChartPlacementInstruction('growth')
  assert.match(instruction, /front-facing chart aperture/)
  assert.match(instruction, /39% from the top/)
  assert.match(instruction, /84% canvas width/)
})
