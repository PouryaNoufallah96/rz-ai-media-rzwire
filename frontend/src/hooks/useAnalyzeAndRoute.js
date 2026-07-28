import { useCallback } from 'react'
import { useMmStore, API_BASE, MM_SOURCES, SRC_COLORS, EDITORIAL_MODEL_META, mkey, anyPromoOn } from '../store/mmStore'
import { useLanguageStore } from '../store/languageStore'
import { fetchRSS, parseRSS, filterByRecency, timeAgo } from '../utils/rss'
import { preScore } from '../utils/scoring'

// Gzip-compress the JSON body before sending (mirrors the gzip the backend
// already applies to its responses) — large filter payloads (100s of KB of
// articles) shrink ~70-85%, avoiding the same MTU-stall risk on upload.
// Falls back to plain JSON on browsers without CompressionStream.
async function postJSON(url, obj) {
  if (typeof CompressionStream !== 'undefined') {
    try {
      const bytes  = new TextEncoder().encode(JSON.stringify(obj))
      const stream = new Blob([bytes]).stream().pipeThrough(new CompressionStream('gzip'))
      const body   = await new Response(stream).arrayBuffer()
      return await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Encoding': 'gzip' },
        body,
      })
    } catch (_) { /* fall through to uncompressed */ }
  }
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj),
  })
}

