import assert from 'node:assert/strict'
import test from 'node:test'

import { applyOfficialAnalyticsLogo } from './analyticsBrandLogo.js'

test('leaves the source unchanged outside a browser canvas', async () => {
  const source = 'data:image/png;base64,source'
  assert.equal(await applyOfficialAnalyticsLogo(source, {logoUrl:'/brands/mgc-coin-logo.png'}), source)
})
