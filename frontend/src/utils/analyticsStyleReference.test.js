import assert from 'node:assert/strict'
import test from 'node:test'

import { styleReferenceDimensions } from './analyticsStyleReference.js'

test('reduces every publishing sample to a non-readable style map', () => {
  assert.deepEqual(styleReferenceDimensions(1080, 1350), {width:77, height:96})
  assert.deepEqual(styleReferenceDimensions(1080, 1080), {width:96, height:96})
  assert.deepEqual(styleReferenceDimensions(1600, 900), {width:96, height:54})
})

test('preserves the sample aspect ratio closely', () => {
  const dimensions = styleReferenceDimensions(1080, 1920)
  assert.ok(Math.abs((dimensions.width / dimensions.height) - (1080 / 1920)) < .01)
})