export function useAnalyzeAndRoute() {
  const store = useMmStore()

  const run = useCallback(async (topics) => {
    const { selectedSources, selectedMedia, selectedPlatforms, selectedModels,
            recencyHours, filterMode, testMode, enrichArticles, setProgress, setAnalyzing,
            setErrorMsg, setModelLanes, setPlatformLanes, setLastShortlist,
            setEditorial, setMmReport, promoMode, promoPrompts,
            useTelegramSources, selectedTelegramSources, telegramSortMode, telegramTopN,
            setTelegramLanes } = useMmStore.getState()
    const language = useLanguageStore.getState().language

    // ── Promo-only rule ──
    // If ANY selected brand has Promo Copy ON, the whole run is promo-only:
    // news sources, filtering, and the editorial pipeline are all skipped.
    // Only promo brands run; a brand with promo OFF can't mix into a promo run.
    const promoActive = anyPromoOn(useMmStore.getState())
    let promoBrands, editorialBrands
    if (promoActive) {
      promoBrands = selectedMedia.filter(m => promoMode[m] && promoPrompts[m]?.trim())
      editorialBrands = []                       // no news at all in a promo run
      if (!promoBrands.length) {
        setErrorMsg('Promo mode is on — enter a prompt for at least one brand, or turn Promo Copy off to run news.')
        return
      }
    } else {
      promoBrands = []
      editorialBrands = selectedMedia.filter(m => true)
    }

    if (!editorialBrands.length && !promoBrands.length) { setErrorMsg('Select at least one media brand.'); return }
    if (!promoActive && editorialBrands.length && !selectedSources.length && !useTelegramSources) {
      setErrorMsg('Select at least one source.'); return
    }
    if (!promoActive && useTelegramSources && !selectedTelegramSources.length) {
      setErrorMsg('Select at least one Telegram source.'); return
    }
    if (!promoActive && useTelegramSources && telegramSortMode === 'keywords') {
      const kwCount = (topics || '').split(',').map(s => s.trim()).filter(Boolean).length
      if (kwCount < 2) { setErrorMsg('Add at least 2 keywords to use Telegram keyword matching.'); return }
    }
    if (!selectedMedia.length)   { setErrorMsg('Select at least one media brand.'); return }

    setAnalyzing(true)
    setErrorMsg('')

    if (topics && topics.trim()) {
      fetch(`${API_BASE}/api/account/log-keywords`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topics, brands: selectedMedia }),
      }).catch(() => {})
    }

    try {
      const sourceCounts = {}
      let allArticles = [], tooOldCount = 0, recent = [], tooOldArticles = []
      let shortlistPayload = [], allTracked = [], preResult = null
      let telegramRanked = [], telegramErrors = {}, telegramFetchedTotal = 0
      const editorial = {}
      setTelegramLanes({})

      // ── Promo brands: generate ideas (no articles needed) ──
      if (promoBrands.length) {
        setProgress(5, `Generating promo ideas for ${promoBrands.length} brand${promoBrands.length>1?'s':''}…`)
        let promoErrorShown = false
        for (const brand of promoBrands) {
          for (const modelKey of selectedModels) {
            try {
              const res = await fetch(`${API_BASE}/api/promo/generate-ideas`, {
                method:'POST', headers:{'Content-Type':'application/json'},
                body:JSON.stringify({ brand, prompt:promoPrompts[brand], modelKey, language })
              })
              const data = await res.json().catch(()=>({}))
              if (!res.ok || data.error) {
                const reason = data.error || `HTTP ${res.status}`
                console.warn(`Promo ${brand}/${modelKey}:`, reason)
                // Surface the first error to the user so failures aren't silent empty lanes.
                if (!promoErrorShown) { setErrorMsg(`Promo ${brand} (${modelKey}): ${reason}`); promoErrorShown = true }
                continue
              }
              const meta = EDITORIAL_MODEL_META[modelKey]
              const existing = useMmStore.getState().modelLanes[modelKey] || {}
              const lanes = { ...existing }
              if (!lanes[brand]) lanes[brand] = []
              ;(data.ideas||[]).forEach((idea, i) => {
                lanes[brand].push({
                  id:`${modelKey}-${mkey(brand)}-promo-${i}`,
                  _modelKey:modelKey, _modelDisplay:meta?.display, _modelColor:meta?.color,
                  media:brand, platform:'suggested', source:'Promo', initials:'PR', srcColor:'#f0a040',
                  headline:idea.title||'', copy:idea.description||'',
                  selectionReason:'User-requested promo post', mediaReason:'Promo', platReason:'',
                  hashtags:[], suitability:10, impact:8, virality:7, sentiment:'Neutral',
                  link:'#', status:'ready', timeAgo:'Now',
                  lowConfidence:false, lowConfidenceReason:'',
                  _isPromo:true, _promoPrompt:promoPrompts[brand],
                })
              })
              setModelLanes({ ...useMmStore.getState().modelLanes, [modelKey]: lanes })
            } catch(e) { console.warn(`Promo ${brand}/${modelKey} failed:`, e.message) }
          }
        }
      }

      // ── Editorial brands: full RSS → Filter → AI pipeline ──
      if (editorialBrands.length) {
        if (useTelegramSources) {
          setProgress(5, `Fetching Telegram news from ${selectedTelegramSources.length} source${selectedTelegramSources.length===1?'':'s'}...`)
          const res = await fetch(`${API_BASE}/api/telegram/rank`, {
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
              channels:selectedTelegramSources,
              hours:recencyHours,
              sortMode:telegramSortMode,
              topN:telegramTopN,
              topics,
            })
          })
          const data = await res.json().catch(()=>({}))
          if (!res.ok || data.error) throw new Error(data.error || `Telegram ranking failed (${res.status})`)
          telegramRanked = data.articles || []
          telegramErrors = data.errors || {}
          telegramFetchedTotal = data.fetchedTotal || telegramRanked.length
          sourceCounts.Telegram = telegramRanked.length
          if (!telegramRanked.length && !selectedSources.length) throw new Error(`No Telegram posts in the last ${recencyHours}h. Try a wider time range or more Telegram sources.`)
          const telegramCopyModel = selectedModels[0] || 'gpt'
          const telegramCopyModelMeta = EDITORIAL_MODEL_META[telegramCopyModel] || EDITORIAL_MODEL_META.gpt
          const tgLanes = {}
          editorialBrands.forEach(brand => {
            tgLanes[brand] = telegramRanked.map((a, rank) => {
              const srcCol = SRC_COLORS[a.source] || '#24a1de'
              const init = (a.source || 'TG').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()
              return {
                id:`tg-${mkey(brand)}-${a.channel || 'source'}-${a.messageId || rank}`,
                _modelKey:telegramCopyModel, _modelDisplay:telegramCopyModelMeta.display, _modelColor:telegramCopyModelMeta.color,
                _isTelegramSource:true,
                language,
                media:brand, platform:'suggested', source:a.source || 'Telegram', initials:init, srcColor:srcCol,
                headline:a.title || '', copy:a.desc || a.telegramText || '',
                selectionReason:telegramSortMode === 'keywords'
                  ? 'Matched selected keywords from Telegram source posts.'
                  : telegramSortMode === 'views_per_source'
                    ? 'Top-viewed post from each source first, then the next highest-viewed posts.'
                    : telegramSortMode === 'latest_per_source'
                      ? 'Newest post from each source first, then the next newest posts.'
                  : telegramSortMode === 'latest'
                    ? 'Ranked by Telegram publish date.'
                    : 'Ranked by Telegram view count.',
                mediaReason:'Telegram source discovery', platReason:'', hashtags:[],
                suitability:Math.max(1, Math.min(10, Math.round(((a.keywordScore || 0.7) * 10)) || 7)),
                impact:Math.max(1, Math.min(10, Math.round(((a.views || 0) / 1000)) || 6)),
                virality:Math.max(1, Math.min(10, Math.round(((a.views || 0) / 1000)) || 6)),
                sentiment:'Neutral',
                link:a.link || '#', status:'ready',
                timeAgo:a.pubDate ? timeAgo(a.pubDate) : 'Recent',
                lowConfidence:false, lowConfidenceReason:'',
                views:a.views || null, viewsLabel:a.viewsLabel || '',
                matchedKeywords:a.matchedKeywords || [],
              }
            })
          })
          setTelegramLanes(tgLanes)
        }

        if (!selectedSources.length) {
          allTracked = telegramRanked.map(a => ({ ...a, _pipelineStatus:'telegram_ranked', _scores:null, _keywords:a.matchedKeywords||null, _routing:null }))
        } else {
        // Phase 1: RSS Fetch
        selectedSources.forEach(s => { sourceCounts[s] = 0 })
        let fetchedCount = 0
        const perSource = await Promise.allSettled(selectedSources.map(async name => {
          const url = MM_SOURCES[name]
          if (!url) return []
          try {
            const xml  = await fetchRSS(url)
            const arts = parseRSS(xml, name)
            sourceCounts[name] = arts.length
            return arts.slice(0, 15)
          } catch(e) {
            console.warn(`Skip ${name}:`, e.message)
            return []
          } finally {
            fetchedCount++
            setProgress(5 + Math.round((fetchedCount / selectedSources.length) * 35), `Fetched ${fetchedCount}/${selectedSources.length} sources…`)
          }
        }))
        allArticles = perSource.flatMap(r => r.status === 'fulfilled' ? r.value : [])
        if (!allArticles.length && !telegramRanked.length) throw new Error('Could not load any feeds. Check your connection.')

        tooOldCount = allArticles.length - allArticles.filter(a => {
          if (!a.pubDate) return true
          const t = Date.parse(a.pubDate)
          return isNaN(t) ? true : t >= Date.now() - recencyHours * 3600000
        }).length

        recent = filterByRecency(allArticles, recencyHours)
        if (!recent.length && !telegramRanked.length) throw new Error(`No articles in the last ${recencyHours}h. Try a wider time range.`)

        tooOldArticles = allArticles
          .filter(a => a.pubDate && (() => { const t = Date.parse(a.pubDate); return !isNaN(t) && t < Date.now() - recencyHours*3600000 })())
          .map(a => ({ ...a, _pipelineStatus:'too_old', _scores:null, _keywords:null, _routing:null }))

        if (!recent.length && telegramRanked.length) {
          allTracked = telegramRanked.map(a => ({ ...a, _pipelineStatus:'telegram_ranked', _scores:null, _keywords:a.matchedKeywords||null, _routing:null }))
        }

        if (recent.length) {
        // Phase 2: Filter
        if (filterMode === 'openai_embedding') {
          setProgress(48, `Running OpenAI Embedding pipeline on ${recent.length} articles…`)
          const r = await postJSON(`${API_BASE}/api/filter/pipeline`, { articles:recent, selectedMedia:editorialBrands, topics, recencyHours })
          if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e?.error||`Filter failed (${r.status})`) }
          const fd = await r.json()
          if (!fd.shortlist?.length) throw new Error('OpenAI Embedding: no articles passed. Try wider range.')
          shortlistPayload = fd.shortlist; allTracked = fd.all_tracked||[]
          setLastShortlist(shortlistPayload)
          preResult = { rejected:{duplicate:(fd.stats?.dropped_dup_cheap||0)+(fd.stats?.dropped_clustered||0),noMediaFit:fd.stats?.no_media_fit||0,lowScore:fd.stats?.cap_exceeded||0}, passed:fd.stats?.embedded||0, shortlisted:shortlistPayload, allTracked }

        } else if (filterMode === 'deepseek_preprocess') {
          setProgress(48, `Sending ${recent.length} articles to DeepSeek V4 Flash…`)
          const r = await postJSON(`${API_BASE}/api/filter/deepseek`, { articles:recent, selectedMedia:editorialBrands, topics, recencyHours })
          if (!r.ok) { const e = await r.json().catch(()=>({})); throw new Error(e?.error||`DeepSeek filter failed (${r.status})`) }
          const fd = await r.json()
          if (!fd.shortlist?.length) throw new Error('DeepSeek Pre-Process: no articles passed.')
          shortlistPayload = fd.shortlist; allTracked = fd.all_tracked||[]
          setLastShortlist(shortlistPayload)
          preResult = { rejected:{duplicate:fd.stats?.dropped_dup_cheap||0,noMediaFit:0,lowScore:0}, passed:fd.stats?.sent_to_deepseek||0, shortlisted:shortlistPayload, allTracked }

        } else {
          if (filterMode !== 'test') {
            setProgress(45, 'Loading semantic model…')
            if (window._semRouter?._initPromise) await window._semRouter._initPromise
            setProgress(50, `Embedding ${recent.length} articles…`)
            if (window._semRouter?.embedArticles) await window._semRouter.embedArticles(recent)
          }
          setProgress(58, `Pre-scoring ${recent.length} articles…`)
          await new Promise(r => setTimeout(r, 20))
          preResult = preScore(recent, editorialBrands, topics)
          allTracked = preResult.allTracked
          const { shortlisted } = preResult
          if (!shortlisted.length) throw new Error('All articles filtered. Try wider range or more sources.')

          const isTest = testMode
          let articlesForAI = shortlisted
          if (isTest) {
            const seen=new Set(), picked=[]
            for (const brand of editorialBrands) {
              shortlisted.filter(a=>a._routing?.primary_media===brand).slice(0,3)
                .forEach(a=>{ if(!seen.has(a.title)){seen.add(a.title);picked.push(a)} })
            }
            articlesForAI = picked.length ? picked : shortlisted.slice(0, 3)
          }
          shortlistPayload = articlesForAI.map((a,i) => ({
            input_index: i,
            title:   isTest ? a.title.split(' ').slice(0,6).join(' ') : a.title,
            source:  a.source, link: a.link||'',
            desc:    isTest ? (a.desc||'').split(' ').slice(0,10).join(' ') : (a.desc||'').slice(0,220),
            pubDate: a.pubDate||'',
            scores: {
              final:      Math.round(a._scores?.final||0),  virality: Math.round(a._scores?.virality||0),
              freshness:  Math.round(a._scores?.freshness||0), authority: Math.round(a._scores?.authority||0),
              userTopic:  Math.round(a._scores?.userTopic||0), confidence: Math.round(a._scores?.confidence||0),
            },
            routing: { primary_media:a._routing?.primary_media||'', secondary_media:a._routing?.secondary_media||'' },
          }))
          setLastShortlist(preResult.shortlisted)
        }

        if (window.innerWidth <= 768) {
          const bc = {}
          shortlistPayload = shortlistPayload.filter(a => { const b=a.routing?.primary_media||'_'; bc[b]=(bc[b]||0)+1; return bc[b]<=10 })
        }

        setProgress(62, `Sending ${shortlistPayload.length} articles to ${selectedModels.length} AI editor${selectedModels.length===1?'':'s'}…`)

        // Phase 3: Editorial AI (streamed)
        // Source cards stay in their original English form. Persian is applied on
        // demand with the card's Translate button and is mandatory after routing.
        const editRes = await postJSON(`${API_BASE}/api/ai/editorial-select`, { shortlist:shortlistPayload, selectedMedia:editorialBrands, selectedPlatforms, selectedModels, topics, testMode, enrichArticles, language:'en' })
        if (!editRes.ok) { const e = await editRes.json().catch(()=>({})); throw new Error(e?.error||`Editorial AI failed (${editRes.status})`) }

        const lastShortlist = useMmStore.getState().lastShortlist

        const buildLanesForModel = (key, data) => {
          const meta = EDITORIAL_MODEL_META[key], brands = data?.brands||{}
          const existingLanes = useMmStore.getState().modelLanes[key] || {}
          const lanes = { ...existingLanes }
          editorialBrands.forEach(brand => {
            lanes[brand] = [];
            (brands[brand]||[]).forEach((a,rank) => {
              const src = lastShortlist[a.input_index]||{}, srcCol=SRC_COLORS[a.source]||'#7a8499'
              const init=(a.source||'').split(' ').map(w=>w[0]).join('').slice(0,2).toUpperCase()
              lanes[brand].push({
                id:`${key}-${mkey(brand)}-${a.input_index}-${rank}`,
                _modelKey:key, _modelDisplay:meta?.display, _modelColor:meta?.color,
                media:brand, platform:'suggested', source:a.source||'', initials:init, srcColor:srcCol,
                headline:a.title||'', copy:a.copy||'', selectionReason:a.selection_reason||'',
                mediaReason:a.selection_reason||'', platReason:'', hashtags:a.hashtags||[],
                suitability:Math.round((a.suitability_score||70)/10), impact:Math.round((a.impact_score||70)/10),
                virality:Math.round((a.virality_score||60)/10), sentiment:'Neutral',
                link:a.source_url||src.link||'#', status:'ready',
                timeAgo:src.pubDate?timeAgo(src.pubDate):src.pub_date?timeAgo(src.pub_date):'Recent',
                lowConfidence:false, lowConfidenceReason:'',
                language,
              })
            })
          })
          return lanes
        }

        const total = selectedModels.length
        let completed = 0
        const reader = editRes.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        while (true) {
          const { done, value } = await reader.read()
          if (value) buf += decoder.decode(value, { stream: true })
          let nl
          while ((nl = buf.indexOf('\n')) >= 0) {
            const line = buf.slice(0, nl).trim()
            buf = buf.slice(nl + 1)
            if (!line) continue
            const entry = JSON.parse(line)
            const [key, data] = Object.entries(entry)[0]
            editorial[key] = data
            completed++
            setProgress(62 + Math.round((completed/total)*30), `${EDITORIAL_MODEL_META[key]?.display||key} ready (${completed}/${total})…`)
            setModelLanes({ ...useMmStore.getState().modelLanes, [key]: buildLanesForModel(key, data) })
          }
          if (done) break
        }
        }
        }
      }

      setEditorial(editorial)

      const platformLanes = {}
      selectedMedia.forEach(brand => { platformLanes[brand]={}; selectedPlatforms.forEach(p=>{platformLanes[brand][p]=[]}) })
      setPlatformLanes(platformLanes)

      // Build report — count ACTUAL promo cards that made it into the lanes, not a
      // fabricated number (the old arithmetic lied: it claimed "4 shortlisted" even
      // when every promo fetch failed and the lanes were empty).
      const perMedia = {}
      selectedMedia.forEach(m=>{perMedia[m]=0})
      Object.values(editorial).forEach(md => { const bm=md.brands||{}; Object.entries(bm).forEach(([brand,arts]) => { if(perMedia.hasOwnProperty(brand)) perMedia[brand]+=(arts?.length||0) }) })
      let actualPromoTotal = 0
      promoBrands.forEach(m => {
        const n = selectedModels.reduce((s,k) => s + (useMmStore.getState().modelLanes[k]?.[m]?.length||0), 0)
        perMedia[m] = (perMedia[m]||0) + n
        actualPromoTotal += n
      })
      let actualTelegramTotal = 0
      selectedMedia.forEach(m => {
        const n = useMmStore.getState().telegramLanes[m]?.length || 0
        perMedia[m] = (perMedia[m]||0) + n
        actualTelegramTotal += n
      })
      const shortlisted = preResult?.shortlisted || shortlistPayload
      const trackedTelegram = telegramRanked.map(a => ({ ...a, _pipelineStatus:'telegram_ranked', _scores:null, _keywords:a.matchedKeywords||null, _routing:null }))
      setMmReport({
        runAt:Date.now(), selectedSources:[...selectedSources], selectedMedia:[...selectedMedia],
        telegramSources: useTelegramSources ? [...selectedTelegramSources] : [],
        telegramSortMode, telegramErrors,
        recencyHours, sourceCounts, fetchedTotal:allArticles.length + telegramFetchedTotal, tooOld:tooOldCount,
        afterRecency:recent.length, rejected:preResult?.rejected||{duplicate:0,noMediaFit:0,lowScore:0},
        shortlistedCount:shortlistPayload.length + actualPromoTotal + actualTelegramTotal, perMedia, filterMode,
        allArticles:[...tooOldArticles,...allTracked,...trackedTelegram],
      })

      setProgress(100, 'Done!')
      setTimeout(() => useMmStore.getState().setProgress(0,''), 1800)

    } catch(err) {
      setErrorMsg(err.message)
      useMmStore.getState().setProgress(0,'')
    } finally {
      setAnalyzing(false)
    }
  }, [])

  return run
}
