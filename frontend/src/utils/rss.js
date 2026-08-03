import { API_BASE } from '../store/mmStore'

async function fetchWithTimeout(url, ms = 30000) {
  const ctrl = new AbortController()
  const id = setTimeout(() => ctrl.abort(), ms)
  try {
    const response = await fetch(url, {
      signal: ctrl.signal,
      headers: { Accept: 'application/rss+xml, application/atom+xml, application/xml, text/xml' },
    })
    const text = await response.text()
    return { response, text }
  } finally {
    clearTimeout(id)
  }
}

export async function fetchRSS(url) {
  let response, text
  try {
    const result = await fetchWithTimeout(`${API_BASE}/api/rss?url=${encodeURIComponent(url)}`)
    response = result.response
    text = result.text
  } catch (error) {
    if (error?.name === 'AbortError') throw new Error('News source timed out. Please retry.', { cause: error })
    throw new Error('Cannot reach the RZWire news service. Check that the backend is running.', { cause: error })
  }

  if (!response.ok) {
    let message = `News source returned HTTP ${response.status}.`
    try { message = JSON.parse(text)?.error || message } catch { /* keep HTTP message */ }
    throw new Error(message)
  }

  const sample = text.toLowerCase()
  if (!sample.includes('<item') && !sample.includes('<entry') && !sample.includes('<rss') && !sample.includes('<feed')) {
    throw new Error('Publisher returned a web page instead of an RSS feed.')
  }
  return text
}

function stripHTML(h) {
  const d = document.createElement('div'); d.innerHTML = h
  return (d.textContent || d.innerText || '').replace(/\s+/g,' ').trim()
}

export function parseRSS(xml, src) {
  const doc = new DOMParser().parseFromString(xml, 'application/xml')
  if (doc.querySelector('parsererror')) return []
  const entries = [...doc.querySelectorAll('entry')]
  if (entries.length) return entries.map(el => ({
    title:   el.querySelector('title')?.textContent?.trim() || '',
    desc:    stripHTML(el.querySelector('summary,content')?.textContent || '').slice(0,400),
    link:    el.querySelector('link')?.getAttribute('href') || el.querySelector('link')?.textContent?.trim() || '',
    pubDate: el.querySelector('published,updated')?.textContent?.trim() || '',
    source: src,
  }))
  return [...doc.querySelectorAll('item')].map(el => {
    const lk = el.querySelector('link')
    return {
      title:   el.querySelector('title')?.textContent?.trim() || '',
      desc:    stripHTML(el.querySelector('description')?.textContent || '').slice(0,400),
      link:    lk?.textContent?.trim() || lk?.getAttribute('href') || el.querySelector('guid')?.textContent?.trim() || '',
      pubDate: el.querySelector('pubDate')?.textContent?.trim() || '',
      source: src,
    }
  })
}

export function filterByRecency(arts, h) {
  const cut = Date.now() - h * 3600000
  return arts.filter(a => { if (!a.pubDate) return true; const t = Date.parse(a.pubDate); return isNaN(t) ? true : t >= cut })
}

export function timeAgo(pubDate) {
  if (!pubDate) return 'Recent'
  const d = Date.parse(pubDate)
  if (isNaN(d)) return 'Recent'
  const ageMin = (Date.now() - d) / 60000
  if (ageMin < 60) return `${Math.round(ageMin)}m ago`
  if (ageMin < 1440) return `${Math.round(ageMin/60)}h ago`
  return `${Math.round(ageMin/1440)}d ago`
}
