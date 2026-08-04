import { useState, useRef, useEffect } from 'react'
import { useMmStore, API_BASE, MEDIA_COLORS, PLAT_COLORS, IMAGE_MODEL_OPTIONS, MEDIA_LIST, PLAT_LIST, EDITORIAL_MODEL_META } from '../../store/mmStore'
import { useLanguageStore, t } from '../../store/languageStore'
import { useAccountStore } from '../../store/accountStore'
import { PLAT_ICONS } from '../../utils/platformIcons'
import { generateImageInBackground } from '../../utils/imageJobs'
import mgcLogoUrl from '../../assets/brands/mgc-coin-logo.png'
import rankingLogoUrl from '../../assets/brands/ranking-platform-logo.png'
import oasisLogoUrl from '../../assets/brands/oasis-coin-logo.png'
import jewelryLogoUrl from '../../assets/brands/jewelry-coin-logo.png'
import SchedulePicker from './SchedulePicker'

const STATUS_CLASSES = {ready:'sb-ready',image:'sb-image',approved:'sb-approved',scheduled:'sb-scheduled',published:'sb-published',saved:'sb-saved'}
const STATUS_LABELS  = {ready:'Ready',image:'Needs Image',approved:'Approved',scheduled:'Scheduled',published:'Published',saved:'Saved'}
const SCHEDULABLE_PLATFORMS = ['X', 'Telegram']
const PLAT_REASONS = {
  X: '<= 280 chars - punchy hook - 2-3 hashtags',
  Telegram: 'Full context - 2-4 paragraphs - brand-voice',
  Instagram: 'Strong opening hook - 5-10 hashtags',
}
const MEDIA_LOGOS = {
  mgccoin: mgcLogoUrl,
  rankingplatform: rankingLogoUrl,
  oasiscoin: oasisLogoUrl,
  jewelrycoin: jewelryLogoUrl,
}
const brandLogoPromises = new Map()

function loadCanvasImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image()
    image.onload = () => resolve(image)
    image.onerror = () => reject(new Error('Media logo could not be loaded'))
    image.src = src
  })
}
function getBrandLogoCutout(logoUrl) {
  if (brandLogoPromises.has(logoUrl)) return brandLogoPromises.get(logoUrl)
  const logoPromise = loadCanvasImage(logoUrl).then(image => {
    const source = document.createElement('canvas')
    source.width = image.naturalWidth
    source.height = image.naturalHeight
    const ctx = source.getContext('2d', { willReadFrequently:true })
    ctx.drawImage(image, 0, 0)
    const pixels = ctx.getImageData(0, 0, source.width, source.height)
    const data = pixels.data
    const corners = [0, source.width - 1, (source.height - 1) * source.width, source.width * source.height - 1]
    const background = corners.reduce((rgb, pixel) => {
      const offset = pixel * 4
      rgb[0] += data[offset]
      rgb[1] += data[offset + 1]
      rgb[2] += data[offset + 2]
      return rgb
    }, [0, 0, 0]).map(channel => channel / corners.length)

    let minX = source.width, minY = source.height, maxX = -1, maxY = -1
    for (let y = 0; y < source.height; y += 1) {
      for (let x = 0; x < source.width; x += 1) {
        const offset = (y * source.width + x) * 4
        const distance = Math.hypot(
          data[offset] - background[0],
          data[offset + 1] - background[1],
          data[offset + 2] - background[2],
        )
        // The supplied brand assets have solid, non-transparent backgrounds.
        // A wide matte range removes the whole background instead of leaving a
        // pale/dark square behind the coloured logo on generated artwork.
        const alpha = Math.max(0, Math.min(1, (distance - 52) / 32))
        data[offset + 3] = Math.round(data[offset + 3] * alpha)
        if (data[offset + 3] > 18) {
          minX = Math.min(minX, x); minY = Math.min(minY, y)
          maxX = Math.max(maxX, x); maxY = Math.max(maxY, y)
        }
      }
    }
    ctx.putImageData(pixels, 0, 0)
    if (maxX < minX || maxY < minY) throw new Error('Media logo asset is empty')

    const cutout = document.createElement('canvas')
    cutout.width = maxX - minX + 1
    cutout.height = maxY - minY + 1
    cutout.getContext('2d').drawImage(
      source,
      minX, minY, cutout.width, cutout.height,
      0, 0, cutout.width, cutout.height,
    )
    return cutout
  }).catch(error => {
    brandLogoPromises.delete(logoUrl)
    throw error
  })
  brandLogoPromises.set(logoUrl, logoPromise)
  return logoPromise
}

async function applyMediaLogo(imageB64, mediaBrand) {
  const mediaKey = String(mediaBrand || '').replace(/\s+/g, '').toLowerCase()
  const logoUrl = MEDIA_LOGOS[mediaKey]
  if (!logoUrl) return imageB64
  const [image, logo] = await Promise.all([
    loadCanvasImage(`data:image/png;base64,${imageB64}`),
    getBrandLogoCutout(logoUrl),
  ])
  const canvas = document.createElement('canvas')
  canvas.width = image.naturalWidth
  canvas.height = image.naturalHeight
  const ctx = canvas.getContext('2d')
  ctx.drawImage(image, 0, 0)

  const shortSide = Math.min(canvas.width, canvas.height)
  const logoWidth = Math.max(45, Math.round(shortSide * 0.096))
  const logoHeight = Math.round(logoWidth * (logo.height / logo.width))
  const margin = Math.max(20, Math.round(shortSide * 0.045))
  ctx.drawImage(logo, margin, canvas.height - margin - logoHeight, logoWidth, logoHeight)
  return canvas.toDataURL('image/png').split(',', 2)[1]
}

function ButtonSpinner() {
  return <span className="spinner" aria-hidden="true" style={{width:12,height:12,border:'1.5px solid rgba(7,9,14,.3)',borderTopColor:'#171c26'}} />
}

async function callAppsScript(payload) {
  const { action, ...rest } = payload
  const pathMap = { approve:'/api/sheets/approve', schedule:'/api/sheets/schedule', uploadImage:'/api/sheets/upload-image', update:'/api/sheets/update' }
  const res = await fetch(`${API_BASE}${pathMap[action]||'/api/sheets/approve'}`, {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(rest)
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error || `Sheets error ${res.status}`)
  }
  return res.json()
}
async function postingError(res, destination) {
  const data = await res.json().catch(() => ({}))
  if (data?.error) return data.error
  if (res.status === 413) return `The ${destination} image upload is too large for the server.`
  return `${destination} error ${res.status}`
}

class TelegramConfirmationDelayedError extends Error {
  constructor() {
    super('Telegram did not return its confirmation in time.')
    this.name = 'TelegramConfirmationDelayedError'
  }
}

// Note: copyText / hashtagsState are the LIVE, user-approved values from the panel
// (what the user is actually looking at) — NOT card.copy/card.hashtags, which are
// the stale store snapshot frozen when the panel opened. Every action that ships a
// post MUST use the live values so the published text matches the approved copy.
async function sendToTelegram(card, imageB64, copyText, hashtagsState) {
  const res = await fetch(`${API_BASE}/api/telegram/post`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ imageB64:imageB64||'', headline:card.headline||'', copy:copyText, hashtags:hashtagsState, link:card.link||'', mediaBrand:card.media })
  })
  if (res.status === 504) throw new TelegramConfirmationDelayedError()
  if (!res.ok) throw new Error(await postingError(res, 'Telegram'))
  const data = await res.json()
  if (!data?.ok || !data?.result?.message_id) throw new Error('Telegram did not confirm the post with a message ID')
  return data
}

async function sendToX(card, imageB64, copyText, hashtagsState) {
  const res = await fetch(`${API_BASE}/api/twitter/post`, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({ imageB64:imageB64||'', copy:copyText, hashtags:hashtagsState, platform:card.platform, mediaBrand:card.media })
  })
  if (!res.ok) throw new Error(await postingError(res, 'X'))
  const data = await res.json()
  if (!data?.success || !data?.tweetId) throw new Error('X did not confirm the post with a post ID')
  return data
}

