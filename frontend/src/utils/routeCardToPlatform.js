import { API_BASE } from '../store/mmStore'
import { useLanguageStore } from '../store/languageStore'

const PLAT_REASONS = {
  X:         '≤ 280 chars · punchy hook · 2–3 hashtags',
  Telegram:  'Full context · 2–4 paragraphs · brand-voice',
  Instagram: 'Strong opening hook · 5–10 hashtags',
}

async function translatePreviewFields(card, language) {
  if (language !== 'fa') return {}
  if (card._sourceTranslated) {
    return {
      headline:card.headline,
      mediaReason:card.mediaReason,
      selectionReason:card.selectionReason,
      _previewTranslated:true,
    }
  }
  try {
    const reason = card.mediaReason || card.selectionReason || ''
    const response = await fetch(`${API_BASE}/api/translate/cards`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ language:'fa', articles:[{ title:card.headline || '', desc:reason }] }),
    })
    const data = await response.json().catch(() => ({}))
    const translated = response.ok && Array.isArray(data.articles) ? data.articles[0] : null
    if (!translated) return {}
    return {
      headline:translated.title || card.headline,
      mediaReason:translated.desc || reason,
      selectionReason:translated.desc || reason,
      _previewTranslated:true,
    }
  } catch (_) {
    return {}
  }
}

export async function generatePlatformCopy(card, platform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy, promoMode }) {
  const isPromo = card._isPromo || promoMode
  const modelKey = card._modelKey || 'gpt'
  const language = useLanguageStore.getState().language
  const cacheMode = `${isPromo ? 'promo' : 'editorial'}:${language}`
  const cached = getCachedCopy(card.id, platform, modelKey, cacheMode)
  if (cached) { updatePlatformCard(card.id, platform, { ...cached, isGenerating: false }); return }

  try {
    const desc = card._isPromo ? (card._promoPrompt || card.copy) : card.copy
    const previewFieldsPromise = translatePreviewFields(card, language)
    const body = { article:{title:card.headline,source:card.source,desc,matchedKeywords:card.matchedKeywords||card.hashtags||[]}, platform, mediaBrand:card.media, sentiment:card.sentiment||'Neutral', modelKey, language }
    if (siblingCopy) body.siblingCopy = siblingCopy
    if (isPromo) body.promoMode = true
    const r = await fetch(`${API_BASE}/api/copy/generate`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)
    })
    if (!r.ok) { updatePlatformCard(card.id, platform, { isGenerating: false }); return }
    const result = await r.json()
    const previewFields = await previewFieldsPromise
    const payload = {
      ...previewFields,
      copy: result.copy || card.copy,
      hashtags: result.hashtags?.length ? result.hashtags : card.hashtags,
      charCount: platform === 'X' ? (result.copy || '').length : null,
      variants: result.variants || null,
      platReason: PLAT_REASONS[platform] || `Formatted for ${platform}`,
      isGenerating: false,
    }
    setCachedCopy(card.id, platform, modelKey, payload, cacheMode)
    updatePlatformCard(card.id, platform, payload)
  } catch (e) {
    console.warn('Platform copy failed:', e.message)
    updatePlatformCard(card.id, platform, { isGenerating: false })
  }
}

export function routeCardToPlatform(cardId, targetPlatform, targetBrand, storeBag) {
  const { modelLanes, telegramLanes, platformLanes, setPlatformLanes, updatePlatformCard, getCachedCopy, setCachedCopy, setActiveCard, promoMode } = storeBag
  if ((platformLanes[targetBrand]?.[targetPlatform] || []).some(c => c.id === cardId)) return   // already routed here — no-op

  let siblingCopy = null
  if (targetPlatform !== 'X') {
    const xCard = (platformLanes[targetBrand]?.X || []).find(c => c.id === cardId)
    if (xCard) siblingCopy = xCard.copy
  }

  // Look for the card in model lanes first — those are cloned (card stays put)
  for (const mk of Object.keys(modelLanes)) {
    for (const brand of Object.keys(modelLanes[mk])) {
      const found = modelLanes[mk][brand].find(c => c.id === cardId)
      if (found) {
        const routed = { ...found, platform: targetPlatform, media: brand, isGenerating: true, genStartedAt: Date.now() }
        const newPl = JSON.parse(JSON.stringify(platformLanes))
        if (!newPl[brand]) newPl[brand] = {}
        if (!newPl[brand][targetPlatform]) newPl[brand][targetPlatform] = []
        newPl[brand][targetPlatform].push(routed)
        setPlatformLanes(newPl)
        setActiveCard(routed)
        generatePlatformCopy(routed, targetPlatform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy, promoMode: promoMode?.[brand] || false })
        return
      }
    }
  }

  // Otherwise the card is already in a platform lane — move it (remove from old lane)
  for (const brand of Object.keys(telegramLanes || {})) {
    const found = (telegramLanes[brand] || []).find(c => c.id === cardId)
    if (found) {
      const routed = { ...found, platform: targetPlatform, media: brand, isGenerating: true, genStartedAt: Date.now() }
      const newPl = JSON.parse(JSON.stringify(platformLanes))
      if (!newPl[brand]) newPl[brand] = {}
      if (!newPl[brand][targetPlatform]) newPl[brand][targetPlatform] = []
      newPl[brand][targetPlatform].push(routed)
      setPlatformLanes(newPl)
      setActiveCard(routed)
      generatePlatformCopy(routed, targetPlatform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy, promoMode: promoMode?.[brand] || false })
      return
    }
  }

  const pl = JSON.parse(JSON.stringify(platformLanes))
  let card = null
  for (const brand of Object.keys(pl)) {
    for (const plat of Object.keys(pl[brand])) {
      const idx = pl[brand][plat].findIndex(c => c.id === cardId)
      if (idx !== -1) {
        card = { ...pl[brand][plat][idx], platform: targetPlatform, isGenerating: true, genStartedAt: Date.now() }
        pl[brand][plat].splice(idx, 1)
        break
      }
    }
    if (card) break
  }
  if (!card) return
  if (!pl[targetBrand]) pl[targetBrand] = {}
  if (!pl[targetBrand][targetPlatform]) pl[targetBrand][targetPlatform] = []
  pl[targetBrand][targetPlatform].push(card)
  setPlatformLanes(pl)
  setActiveCard(card)
  generatePlatformCopy(card, targetPlatform, { updatePlatformCard, getCachedCopy, setCachedCopy, siblingCopy, promoMode: promoMode?.[targetBrand] || false })
}
