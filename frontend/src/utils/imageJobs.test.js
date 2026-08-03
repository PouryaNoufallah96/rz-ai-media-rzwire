import assert from 'node:assert/strict'
import test from 'node:test'

import { generateImageInBackground } from './imageJobs.js'

const jsonResponse = (body, ok = true) => ({ok, json:async () => body})
const noWait = async () => {}

test('returns the completed image result through the async job contract', async () => {
  const calls = []
  const responses = [
    jsonResponse({jobId:'job-123', status:'queued'}),
    jsonResponse({jobId:'job-123', status:'running'}),
    jsonResponse({jobId:'job-123', status:'complete', result:{imageB64:'abc123'}}),
  ]
  const fetchImpl = async (url, options) => {
    calls.push({url, options})
    return responses.shift()
  }

  const result = await generateImageInBackground({
    apiBase:'https://rzwire.test',
    payload:{model:'google/gemini-3-pro-image-preview'},
    fetchImpl,
    sleepImpl:noWait,
  })

  assert.equal(result.imageB64, 'abc123')
  assert.equal(calls[0].url, 'https://rzwire.test/api/image/generate-async')
  assert.equal(calls[0].options.credentials, 'include')
  assert.match(calls[1].url, /generation-status\?jobId=job-123$/)
})

test('retries temporary polling disconnects without starting a second job', async () => {
  let call = 0
  const fetchImpl = async () => {
    call += 1
    if (call === 1) return jsonResponse({jobId:'job-456', status:'queued'})
    if (call === 2) throw new TypeError('Failed to fetch')
    return jsonResponse({jobId:'job-456', status:'complete', result:{imageB64:'finished'}})
  }

  const result = await generateImageInBackground({
    payload:{},
    fetchImpl,
    sleepImpl:noWait,
  })

  assert.equal(result.imageB64, 'finished')
  assert.equal(call, 3)
})

test('surfaces the backend job error', async () => {
  const responses = [
    jsonResponse({jobId:'job-789', status:'queued'}),
    jsonResponse({jobId:'job-789', status:'failed', error:'provider unavailable'}),
  ]

  await assert.rejects(
    generateImageInBackground({payload:{}, fetchImpl:async () => responses.shift(), sleepImpl:noWait}),
    /provider unavailable/,
  )
})