async function createScheduledPost(card, mode, copyText, hashtagsState, generatedImg, scheduledAtIso, platformOverride) {
  // platformOverride comes from the scheduler's platform picker — it is the
  // authoritative platform for the scheduled post, since card.platform may be
  // 'suggested' or '' for unrouted saved cards.
  const platform = platformOverride || card.platform
  const res = await fetch(`${API_BASE}/api/schedule/create`, {
    method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      cardId: mode === 'saved' ? card.card_id : card.id,
      savedCardId: mode === 'saved' ? card.id : null,
      brand: card.media, platform, modelDisplay: card._modelDisplay||'',
      headline: card.headline, copy: copyText,
      hashtags: hashtagsState.length ? hashtagsState : (card.hashtags||[]),
      sentiment: card.sentiment, suitability: card.suitability, impact: card.impact, virality: card.virality,
      source: card.source, sourceUrl: card.link||'',
      imageB64: generatedImg || card._generatedImageB64 || '',
      imageUrl: card.imageUrl||'',
      scheduledAt: scheduledAtIso,
    })
  })
  if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Schedule failed (${res.status})`) }
}

export default function PreviewPanel({ mode = 'multimedia', card: cardProp, onClose }) {
  const language = useLanguageStore(state => state.language)
  const tr = text => t(language, text)
  const { activeCard, setActiveCard, updateCardStatus, updatePlatformCard } = useMmStore()
  const { confirmScheduleSaved, discardSaved, updateSavedCard, updateSavedCardLocal } = useAccountStore()
  const card = mode === 'saved' ? cardProp : activeCard
  const isOpen = !!card
  // A routed card can retain its article id while moving between platforms.
  // Treat that move as a new panel session so completed actions never leak
  // into the next article/platform the user opens.
  const cardIdentity = card?.id || card?.card_id || card?.link || card?.sourceUrl || ''
  const cardSessionKey = `${cardIdentity}|${card?.platform || ''}`

  function _approveLabel(plat) {
    const p = (plat || '').trim().toLowerCase()
    if (p === 'telegram') return 'Post to Telegram'
    if (p === 'x' || p === 'twitter') return 'Post to X'
    return 'Approve Image'
  }

  const [editingHeadline, setEditingHeadline] = useState(false)
  const [headlineText, setHeadlineText] = useState('')
  const [editing, setEditing]         = useState(false)
  const [copyText, setCopyText]       = useState('')
  const [showImage, setShowImage]     = useState(false)
  const [showSchedule, setShowSchedule] = useState(false)
  const [imageModel, setImageModel]   = useState('openai/gpt-5.4-image-2')
  const [imagePrompt, setImagePrompt] = useState('')
  const [refImages, setRefImages]     = useState([])
  const [generatedImg, setGeneratedImg] = useState(cardProp?._generatedImageB64 || '')
  const [imgLoading, setImgLoading]   = useState(false)
  const [imageGenError, setImageGenError] = useState('')
  const [aiBrief, setAiBrief]         = useState(null)
  const [showAiBrief, setShowAiBrief] = useState(false)
  const [approveLabel, setApproveLabel] = useState('✓ Approve')
  const [approveImgLabel, setApproveImgLabel] = useState(() => _approveLabel(cardProp?.platform))
  const [saveLabel, setSaveLabel] = useState('Save for Later')
  const [schedDate, setSchedDate] = useState('')
  const [schedTime, setSchedTime] = useState('09:00')
  const [selectedVariant, setSelectedVariant] = useState(null)
  const [genPct, setGenPct] = useState(0)
  const [hashtagsState, setHashtagsState] = useState([])
  const [discardLabel, setDiscardLabel] = useState('Discard')
  const [confirmLabel, setConfirmLabel] = useState('✓ Confirm')
  const [savedStatus, setSavedStatus] = useState(null)
  const [scheduleSavedLabel, setScheduleSavedLabel] = useState('Confirm Schedule')
  const [retargetBrand, setRetargetBrand] = useState(cardProp?.media || cardProp?.brand || MEDIA_LIST[0])
  const [retargetPlatform, setRetargetPlatform] = useState(cardProp?.platform || 'X')
  const [retargetModel, setRetargetModel] = useState(cardProp?._modelKey || 'gpt')
  const [retargetLoading, setRetargetLoading] = useState(false)
  const [retargetMsg, setRetargetMsg] = useState(null)
  // Effective platform for scheduling. Cards may be unrouted ('suggested'/'')
  // — the scheduler requires the user to pick X or Telegram explicitly before
  // a scheduled post can be created, so the choice lives here, not on card.platform.
  const [schedPlatform, setSchedPlatform] = useState(cardProp?.platform || '')
  // Inline status message for the schedule panel (replaces jarring alert() popups).
  // type: 'error' | 'info' | 'success'. Cleared on any scheduler interaction.
  const [schedMsg, setSchedMsg] = useState(null)
  const [actionMsg, setActionMsg] = useState(null)
  const [sheetSyncMsg, setSheetSyncMsg] = useState(null)
  const [actionBusy, setActionBusy] = useState(false)
  const [telegramConfirmationDelayed, setTelegramConfirmationDelayed] = useState(false)
  const [integrationStatus, setIntegrationStatus] = useState({ publishing:{enabled:false}, sheets:{enabled:false} })
  const copyRef = useRef(null)
  const panelRef = useRef(null)
  const imageSectionRef = useRef(null)
  const imageJobSessionRef = useRef(0)

  function showSchedMsg(text, type = 'error') { setSchedMsg({ text, type }) }

  useEffect(() => {
    fetch(`${API_BASE}/api/integrations/status`, { credentials:'include' })
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(setIntegrationStatus)
      .catch(() => setIntegrationStatus({ publishing:{enabled:false}, sheets:{enabled:false} }))
  }, [])

  // Stop updating this panel if the user closes it or opens another card while
  // the detached backend job continues safely to completion.
  useEffect(() => () => { imageJobSessionRef.current += 1 }, [])

  // Whenever the image panel opens, scroll it into view. Otherwise the textarea
  // + reference-image picker render below the fold (after headline/scores/copy/
  // variants/hashtags) and look like "nothing happened" — the user can't see
  // them. Runs in both multimedia and saved modes, for every media/platform.
  useEffect(() => {
    if (showImage && imageSectionRef.current && panelRef.current) {
      // Defer one tick so the section has actually mounted before we scroll.
      const t = setTimeout(() => {
        const panel = panelRef.current
        const section = imageSectionRef.current
        if (!panel || !section) return
        const targetTop = panel.scrollTop
          + section.getBoundingClientRect().top
          - panel.getBoundingClientRect().top
          - 12
        panel.scrollTo({ top: Math.max(0, targetTop), behavior:'smooth' })
      }, 50)
      return () => clearTimeout(t)
    }
  }, [showImage])

  const ESTIMATE_MS = 18000
  useEffect(() => {
    if (!card?.isGenerating) return
    setGenPct(0)
    const started = card.genStartedAt || Date.now()
    const tick = () => setGenPct(Math.min(92, Math.round(100 * (1 - Math.exp(-(Date.now() - started) / ESTIMATE_MS)))))
    tick()
    const id = setInterval(tick, 250)
    return () => { clearInterval(id); setGenPct(100) }
  }, [card?.id, card?.platform, card?.isGenerating, card?.genStartedAt])

  useEffect(() => {
    if (card) {
      setHeadlineText(card.headline || '')
      setEditingHeadline(false)
      setCopyText(card.copy || '')
      setEditing(false)
      setShowImage(false)
      setShowSchedule(false)
      setGeneratedImg(card._generatedImageB64 || '')
      setImageGenError('')
      setApproveLabel('✓ Approve')
      setApproveImgLabel(_approveLabel(card?.platform))
      setSaveLabel('Save for Later')
      setSelectedVariant(0)
      setHashtagsState(card.hashtags || [])
      setDiscardLabel('Discard')
      setScheduleSavedLabel('Confirm Schedule')
      setConfirmLabel('✓ Confirm')
      setSavedStatus(null)
      setSchedMsg(null)
      setActionMsg(null)
      setSheetSyncMsg(null)
      setActionBusy(false)
      setTelegramConfirmationDelayed(false)
      setRetargetBrand(card.media || card.brand || MEDIA_LIST[0])
      setRetargetPlatform(PLAT_LIST.includes(card.platform) ? card.platform : 'X')
      setRetargetModel(card._modelKey || 'gpt')
      setRetargetLoading(false)
      setRetargetMsg(null)
      // Pre-select the card's existing platform only if it's actually schedulable;
      // for unrouted cards leave it blank so the picker forces a choice.
      setSchedPlatform(SCHEDULABLE_PLATFORMS.includes(card.platform) ? card.platform : '')
    }
  }, [cardSessionKey])

  if (!card) return null

  const liveHeadline = headlineText.trim() || card.headline || ''
  const actionCard = liveHeadline === card.headline ? card : { ...card, headline: liveHeadline }
  const mc = MEDIA_COLORS[card.media] || '#a7abb2'
  const pc = PLAT_COLORS[card.platform] || '#a7abb2'
  const sentColor = card.sentiment==='Bullish'?'#00d4a0':card.sentiment==='Bearish'?'#ef4455':'#a7abb2'
  const isPersian = language === 'fa'
  const displayStatus = mode === 'saved' ? (savedStatus || card.status) : card.status
  const isApprovalBusy = actionBusy && approveLabel.startsWith('Saving')
  const isImageActionBusy = actionBusy && (approveImgLabel.startsWith('Posting') || approveImgLabel.startsWith('Uploading'))
  const isSaveBusy = actionBusy && saveLabel.startsWith('Saving')
  const selectedImageModel = IMAGE_MODEL_OPTIONS.find(option => option.value === imageModel) || IMAGE_MODEL_OPTIONS[0]
  const maxReferenceImages = selectedImageModel.maxReferences || 3

  function markApproved() {
    if (mode === 'multimedia') updateCardStatus(card.id, 'approved')
    else setSavedStatus('approved')
  }

  function commitHeadline() {
    const nextHeadline = headlineText.trim()
    if (!nextHeadline) {
      setHeadlineText(card.headline || '')
      setEditingHeadline(false)
      return
    }
    setHeadlineText(nextHeadline)
    if (mode === 'multimedia') {
      if (nextHeadline !== card.headline) updatePlatformCard(card.id, card.platform, { headline: nextHeadline })
    } else {
      updateSavedCardLocal(card.id, { headline: nextHeadline })
      void updateSavedCard(card.id, { headline: nextHeadline }).catch(e => {
        setActionMsg({ type:'error', text:`Headline update failed: ${e.message}` })
      })
    }
    setEditingHeadline(false)
  }

  function handleHeadlineChange(nextHeadline) {
    setHeadlineText(nextHeadline)
    if (!nextHeadline.trim()) return
    if (mode === 'multimedia') updatePlatformCard(card.id, card.platform, { headline: nextHeadline })
  }

  async function handleRegenerateSavedCopy() {
    if (mode !== 'saved' || retargetLoading) return
    const modelMeta = EDITORIAL_MODEL_META[retargetModel] || EDITORIAL_MODEL_META.gpt
    const nextCard = {
      brand: retargetBrand,
      platform: retargetPlatform,
      model_display: modelMeta.display,
      model_color: modelMeta.color,
      _modelKey: retargetModel,
      isGenerating: true,
      genStartedAt: Date.now(),
    }
    setRetargetLoading(true)
    setRetargetMsg(null)
    setShowImage(false)
    setGeneratedImg('')
    setAiBrief(null)
    updateSavedCardLocal(card.id, nextCard)

    try {
      const res = await fetch(`${API_BASE}/api/copy/generate`, {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          article:{
            title:liveHeadline,
            source:card.source,
            desc:copyText || card.copy || '',
            matchedKeywords:hashtagsState || card.hashtags || [],
          },
          platform:retargetPlatform,
          mediaBrand:retargetBrand,
          sentiment:card.sentiment || 'Neutral',
          modelKey:retargetModel,
          language:card.language || useLanguageStore.getState().language,
          promoMode:Boolean(card._isPromo || card.promoMode || card.source === 'Promo'),
          variantCount:3,
        })
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Copy failed (${res.status})`) }
      const result = await res.json()
      const variants = result.variants || []
      const chosen = variants[0] || result
      const copy = chosen.copy || result.copy || copyText
      const hashtags = chosen.hashtags || result.hashtags || hashtagsState
      const patch = {
        media:retargetBrand,
        brand:retargetBrand,
        platform:retargetPlatform,
        modelDisplay:modelMeta.display,
        model_display:modelMeta.display,
        modelColor:modelMeta.color,
        model_color:modelMeta.color,
        copy,
        hashtags,
        variants,
        _modelKey:retargetModel,
        _modelDisplay:modelMeta.display,
        _modelColor:modelMeta.color,
        platReason:PLAT_REASONS[retargetPlatform] || `Formatted for ${retargetPlatform}`,
        isGenerating:false,
      }
      setCopyText(copy)
      setHashtagsState(hashtags)
      setSelectedVariant(null)
      setApproveImgLabel(_approveLabel(retargetPlatform))
      setSchedPlatform(SCHEDULABLE_PLATFORMS.includes(retargetPlatform) ? retargetPlatform : '')
      const saved = await updateSavedCard(card.id, {
        media:retargetBrand,
        platform:retargetPlatform,
        modelDisplay:modelMeta.display,
        modelColor:modelMeta.color,
        copy,
        hashtags,
        variants,
        modelKey:retargetModel,
      })
      updateSavedCardLocal(card.id, { ...(saved || {}), ...patch })
      setRetargetMsg({ type:'success', text:'New copy generated. Pick a variant, then approve, image, or schedule.' })
    } catch(e) {
      updateSavedCardLocal(card.id, { isGenerating:false })
      setRetargetMsg({ type:'error', text:e.message || 'Copy generation failed' })
    } finally {
      setRetargetLoading(false)
    }
  }

  async function handleApprove() {
    if (actionBusy) return
    setActionBusy(true)
    setActionMsg(null)
    if (!integrationStatus.sheets.enabled) {
      markApproved()
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand:card.media, platform:card.platform, modelDisplay:card._modelDisplay||'', headline:liveHeadline, action:'approved' })
      }).catch(()=>{})
      setApproveLabel('✓ Approved locally')
      setActionMsg({ type:'success', text:'Approved locally. Google Sheets is disconnected.' })
      setActionBusy(false)
      return
    }
    setActionMsg({ type:'info', text:'Updating Google Sheets...' })
    setApproveLabel('Saving…')
    try {
      await callAppsScript({ action:'approve', id:card.id, title:liveHeadline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:hashtagsState, sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:card.imageUrl?'Image Approved':'No Image', imageUrl:card.imageUrl||'' })
      markApproved()
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'', headline: liveHeadline, action: 'approved' })
      }).catch(()=>{})
      if (card.platform==='X') setApproveLabel('✓ Saved — Approve Image below to post to X')
      else if (card.platform==='Telegram') setApproveLabel('✓ Saved — Approve Image to post to Telegram')
      else if (card.platform==='Instagram') setApproveLabel('✓ Saved to Sheets — post manually on Instagram')
      else setApproveLabel('✓ Approved')
      setActionMsg({ type:'success', text:'Google Sheets updated.' })
    } catch(e) {
      setApproveLabel('✓ Approve')
      setActionMsg({ type:'error', text:`Approval failed: ${e.message}` })
    } finally {
      setActionBusy(false)
    }
  }

  async function handleGenerateImage() {
    if (imgLoading) return
    const sessionId = imageJobSessionRef.current + 1
    imageJobSessionRef.current = sessionId
    const requestedCardIdentity = cardIdentity
    setImgLoading(true); setGeneratedImg(''); setAiBrief(null); setImageGenError('')
    try {
      const payload = { article:{title:liveHeadline}, platform:card.platform||'X', mediaBrand:card.media||MEDIA_LIST[0], sentiment:card.sentiment||'Neutral', model:imageModel, copy:copyText, language:card.language || useLanguageStore.getState().language, ...(imagePrompt.trim() && {imageDirection:imagePrompt.trim()}), ...(refImages.length && {referenceImages:refImages.map(r=>r.b64)}) }
      const data = await generateImageInBackground({
        apiBase:API_BASE,
        payload,
        isCancelled:() => imageJobSessionRef.current !== sessionId,
      })
      if (!data) return
      if (!data.imageB64) throw new Error(data.error || 'No image data returned')
      if (imageJobSessionRef.current !== sessionId) return
      const finalImageB64 = await applyMediaLogo(data.imageB64, card.media||MEDIA_LIST[0])
      if (imageJobSessionRef.current !== sessionId) return
      setGeneratedImg(finalImageB64)
      if (mode === 'multimedia') {
        const currentCard = useMmStore.getState().activeCard
        const currentIdentity = currentCard?.id || currentCard?.card_id || currentCard?.link || currentCard?.sourceUrl || ''
        if (currentCard && currentIdentity === requestedCardIdentity) currentCard._generatedImageB64 = finalImageB64
      }
      if (data.brief) setAiBrief({ brief: data.brief, prompt: data.prompt })
    } catch(e) {
      if (imageJobSessionRef.current === sessionId) {
        const message = e?.message === 'Failed to fetch'
          ? 'The connection was interrupted while starting image generation. Please try again.'
          : e?.message
        setImageGenError(message || 'Image generation failed after automatic retries.')
      }
    } finally {
      if (imageJobSessionRef.current === sessionId) setImgLoading(false)
    }
  }

  async function handleDownloadImage() {
    const b64 = generatedImg || card._generatedImageB64
    if (!b64) return
    try {
      // Build a Blob from the base64 PNG and trigger a download. The Blob route
      // is more reliable than a raw data URL in `href` for large images.
      const res = await fetch(`data:image/png;base64,${b64}`)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeBrand = (card.media || card.brand || 'image').replace(/[^a-z0-9]+/gi, '-').toLowerCase()
      a.download = `${safeBrand}-${(card.id || 'card').slice(0, 8)}.png`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert('Download failed: ' + e.message)
    }
  }

  async function syncPostedImageToGoogle(b64, destination) {
    if (!integrationStatus.sheets.enabled) {
      setSheetSyncMsg({ type:'info', text:'Google Sheets is disconnected in this local workspace.' })
      return
    }
    try {
      setSheetSyncMsg({ type:'info', text:'Saving the image to Google Drive...' })
      const upload = await callAppsScript({ action:'uploadImage', imageB64:b64, mediaBrand:card.media, platform:card.platform||'X' })
      const driveUrl = upload?.driveUrl || ''
      if (mode === 'multimedia') useMmStore.getState().activeCard.imageUrl = driveUrl
      setSheetSyncMsg({ type:'info', text:'Updating Google Sheets...' })
      await callAppsScript({ action:'approve', id:card.id, title:liveHeadline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:hashtagsState, sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:'Image Approved', imageUrl:driveUrl })
      setSheetSyncMsg({ type:'success', text:'Google Sheets updated.' })
    } catch (e) {
      setSheetSyncMsg({ type:'error', text:`Google sync did not complete: ${e.message}` })
    }
  }

  function handleTelegramConfirmationDelayed(b64) {
    markApproved()
    setTelegramConfirmationDelayed(true)
    setApproveImgLabel('Check Telegram')
    setActionMsg({ type:'warning', text:'Telegram may have posted this image, but its confirmation was delayed. Check the channel before posting again.' })
    void syncPostedImageToGoogle(b64, 'Telegram')
  }

  async function handleApproveImage() {
    if (actionBusy) return
    const b64 = generatedImg || card._generatedImageB64
    if (!b64) {
      setActionMsg({ type:'error', text:'Generate an image before approving or posting it.' })
      return
    }
    if (!integrationStatus.publishing.enabled && !integrationStatus.sheets.enabled) {
      markApproved()
      setApproveImgLabel('✓ Approved locally')
      setActionMsg({ type:'success', text:'Image approved locally. External posting and Google Sheets are disconnected.' })
      return
    }
    const platform = (card.platform || '').trim().toLowerCase()
    if (platform === 'telegram' || platform === 'x' || platform === 'twitter') {
      const destination = platform === 'telegram' ? 'Telegram' : 'X'
      setActionBusy(true)
      setSheetSyncMsg(null)
      setApproveImgLabel(`Posting to ${destination}...`)
      setActionMsg({ type:'info', text:`Posting this article to ${destination}...` })
      try {
        if (platform === 'telegram') await sendToTelegram(actionCard, b64, copyText, hashtagsState)
        else await sendToX(actionCard, b64, copyText, hashtagsState)
        markApproved()
        setApproveImgLabel(`✓ Posted to ${destination}`)
        setActionMsg({ type:'success', text:`✓ Posted to ${destination}.` })
        void syncPostedImageToGoogle(b64, destination)
      } catch (e) {
        if (platform === 'telegram' && e instanceof TelegramConfirmationDelayedError) {
          handleTelegramConfirmationDelayed(b64)
          return
        }
        setApproveImgLabel(`Post to ${destination}`)
        setActionMsg({ type:'error', text:`${destination} posting failed: ${e.message}` })
      } finally {
        setActionBusy(false)
      }
      return
    }
    setActionBusy(true)
    setActionMsg({ type:'info', text:'Uploading image to Google Drive...' })
    setApproveImgLabel('Uploading to Drive…')
    try {
      const up = await callAppsScript({ action:'uploadImage', imageB64:b64, mediaBrand:card.media, platform:card.platform||'X' })
      const driveUrl = up?.driveUrl || ''
      if (mode === 'multimedia') useMmStore.getState().activeCard.imageUrl = driveUrl
      setActionMsg({ type:'info', text:'Updating Google Sheets with the approved image...' })
      await callAppsScript({ action:'approve', id:card.id, title:liveHeadline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:hashtagsState, sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:'Image Approved', imageUrl:driveUrl })
      const plat = (card.platform || '').trim().toLowerCase()
      if (plat === 'x' || plat === 'twitter') {
        setActionMsg({ type:'info', text:'Image saved. Posting to X...' })
        setApproveImgLabel('Posting to X…')
        try {
          await sendToX(actionCard, b64, copyText, hashtagsState)
          markApproved()
          setApproveImgLabel('✓ Posted to X')
          setActionMsg({ type:'success', text:'✓ Posted to X.' })
        } catch(e) {
          setApproveImgLabel('Post to X')
          setActionMsg({ type:'error', text:`X posting failed: ${e.message}` })
        }
      } else if (plat === 'telegram') {
        setActionMsg({ type:'info', text:'Image saved. Posting to Telegram...' })
        setApproveImgLabel('Posting to Telegram…')
        try {
          await sendToTelegram(actionCard, b64, copyText, hashtagsState)
          markApproved()
          setApproveImgLabel('✓ Posted to Telegram')
          setActionMsg({ type:'success', text:'✓ Posted to Telegram.' })
        } catch(e) {
          if (e instanceof TelegramConfirmationDelayedError) {
            handleTelegramConfirmationDelayed(b64)
            return
          }
          setApproveImgLabel('Post to Telegram')
          setActionMsg({ type:'error', text:`Telegram posting failed: ${e.message}` })
        }
      } else if (plat === 'instagram') {
        markApproved(); setApproveImgLabel('✓ Image saved — post manually on Instagram')
        setActionMsg({ type:'success', text:'✓ Image saved to Google Drive.' })
      } else {
        markApproved(); setApproveImgLabel('✓ Image saved to Drive — route card to a platform to post')
        setActionMsg({ type:'success', text:'✓ Image saved to Google Drive.' })
      }
    } catch(e) {
      setApproveImgLabel('Approve Image')
      setActionMsg({ type:'error', text:`Image approval failed before posting: ${e.message}` })
    } finally {
      setActionBusy(false)
    }
  }

  async function handleSchedule() {
    if (!integrationStatus.publishing.enabled) {
      showSchedMsg('Scheduling is disabled in this local workspace until RZWire publishing is connected.', 'info')
      return
    }
    if (!schedDate||!schedTime) { showSchedMsg('Please select a date and time.', 'error'); return }
    if (!SCHEDULABLE_PLATFORMS.includes(schedPlatform)) {
      showSchedMsg('Choose a platform to schedule — X or Telegram. Instagram requires a manual post.', 'error'); return
    }
    const scheduledAtIso = new Date(`${schedDate}T${schedTime}`).toISOString()
    if (new Date(scheduledAtIso) <= new Date()) { showSchedMsg('Please pick a time in the future.', 'error'); return }
    setSchedMsg(null)
    try {
      await callAppsScript({ action:'schedule', id:card.id, title:liveHeadline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:schedPlatform, copy:copyText, hashtags:hashtagsState, sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, scheduledDate:schedDate, scheduledTime:schedTime })
      if (SCHEDULABLE_PLATFORMS.includes(schedPlatform)) {
        await createScheduledPost(actionCard, mode, copyText, hashtagsState, generatedImg, scheduledAtIso, schedPlatform)
        useAccountStore.getState().fetchScheduled()
      }
      updateCardStatus(card.id,'scheduled')
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: schedPlatform, modelDisplay: card._modelDisplay||'', headline: liveHeadline, action: 'scheduled' })
      }).catch(()=>{})
      setShowSchedule(false)
    } catch(e) { showSchedMsg('Schedule error: '+e.message, 'error') }
  }

  async function handleSaveForLater() {
    if (actionBusy) return
    setActionBusy(true)
    setActionMsg({ type:'info', text:'Saving this card for later...' })
    setSaveLabel('Saving…')
    try {
      const res = await fetch(`${API_BASE}/api/account/save`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({
          id: card.id, media: card.media, platform: card.platform,
          modelDisplay: card._modelDisplay, modelColor: card._modelColor,
          headline: liveHeadline, copy: copyText, hashtags: hashtagsState,
          sentiment: card.sentiment, suitability: card.suitability, impact: card.impact, virality: card.virality,
          source: card.source, link: card.link||'', initials: card.initials, srcColor: card.srcColor,
          variants: card.variants||[],
        })
      })
      if (!res.ok) { const e = await res.json().catch(()=>({})); throw new Error(e?.error || `Save failed (${res.status})`) }
      setSaveLabel('✓ Saved for Later')
      setActionMsg({ type:'success', text:'Saved for later.' })
    } catch(e) {
      setSaveLabel('Save for Later')
      setActionMsg({ type:'error', text:`Save failed: ${e.message}` })
    } finally {
      setActionBusy(false)
    }
  }

  async function handleConfirmScheduleSaved() {
    if (!schedDate||!schedTime) { showSchedMsg('Please select a date and time.', 'error'); return }
    if (!SCHEDULABLE_PLATFORMS.includes(schedPlatform)) {
      showSchedMsg('Choose a platform to schedule — X or Telegram. Instagram requires a manual post.', 'error'); return
    }
    const scheduledAtIso = new Date(`${schedDate}T${schedTime}`).toISOString()
    if (new Date(scheduledAtIso) <= new Date()) { showSchedMsg('Please pick a time in the future.', 'error'); return }
    setSchedMsg(null)
    setScheduleSavedLabel('Scheduling…')
    try {
      // Always create the scheduled-post row — the platform was just chosen
      // explicitly in the picker, so the silent-skip failure mode is gone.
      await createScheduledPost(actionCard, mode, copyText, hashtagsState, generatedImg, scheduledAtIso, schedPlatform)
      useAccountStore.getState().fetchScheduled()
      const ok = await confirmScheduleSaved(card.id, schedDate, schedTime, copyText, hashtagsState, {
        media: card.media,
        platform: schedPlatform,
        modelDisplay: card._modelDisplay || card.model_display || '',
        headline: liveHeadline,
      })
      if (ok) onClose?.()
      else setScheduleSavedLabel('Confirm Schedule')
    } catch(e) { setScheduleSavedLabel('Confirm Schedule'); showSchedMsg('Schedule error: '+e.message, 'error') }
  }

  async function handleDiscard() {
    setDiscardLabel('Discarding…')
    const ok = await discardSaved(card.id)
    if (ok) onClose?.()
    else setDiscardLabel('Discard')
  }

  async function handleConfirmSaved() {
    setConfirmLabel('Saving…')
    try {
      await callAppsScript({ action:'approve', id:card.id, title:liveHeadline, source:card.source, sourceUrl:card.link||'', mediaBrand:card.media, platform:card.platform, copy:copyText, hashtags:hashtagsState, sentiment:card.sentiment, fitScore:card.suitability, impactScore:card.impact, viralityScore:card.virality, imageStatus:card.imageUrl?'Image Approved':'No Image', imageUrl:card.imageUrl||'' })
      markApproved()
      fetch(`${API_BASE}/api/account/log-action`, {
        method:'POST', credentials:'include', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ brand: card.media, platform: card.platform, modelDisplay: card._modelDisplay||'', headline: liveHeadline, action: 'approved' })
      }).catch(()=>{})
      if (card.platform==='X') setConfirmLabel('✓ Saved — Approve Image below to post to X')
      else if (card.platform==='Telegram') setConfirmLabel('✓ Saved — Approve Image to post to Telegram')
      else if (card.platform==='Instagram') setConfirmLabel('✓ Saved to Sheets — post manually on Instagram')
      else setConfirmLabel('✓ Approved')
    } catch(e) { markApproved(); setConfirmLabel('✓ Confirm') }
  }

  function openSchedule() {
    setShowImage(false)
    setShowSchedule(s => {
      if (!s) {
        const d = new Date(); d.setDate(d.getDate()+1)
        setSchedDate(d.toISOString().split('T')[0])
        setSchedTime('09:00')
      }
      setSchedMsg(null)
      return !s
    })
  }

  function handleClose() {
    if (mode === 'saved') onClose?.()
    else setActiveCard(null)
  }

  function chooseVariant(variant, index) {
    const nextCopy = variant?.copy || ''
    const nextHashtags = Array.isArray(variant?.hashtags) ? variant.hashtags : []
    setSelectedVariant(index)
    setCopyText(nextCopy)
    setHashtagsState(nextHashtags)
    setEditing(false)
    if (copyRef.current) copyRef.current.textContent = nextCopy
    if (mode === 'multimedia') {
      // Replace the active card as well as its lane entry. Telegram cards are
      // rendered from activeCard, so this makes the visible copy change in the
      // same render as the chosen-variant highlight.
      setActiveCard({
        ...card,
        copy: nextCopy,
        hashtags: nextHashtags,
        charCount: nextCopy.length,
        selectedVariant: index,
      })
      updatePlatformCard(card.id, card.platform, {
        copy: nextCopy,
        hashtags: nextHashtags,
        charCount: nextCopy.length,
        selectedVariant: index,
      })
    } else if (mode === 'saved') {
      updateSavedCardLocal(card.id, {
        copy: nextCopy,
        hashtags: nextHashtags,
      })
    }
  }

  const selectedCopy = selectedVariant === null ? copyText : card?.copy || copyText

  const panelId = mode === 'saved' ? 'saved-detail-panel' : 'preview-panel'
  const overlayId = mode === 'saved' ? 'saved-detail-overlay' : 'preview-overlay'

  return (
    <>
      {/* Overlay */}
      <div id={overlayId} className={isOpen?'open':''}></div>

      {/* Panel */}
      <div id={panelId} ref={panelRef} className={isOpen?'open':''}>
        {/* Header */}
        <div style={{padding:'14px 16px',borderBottom:'1px solid rgba(255,255,255,.07)',display:'flex',alignItems:'center',justifyContent:'space-between',flexShrink:0}}>
          <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap'}}>
            <div style={{padding:'2px 8px',borderRadius:5,fontSize:9,fontWeight:700,letterSpacing:'.05em',background:mc+'20',color:mc,border:`1px solid ${mc}35`}}>{card.media}</div>
            <div style={{width:22,height:22,borderRadius:6,display:'flex',alignItems:'center',justifyContent:'center',background:pc+'1a',color:pc}}>{PLAT_ICONS[card.platform]}</div>
            <span style={{fontFamily:"'Space Grotesk',sans-serif",fontWeight:700,fontSize:13,color:'#eeeae2'}}>{card.platform}</span>
            <span className={`sbadge`} style={{fontSize:9,background:sentColor+'15',color:sentColor,border:`1px solid ${sentColor}35`}}>{card.sentiment}</span>
          </div>
          <button onClick={handleClose} style={{background:'none',border:'none',cursor:'pointer',color:'#a7abb2',padding:4,borderRadius:6,transition:'color .18s,background .18s'}}
            onMouseEnter={e=>{e.currentTarget.style.color='#eeeae2';e.currentTarget.style.background='rgba(255,255,255,.07)'}}
            onMouseLeave={e=>{e.currentTarget.style.color='#a7abb2';e.currentTarget.style.background='none'}}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>

        {/* Body */}
        <div style={{padding:16,display:'flex',flexDirection:'column',gap:14}}>
          {!integrationStatus.publishing.enabled && !integrationStatus.sheets.enabled && (
            <div style={{padding:'9px 11px',borderRadius:9,background:'rgba(24,199,207,.08)',border:'1px solid rgba(24,199,207,.24)',color:'#8ee9df',fontSize:11,lineHeight:1.5}}>
              Local safe mode: external publishing and Google Sheets are disconnected.
            </div>
          )}
          {/* Source */}
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <div style={{width:20,height:20,borderRadius:5,flexShrink:0,display:'flex',alignItems:'center',justifyContent:'center',fontSize:7,fontWeight:700,background:card.srcColor+'1a',color:card.srcColor,border:`1px solid ${card.srcColor}30`}}>{card.initials}</div>
            <span style={{fontSize:12,color:'#a7abb2'}}>{card.source}</span>
            <span style={{fontSize:10,color:'#777e88',marginLeft:'auto'}}>{card.timeAgo}</span>
          </div>

          {/* Headline */}
          <div>
            <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:6}}>
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',letterSpacing:0,textTransform:'uppercase'}}>Headline</p>
              <button type="button" onClick={editingHeadline ? commitHeadline : ()=>setEditingHeadline(true)}
                style={{fontSize:10,fontWeight:600,color:'#00d4a0',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',borderRadius:5,transition:'background .18s'}}
                onMouseEnter={e=>e.currentTarget.style.background='rgba(0,212,160,.1)'} onMouseLeave={e=>e.currentTarget.style.background='none'}>
                {editingHeadline ? 'Done' : 'Edit'}
              </button>
            </div>
            {editingHeadline
              ? <textarea autoFocus dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} value={headlineText} onChange={e=>handleHeadlineChange(e.target.value)} rows={2}
                  style={{width:'100%',minHeight:58,background:'rgba(0,212,160,.05)',border:'1px solid rgba(0,212,160,.45)',borderRadius:8,padding:'8px 10px',fontSize:15,fontWeight:700,color:'#eeeae2',lineHeight:1.4,fontFamily:isPersian?"'Vazirmatn','Inter',sans-serif":"'Space Grotesk',sans-serif",resize:'vertical',boxShadow:'0 0 0 3px rgba(0,212,160,.08)',outline:'none',letterSpacing:0}}/>
              : <h3 dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''}
                  style={{fontFamily:isPersian?"'Vazirmatn','Inter',sans-serif":"'Space Grotesk',sans-serif",fontWeight:700,fontSize:15,color:'#eeeae2',lineHeight:1.4,letterSpacing:0}}>{liveHeadline}</h3>
            }
          </div>

          {/* Scores */}
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
            <span className="sbadge sb-ready" style={{fontSize:9.5}}>⚡ Fit {card.suitability}/10</span>
            <span className="sbadge sb-image" style={{fontSize:9.5}}>Impact {card.impact}/10</span>
            <span className="sbadge sb-scheduled" style={{fontSize:9.5}}>Virality {card.virality}/10</span>
          </div>

          {mode === 'saved' && (
            <div style={{display:'flex',flexDirection:'column',gap:8,padding:'10px 12px',borderRadius:8,background:'rgba(255,255,255,.035)',border:'1px solid rgba(255,255,255,.08)'}}>
              <p style={{fontSize:10,fontWeight:700,color:'#a7abb2',letterSpacing:'.06em',textTransform:'uppercase'}}>Retarget Saved Article</p>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8}}>
                <label style={{display:'flex',flexDirection:'column',gap:4}}>
                  <span style={{fontSize:9.5,fontWeight:600,color:'#a7abb2',letterSpacing:'.05em',textTransform:'uppercase'}}>Media</span>
                  <select value={retargetBrand} onChange={e=>{setRetargetBrand(e.target.value); setRetargetMsg(null)}} className="cr-input" style={{width:'100%',padding:'7px 9px',fontSize:11}}>
                    {MEDIA_LIST.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
                <label style={{display:'flex',flexDirection:'column',gap:4}}>
                  <span style={{fontSize:9.5,fontWeight:600,color:'#a7abb2',letterSpacing:'.05em',textTransform:'uppercase'}}>Platform</span>
                  <select value={retargetPlatform} onChange={e=>{setRetargetPlatform(e.target.value); setRetargetMsg(null)}} className="cr-input" style={{width:'100%',padding:'7px 9px',fontSize:11}}>
                    {PLAT_LIST.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </label>
              </div>
              <label style={{display:'flex',flexDirection:'column',gap:4}}>
                <span style={{fontSize:9.5,fontWeight:600,color:'#a7abb2',letterSpacing:'.05em',textTransform:'uppercase'}}>AI Editor</span>
                <select value={retargetModel} onChange={e=>{setRetargetModel(e.target.value); setRetargetMsg(null)}} className="cr-input" style={{width:'100%',padding:'7px 9px',fontSize:11}}>
                  {Object.entries(EDITORIAL_MODEL_META).map(([key, meta]) => (
                    <option key={key} value={key}>{meta.display}</option>
                  ))}
                </select>
              </label>
              <button className="btn-mint" onClick={handleRegenerateSavedCopy} disabled={retargetLoading}
                style={{width:'100%',padding:8,fontSize:10.5,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700,opacity:retargetLoading?0.65:1}}>
                {retargetLoading ? 'Generating...' : 'Generate New Copy'}
              </button>
              {retargetMsg && (
                <div className={`sched-msg sched-msg-${retargetMsg.type}`} style={{marginTop:0}}>
                  <span className="sched-msg-icon">{retargetMsg.type === 'error' ? '!' : retargetMsg.type === 'success' ? 'OK' : 'i'}</span>
                  <span>{retargetMsg.text}</span>
                </div>
              )}
            </div>
          )}

          {/* Why boxes */}
          {mode === 'multimedia' && (
            <div style={{background:'rgba(255,255,255,.04)',border:'1px solid rgba(255,255,255,.08)',borderRadius:10,padding:'10px 12px',display:'flex',flexDirection:'column',gap:9}}>
              <div>
                <p dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Why this media brand?</p>
                <p dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:13,color:'#c8cdd8',lineHeight:1.55}}>{card.mediaReason||'—'}</p>
              </div>
              <div style={{borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:9}}>
                <p dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Why this platform?</p>
                <p dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:13,color:'#c8cdd8',lineHeight:1.55}}>{card.platReason||'—'}</p>
              </div>
            </div>
          )}

          {/* Copy */}
          <div>
            <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:6}}>
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',letterSpacing:'.06em',textTransform:'uppercase'}}>Generated Copy</p>
              <button onClick={()=>{ setEditing(e=>!e) }} style={{fontSize:10,fontWeight:600,color:'#00d4a0',background:'none',border:'none',cursor:'pointer',padding:'2px 6px',borderRadius:5,transition:'background .18s'}}
                onMouseEnter={e=>e.currentTarget.style.background='rgba(0,212,160,.1)'} onMouseLeave={e=>e.currentTarget.style.background='none'}>
                {editing ? 'Done' : 'Edit'}
              </button>
            </div>
            {card.isGenerating
              ? (
                <div style={{background:'rgba(155,114,245,.06)',border:'1px solid rgba(155,114,245,.22)',borderRadius:8,padding:'14px 14px'}}>
                  <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:10}}>
                    <span className="spinner" style={{width:13,height:13,border:'1.5px solid rgba(155,114,245,.25)',borderTopColor:'#9b72f5'}}/>
                    <span style={{fontSize:12,color:'#c8cdd8'}}>Generating 3 platform-specific variants — please wait…</span>
                  </div>
                  <div style={{height:6,borderRadius:4,background:'rgba(255,255,255,.06)',overflow:'hidden'}}>
                    <div style={{height:'100%',width:`${genPct}%`,borderRadius:4,background:'linear-gradient(90deg,#9b72f5,#00d4a0)',transition:'width .25s ease-out'}}/>
                  </div>
                  <div style={{marginTop:6,fontSize:10.5,color:'#a7abb2',textAlign:'right'}}>{genPct}%</div>
                </div>
              )
              : editing
              ? <textarea dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} value={copyText} onChange={e=>{ setSelectedVariant(null); setCopyText(e.target.value) }} style={{width:'100%',minHeight:80,background:'rgba(0,212,160,.05)',border:'1px solid rgba(0,212,160,.45)',borderRadius:8,padding:'8px 10px',fontSize:13,color:'#eeeae2',lineHeight:1.65,fontFamily:isPersian?"'Vazirmatn','Inter',sans-serif":'Inter,sans-serif',resize:'vertical',boxShadow:'0 0 0 3px rgba(0,212,160,.08)',outline:'none'}}/>
              : <div id="preview-copy" ref={copyRef} dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:13,color:'#c8cdd8',lineHeight:1.65}}>{selectedCopy}</div>
            }
          </div>

          {/* Variant picker */}
          {(card.variants||[]).length > 1 && (
            <div>
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',letterSpacing:'.06em',textTransform:'uppercase',marginBottom:6}}>Variants — pick one</p>
              <div style={{display:'flex',flexDirection:'column',gap:6}}>
                {card.variants.map((v,i)=>(
                  <button key={i} type="button" onClick={()=>chooseVariant(v, i)}
                    style={{cursor:'pointer',padding:'7px 10px',borderRadius:7,
                      border:`1px solid ${i===selectedVariant?pc+'70':'rgba(255,255,255,.08)'}`,
                      background:i===selectedVariant?pc+'14':'rgba(255,255,255,.03)',textAlign:isPersian?'right':'left',width:'100%',
                      direction:isPersian?'rtl':'ltr',fontFamily:isPersian?"'Vazirmatn','Inter',sans-serif":'Inter,sans-serif'}}>
                    {v.label && (
                      <span style={{display:'inline-block',fontSize:8.5,fontWeight:700,letterSpacing:'.07em',textTransform:'uppercase',
                        padding:'1.5px 6px',borderRadius:4,marginBottom:4,
                        background:(i===selectedVariant?pc:'#a7abb2')+'1f',
                        color:i===selectedVariant?pc:'#a7abb2',
                        border:`1px solid ${(i===selectedVariant?pc:'#a7abb2')}40`}}>{v.label}</span>
                    )}
                    <div dir={isPersian?'rtl':'ltr'} className={isPersian?'persian-content':''} style={{fontSize:12,lineHeight:1.5,color:i===selectedVariant?'#eeeae2':'#a7abb2',
                      display:'-webkit-box',WebkitLineClamp:2,WebkitBoxOrient:'vertical',overflow:'hidden'}}>
                      {v.copy}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Hashtags */}
          <div dir={isPersian?'rtl':'ltr'} style={{display:'flex',flexWrap:'wrap',gap:5,direction:isPersian?'rtl':'ltr'}}>
            {hashtagsState.map(h=>(
              <span key={h} style={{fontSize:10.5,fontWeight:600,color:pc}}>{h}</span>
            ))}
          </div>

          {/* Source link */}
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#a7abb2" strokeWidth="1.8" strokeLinecap="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
            <a href={card.link||'#'} target="_blank" rel="noreferrer" style={{fontSize:11,color:'#3d8ef0',textDecoration:'none',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{card.link&&card.link!=='#'?'View source article →':'No link available'}</a>
          </div>

          {/* Status */}
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            <span style={{fontSize:11,color:'#a7abb2'}}>Status:</span>
            <span className={`sbadge ${STATUS_CLASSES[displayStatus]||'sb-ready'}`}>{STATUS_LABELS[displayStatus]||'Ready'}</span>
          </div>
        </div>

        {/* Footer actions */}
        <div style={{padding:'14px 16px',borderTop:'1px solid rgba(255,255,255,.07)',display:'flex',flexDirection:'column',gap:8,flexShrink:0}}>
          {mode === 'multimedia' ? (
            <>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-mint" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700,opacity:isApprovalBusy?0.65:1}} onClick={handleApprove} disabled={actionBusy}>{isApprovalBusy && <ButtonSpinner />}{approveLabel}</button>
                <button className={showImage?'btn-mint':'btn-ghost'} style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:showImage?700:400}} onClick={()=>{setShowImage(s=>!s);setShowSchedule(false)}}>{showImage?'▲ Hide':'Need Image'}</button>
              </div>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={openSchedule}>Schedule</button>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',opacity:isSaveBusy?0.65:1}} onClick={handleSaveForLater} disabled={saveLabel!=='Save for Later'||actionBusy}>{isSaveBusy && <ButtonSpinner />}{saveLabel}</button>
              </div>
            </>
          ) : (
            <>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-mint" style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700}} onClick={handleConfirmSaved}>{confirmLabel}</button>
                <button className={showImage?'btn-mint':'btn-ghost'} style={{flex:1,padding:9,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:showImage?700:400}} onClick={()=>{setShowImage(s=>!s);setShowSchedule(false)}}>{showImage?'▲ Hide':'Generate Image'}</button>
              </div>
              <div style={{display:'flex',gap:8}}>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={openSchedule}>Schedule</button>
                <button className="btn-ghost" style={{flex:1,padding:8,fontSize:11,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={handleDiscard} disabled={discardLabel!=='Discard'}>{discardLabel}</button>
              </div>
            </>
          )}

          {actionMsg && (
            <div key={`${actionMsg.type}:${actionMsg.text}`} className={`action-status action-status-${actionMsg.type}`}>
              {actionMsg.type === 'info' ? <ButtonSpinner /> : <span className="action-status-icon">{actionMsg.type === 'success' ? '✓' : '!'}</span>}
              <span>{actionMsg.type === 'success' && actionMsg.text === 'Updating Google Sheets...' ? 'Google Sheets updated.' : actionMsg.text}</span>
            </div>
          )}
          {sheetSyncMsg && (
            <div className={`action-status action-status-${sheetSyncMsg.type}`}>
              {sheetSyncMsg.type === 'info' ? <ButtonSpinner /> : <span className="action-status-icon">{sheetSyncMsg.type === 'success' ? '✓' : '!'}</span>}
              <span>{sheetSyncMsg.type === 'success' && sheetSyncMsg.text === 'Updating Google Sheets...' ? 'Google Sheets updated.' : sheetSyncMsg.text}</span>
            </div>
          )}

          {/* Image section */}
          {showImage && (
            <div ref={imageSectionRef} style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase'}}>Image Direction <span style={{fontWeight:400,textTransform:'none',letterSpacing:0}}>(optional)</span></p>
              <textarea value={imagePrompt} onChange={e=>setImagePrompt(e.target.value)} placeholder={tr('Describe what you want in the image… e.g. show the wolf mascot, use a comparison table layout')} rows={2} className="cr-input" style={{width:'100%',padding:'7px 10px',fontSize:11,resize:'vertical',minHeight:36}} />
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:4,letterSpacing:'.06em',textTransform:'uppercase',marginTop:4}}>Reference Images <span style={{fontWeight:400,textTransform:'none',letterSpacing:0}}>(optional, max {maxReferenceImages})</span></p>
              <label style={{display:'inline-flex',alignItems:'center',gap:5,padding:'6px 12px',fontSize:10,fontWeight:600,borderRadius:8,border:'1px solid rgba(155,114,245,.35)',background:'rgba(155,114,245,.08)',color:'#9b72f5',cursor:'pointer',letterSpacing:'.04em'}}>
                + Add Images
                <input type="file" accept="image/*" multiple style={{display:'none'}} onChange={e=>{
                  const files = Array.from(e.target.files).slice(0, maxReferenceImages - refImages.length)
                  if (!files.length) return
                  Promise.all(files.map(f=>new Promise(res=>{const r=new FileReader();r.onload=()=>res({name:f.name,b64:r.result,preview:r.result});r.readAsDataURL(f)}))).then(imgs=>setRefImages(prev=>[...prev,...imgs].slice(0,maxReferenceImages)))
                  e.target.value = ''
                }} />
              </label>
              {refImages.length > 0 && (
                <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
                  {refImages.map((img,i) => (
                    <div key={i} style={{position:'relative',width:52,height:52}}>
                      <img src={img.preview} alt={img.name} style={{width:52,height:52,objectFit:'cover',borderRadius:6,border:'1px solid rgba(255,255,255,.1)'}} />
                      <button onClick={()=>setRefImages(prev=>prev.filter((_,j)=>j!==i))} style={{position:'absolute',top:-4,right:-4,width:16,height:16,borderRadius:'50%',border:'none',background:'#ef4455',color:'#fff',fontSize:9,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',lineHeight:1,padding:0}}>×</button>
                    </div>
                  ))}
                </div>
              )}
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase',marginTop:4}}>Image Generation Model</p>
              <select value={imageModel} onChange={e=>{
                const nextModel = IMAGE_MODEL_OPTIONS.find(option => option.value === e.target.value)
                setImageModel(e.target.value)
                setRefImages(previous => previous.slice(0, nextModel?.maxReferences || 3))
              }} className="cr-input" style={{width:'100%',padding:'7px 10px',fontSize:11}}>
                {IMAGE_MODEL_OPTIONS.map(m => <option key={m.value} value={m.value}>{m.label} - {m.tier}</option>)}
              </select>
              <div className="image-model-summary">
                <span className={`image-model-tier image-model-tier-${selectedImageModel.tier.toLowerCase().replace(/\s+/g, '-')}`}>{selectedImageModel.tier}</span>
                <span>{selectedImageModel.description}</span>
              </div>
              <button onClick={handleGenerateImage} disabled={imgLoading} aria-busy={imgLoading}
                style={{width:'100%',padding:9,fontSize:11,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',border:'none',borderRadius:9,cursor:imgLoading?'wait':'pointer',background:'linear-gradient(135deg,#f0a040,#e08030)',color:'#171c26',opacity:imgLoading?0.6:1,transition:'opacity .18s'}}>
                {imgLoading ? 'Generating...' : 'Create Image'}
              </button>
              {imageGenError && (
                <div className="action-status action-status-error">
                  <span className="action-status-icon">!</span>
                  <span>{imageGenError}</span>
                </div>
              )}
              {generatedImg && (
                <div style={{display:'flex',flexDirection:'column',gap:8}}>
                  <img src={`data:image/png;base64,${generatedImg}`} alt="Generated" style={{width:'100%',borderRadius:9,border:'1px solid rgba(255,255,255,.1)',display:'block'}} />
                  <div style={{display:'flex',gap:6}}>
                    <button className="btn-mint" style={{flex:1,padding:8,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase',fontWeight:700,opacity:(isImageActionBusy||telegramConfirmationDelayed)?0.65:1}} onClick={handleApproveImage} disabled={actionBusy||telegramConfirmationDelayed}>{isImageActionBusy && <ButtonSpinner />}{approveImgLabel}</button>
                    <button className="btn-ghost" style={{flex:1,padding:8,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase',opacity:imgLoading?0.6:1}} onClick={handleGenerateImage} disabled={imgLoading}>{imgLoading ? 'Generating...' : 'Regenerate'}</button>
                    <button className="btn-ghost" style={{flex:1,padding:8,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase'}} onClick={handleDownloadImage} title={tr('Download PNG')}>{tr('Download')}</button>
                  </div>
                  {actionMsg && (
                    <div key={`${actionMsg.type}:${actionMsg.text}`} className={`action-status action-status-${actionMsg.type}`} style={{marginTop:2}}>
                      {actionMsg.type === 'info' ? <ButtonSpinner /> : <span className="action-status-icon">{actionMsg.type === 'success' ? '✓' : '!'}</span>}
                      <span>{actionMsg.text}</span>
                    </div>
                  )}
                </div>
              )}
              {aiBrief && (
                <div style={{display:'flex',flexDirection:'column',gap:6}}>
                  <button onClick={()=>setShowAiBrief(s=>!s)} className="btn-ghost"
                    style={{width:'100%',padding:7,fontSize:10,letterSpacing:'.06em',textTransform:'uppercase'}}>
                    {showAiBrief ? 'Hide AI Brief ▴' : 'Show AI Brief ▾'}
                  </button>
                  {showAiBrief && (
                    <div style={{display:'flex',flexDirection:'column',gap:8}}>
                      <div>
                        <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:5,letterSpacing:'.06em',textTransform:'uppercase'}}>Visual Brief (JSON)</p>
                        <pre style={{margin:0,padding:'8px 10px',fontSize:10,lineHeight:1.5,color:'#c8cdd8',background:'rgba(0,0,0,.3)',border:'1px solid rgba(255,255,255,.08)',borderRadius:8,overflowX:'auto',whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{JSON.stringify(aiBrief.brief, null, 2)}</pre>
                      </div>
                      <div>
                        <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:5,letterSpacing:'.06em',textTransform:'uppercase'}}>Assembled Prompt</p>
                        <pre style={{margin:0,padding:'8px 10px',fontSize:10,lineHeight:1.5,color:'#c8cdd8',background:'rgba(0,0,0,.3)',border:'1px solid rgba(255,255,255,.08)',borderRadius:8,overflowX:'auto',whiteSpace:'pre-wrap',wordBreak:'break-word'}}>{aiBrief.prompt}</pre>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Schedule section */}
          {showSchedule && (
            <div style={{display:'flex',flexDirection:'column',gap:8,borderTop:'1px solid rgba(255,255,255,.06)',paddingTop:10}}>
              <p style={{fontSize:10,fontWeight:600,color:'#a7abb2',marginBottom:7,letterSpacing:'.06em',textTransform:'uppercase'}}>Schedule Post</p>
              {generatedImg && (
                <div style={{display:'flex',alignItems:'center',gap:8,padding:'6px 8px',borderRadius:8,background:'rgba(0,212,160,.06)',border:'1px solid rgba(0,212,160,.2)'}}>
                  <img src={`data:image/png;base64,${generatedImg}`} alt="Generated" style={{width:44,height:44,borderRadius:6,objectFit:'cover',flexShrink:0}} />
                  <span style={{fontSize:11,color:'#00d4a0'}}>Image will be attached to this post</span>
                </div>
              )}
              <SchedulePicker date={schedDate} time={schedTime} onDateChange={(v)=>{setSchedDate(v); setSchedMsg(null)}} onTimeChange={(v)=>{setSchedTime(v); setSchedMsg(null)}}
                onConfirm={mode === 'multimedia' ? handleSchedule : handleConfirmScheduleSaved}
                confirmLabel={tr(mode === 'multimedia' ? 'Confirm Schedule' : scheduleSavedLabel)}
                platform={schedPlatform} onPlatformChange={(p)=>{setSchedPlatform(p); setSchedMsg(null)}} platformOptions={['X','Telegram']} />
              {schedMsg && (
                <div className={`sched-msg sched-msg-${schedMsg.type}`}>
                  <span className="sched-msg-icon">{schedMsg.type === 'error' ? '⚠' : schedMsg.type === 'success' ? '✓' : 'ℹ'}</span>
                  <span>{schedMsg.text}</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
