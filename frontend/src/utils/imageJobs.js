const DEFAULT_POLL_INTERVAL_MS = 2000
const DEFAULT_TIMEOUT_MS = 10 * 60 * 1000
const DEFAULT_MAX_POLL_ERRORS = 5

const wait = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds))

function isConnectionError(error) {
  const message = String(error?.message || '')
  return error?.name === 'TypeError' || /failed to fetch|networkerror|load failed/i.test(message)
}

async function responseJson(response) {
  return response.json().catch(() => ({}))
}

export async function generateImageInBackground({
  apiBase = '',
  payload,
  fetchImpl = fetch,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  maxPollErrors = DEFAULT_MAX_POLL_ERRORS,
  sleepImpl = wait,
  isCancelled = () => false,
}) {
  let startResponse
  try {
    startResponse = await fetchImpl(`${apiBase}/api/image/generate-async`, {
      method:'POST',
      credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(payload),
    })
  } catch (error) {
    if (isConnectionError(error)) {
      throw new Error('The connection was interrupted while starting image generation. Please try again.', {cause:error})
    }
    throw error
  }

  const started = await responseJson(startResponse)
  if (!startResponse.ok || !started.jobId) {
    throw new Error(started.error || 'Image generation could not be started.')
  }

  const deadline = Date.now() + timeoutMs
  let pollErrors = 0
  while (Date.now() < deadline) {
    await sleepImpl(pollIntervalMs)
    if (isCancelled()) return null

    try {
      const statusResponse = await fetchImpl(
        `${apiBase}/api/image/generation-status?jobId=${encodeURIComponent(started.jobId)}`,
        {credentials:'include'},
      )
      const job = await responseJson(statusResponse)
      if (!statusResponse.ok) {
        throw new Error(job.error || 'Image generation progress could not be checked.')
      }

      pollErrors = 0
      if (job.status === 'failed') throw new Error(job.error || 'Image generation failed.')
      if (job.status === 'complete') return job.result || {}
      if (job.status !== 'queued' && job.status !== 'running') {
        throw new Error('Image generation returned an unknown progress state.')
      }
    } catch (error) {
      // The detached job is still running. Temporary browser/network failures
      // should not discard an image that the backend may already have finished.
      if (!isConnectionError(error)) throw error
      pollErrors += 1
      if (pollErrors > maxPollErrors) {
        throw new Error('The connection was interrupted while checking image progress. Please try again.', {cause:error})
      }
    }
  }

  throw new Error('Image generation is taking longer than expected. Please try again.')
}
