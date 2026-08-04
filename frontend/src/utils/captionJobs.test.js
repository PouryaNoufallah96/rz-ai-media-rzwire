import assert from 'node:assert/strict'
import test from 'node:test'

import { generateCaptionsInBackground } from './captionJobs.js'

const jsonResponse = (body, ok = true) => ({ok, json:async () => body})
const noWait = async () => {}

test('returns three completed captions through the async job contract', async () => {
  const calls = []
  const variants = [{copy:'One'}, {copy:'Two'}, {copy:'Three'}]
  const responses = [
    jsonResponse({jobId:'copy-123', status:'queued'}),
    jsonResponse({jobId:'copy-123', status:'running'}),
    jsonResponse({jobId:'copy-123', status:'complete', result:{variants}}),
  ]
  const result = await generateCaptionsInBackground({
    apiBase:'https://rzwire.test',
    payload:{variantCount:3},
    fetchImpl:async (url, options) => {
      calls.push({url, options})
      return responses.shift()
    },
    sleepImpl:noWait,
  })

  assert.deepEqual(result.variants, variants)
  assert.equal(calls[0].url, 'https://rzwire.test/api/copy/generate-async')
  assert.equal(calls[0].options.credentials, 'include')
  assert.match(calls[1].url, /copy\/generation-status\?jobId=copy-123$/)
})

test('retries a temporary polling disconnect without starting another job', async () => {
  let call = 0
  const result = await generateCaptionsInBackground({
    payload:{},
    fetchImpl:async () => {
      call += 1
      if (call === 1) return jsonResponse({jobId:'copy-456', status:'queued'})
      if (call === 2) throw new TypeError('Failed to fetch')
      return jsonResponse({jobId:'copy-456', status:'complete', result:{variants:[1, 2, 3]}})
    },
    sleepImpl:noWait,
  })

  assert.deepEqual(result.variants, [1, 2, 3])
  assert.equal(call, 3)
})

test('surfaces a backend caption-job error', async () => {
  const responses = [
    jsonResponse({jobId:'copy-789', status:'queued'}),
    jsonResponse({jobId:'copy-789', status:'failed', error:'provider unavailable'}),
  ]

  await assert.rejects(
    generateCaptionsInBackground({payload:{}, fetchImpl:async () => responses.shift(), sleepImpl:noWait}),
    /provider unavailable/,
  )
})
