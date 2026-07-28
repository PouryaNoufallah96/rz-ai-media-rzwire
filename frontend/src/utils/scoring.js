// All pre-scoring logic Ã¢â‚¬â€ ported from multimedia.html

export const SOURCE_AUTHORITY = {
  'CoinDesk':90,'Cointelegraph':88,'The Block':92,'Blockworks':82,
  'Decrypt':78,'Bitcoin Mag':75,'BeInCrypto':65,'Crypto.News':62,
  'U.Today':60,'NewsBTC':58,'CryptoPotato':55,'The Defiant':72,'AMBCrypto':52,
  'Chainlink Blog':80,'DL News':74,'Chainalysis Blog':82,
}

export const SOURCE_MEDIA_BIAS = {
  'MGC Coin':         new Set(['Decrypt','Cointelegraph','BeInCrypto','Crypto.News']),
  'Ranking Platform': new Set(['Decrypt','Cointelegraph','BeInCrypto']),
  'Oasis Coin':       new Set(['Decrypt','Cointelegraph','The Block','Blockworks']),
  'Jewelry Coin':     new Set(['Decrypt','Cointelegraph','BeInCrypto','CoinDesk']),
}

export const REJECT_THRESHOLDS = {
  minTopMediaScore: 22,
  minFinalScore:    18,
  dupSimilarity:    0.78,
  AI_PER_BRAND_CAP: 15,
}

export const VIRALITY_SIGNALS = {
  power_words: {
    'breaking':20,'urgent':18,'alert':16,'crash':22,'surges':18,'explodes':20,
    'collapses':22,'massive':15,'historic':18,'record':14,'first ever':18,
    'all-time high':22,'ath':16,'all-time low':22,'atl':16,'billions':14,
    'trillion':18,'emergency':20,'warning':16,'critical':15,'catastrophic':20,
    'shocking':16,'unprecedented':18,'exclusive':12,'leaked':18,
    'confirmed':12,'just in':18,'developing':14,'soars':16,'plunges':16,
    'free fall':18,'skyrockets':18,'rallies':14,'dumps':16,'major':10,
  },
  high_value_entities: {
    'bitcoin':15,'blackrock':14,'sec':14,'trump':16,'binance':12,
    'coinbase':10,'federal reserve':12,'elon musk':16,'michael saylor':12,
    'vitalik':10,'satoshi':12,'imf':10,'fed':10,
  },
}

export const PLATFORM_FIT_RULES = {
  X:        { positive: {'breaking':20,'alert':18,'surge':16,'crash':18,'record':15,'historic':15,'billion':14,'trillion':16,'just':10,'now':10} },
  Telegram: { positive: {'analysis':18,'breakdown':16,'explained':14,'report':14,'research':14,'deep dive':18,'update':10,'summary':14,'review':12,'what you need':15,'here is why':14} },
  Instagram:{ positive: {'luxury':20,'visual':14,'art':14,'design':12,'lifestyle':18,'exclusive':16,'rare':14,'nft':14,'gaming':12,'milestone':14,'achievement':12,'stunning':15,'beautiful':12} },
}

// Brand-fit keyword profiles.
export const MEDIA_KEYWORDS = {
  'MGC Coin': {
    strong: {
      'meta games coin':32,'metagamescoin':32,'mgc':28,'gaming utility token':26,
      'gaming rewards':24,'player rewards':24,'tournament rewards':22,'play-to-earn':20,
      'play to earn':20,'gamefi':20,'gaming economy':22,'game economy':22,
      'blockchain gaming':22,'web3 gaming':22,'gaming community':18,'creator rewards':18,
      'player achievement':18,'digital ownership':16,'bnb smart chain':16,'bep-20':16,
      'bep20':16,'ranking.game':24,'ranking game':22,'tournament':14,'esports':14,
    },
    weak: {'bitcoin etf':-10,'macro':-8,'federal reserve':-10,'unrelated hack':-8,'luxury watch':-8},
  },
  'Ranking Platform': {
    strong: {
      'ranking.game':32,'ranking game':30,'competitive gaming':28,'player ranking':28,
      'leaderboard':26,'pvp':24,'pvp match':26,'tournament':24,'esports':22,
      'gaming team':22,'team competition':22,'match result':20,'player profile':20,
      'tournament organizer':20,'referee':18,'gaming venue':20,'gaming center':20,
      'sports club':18,'digital game':16,'physical game':16,'gaming community':18,
      'league':14,'competition':14,'rankings':20,
    },
    weak: {'token price':-16,'price prediction':-12,'bitcoin etf':-12,'defi exploit':-10,'presale':-10},
  },
  'Oasis Coin': {
    strong: {
      'rzoasis':32,'rzoasis galaxy':32,'oasis token':30,'oasis coin':30,
      'metaverse':26,'metaverse gaming':28,'virtual world':24,'virtual land':22,
      'web3 game':22,'blockchain game':20,'digital identity':20,'game asset':20,
      'digital asset':16,'world building':22,'metaverse marketplace':20,
      'gaming utility':18,'energy system':18,'rank progression':16,
      'future utility':18,'bnb smart chain':16,'bep-20':16,'bep20':16,
      'virtual economy':18,'planet':12,'galaxy':14,
    },
    weak: {'utility is live':-12,'guaranteed return':-20,'bitcoin etf':-10,'macro':-8,'luxury auction':-8},
  },
  'Jewelry Coin': {
    strong: {
      'jewelry token':32,'jewelry coin':30,'jewellery game':30,'digital jewelry':28,
      'virtual jewelry':26,'jewelry design':26,'gem extraction':24,'gem mining':22,
      'gemstone':20,'nft minting':22,'nft marketplace':22,'digital collectible':20,
      'creator marketplace':20,'physical jewelry':22,'digital-to-physical':24,
      'augmented reality':20,'ar try-on':22,'luxury craft':18,'jeweler':18,
      'merchant':14,'bep-20':16,'bep20':16,'binance smart chain':16,
      'nft':14,'marketplace':14,'crafting':18,
    },
    weak: {'bitcoin etf':-12,'macro':-10,'defi exploit':-10,'price prediction':-10,'presale':-8},
  },
}

// Utility functions
export function normText(t) {
  return (t || '').toLowerCase().replace(/[^\w\s-]/g,' ').replace(/\s+/g,' ').trim()
}

function matchKw(text, kw, tokens) {
  if (kw.includes(' ') || kw.includes('-') || kw.includes("'") || kw.includes('.'))
    return text.includes(kw) ? 1 : 0
  return tokens.has(kw) ? 1 : 0
}

export function scoreMediaFitWithKeywords(article, selectedMedia) {
  const titleNorm   = normText(article.title)
  const descNorm    = normText(article.desc || '')
  const titleTokens = new Set(titleNorm.split(/[^a-z0-9]+/).filter(Boolean))
  const descTokens  = new Set(descNorm.split(/[^a-z0-9]+/).filter(Boolean))
  const scores = {}, kwScores = {}, keywords = {}
  for (const media of selectedMedia) {
    let kw = 0
    const hits = []
    const { strong = {}, weak = {} } = MEDIA_KEYWORDS[media] || {}
    for (const [term, w] of Object.entries(strong)) {
      const bh = matchKw(descNorm, term, descTokens), th = matchKw(titleNorm, term, titleTokens)
      if (bh || th) { const c = w*bh + w*2*th; kw += c; hits.push({kw:term,contrib:c,type:'strong'}) }
    }
    for (const [term, w] of Object.entries(weak)) {
      const bh = matchKw(descNorm, term, descTokens), th = matchKw(titleNorm, term, titleTokens)
      if (bh || th) { const c = w*(bh+th); kw += c; hits.push({kw:term,contrib:c,type:'weak'}) }
    }
    const bias = SOURCE_MEDIA_BIAS[media]?.has(article.source) ? 3 : 0
    if (bias) hits.push({kw:`bias:${article.source}`,contrib:bias,type:'bias'})
    kwScores[media] = Math.max(0, kw)
    scores[media]   = Math.max(0, kw + bias)
    keywords[media] = hits
  }
  return { scores, kwScores, keywords }
}

export function scoreMediaFitSemantic(article, selectedMedia) {
  if (!article._semScores) return scoreMediaFitWithKeywords(article, selectedMedia)
  const scores = {}, kwScores = {}, keywords = {}
  for (const media of selectedMedia) {
    const sem  = article._semScores[media] ?? 0
    const bias = SOURCE_MEDIA_BIAS[media]?.has(article.source) ? 3 : 0
    kwScores[media] = sem
    scores[media]   = sem + bias
    keywords[media] = [{kw:'semantic-similarity',contrib:+sem.toFixed(1),type:'semantic'}]
  }
  return { scores, kwScores, keywords }
}

export function scoreVirality(article) {
  const title = normText(article.title), full = normText(`${article.title} ${article.desc}`)
  let score = 0
  for (const [w, v] of Object.entries(VIRALITY_SIGNALS.power_words)) {
    if (title.includes(w)) score += v * 1.5; else if (full.includes(w)) score += v * 0.4
  }
  for (const [e, v] of Object.entries(VIRALITY_SIGNALS.high_value_entities))
    if (title.includes(e)) score += v
  if (/\d+(\.\d+)?%/.test(article.title)) score += 12
  if (/\$[\d,.]+/.test(article.title)) score += 10
  if (/\b(billion|million|trillion)\b/i.test(article.title)) score += 14
  if (/\b\d{4,}\b/.test(article.title)) score += 6
  return Math.min(100, Math.max(0, score))
}

export function scoreFreshness(article) {
  if (!article.pubDate) return 50
  const ageH = (Date.now() - Date.parse(article.pubDate)) / 3600000
  if (isNaN(ageH) || ageH < 0) return 50
  if (ageH < 1) return 100; if (ageH < 2) return 95; if (ageH < 4) return 88
  if (ageH < 6) return 80;  if (ageH < 12) return 68; if (ageH < 24) return 50
  if (ageH < 36) return 32; if (ageH < 48) return 20; return 8
}

export const scoreAuthority = a => SOURCE_AUTHORITY[a.source] || 50

export function scorePlatformFit(article, platform) {
  const text = normText(`${article.title} ${article.desc}`)
  const rules = PLATFORM_FIT_RULES[platform]; if (!rules) return 50
  let score = 50
  for (const [kw, w] of Object.entries(rules.positive || {})) if (text.includes(kw)) score += w
  if (platform === 'X') { if (article.title.length < 65) score += 10; else if (article.title.length > 110) score -= 8 }
  if (platform === 'Telegram' && article.desc) { if (article.desc.length > 200) score += 15; else if (article.desc.length < 80) score -= 10 }
  if (platform === 'Instagram' && /\b(nft|art|luxury|visual|lifestyle|gaming|rare|stunning)\b/i.test(text)) score += 14
  return Math.min(100, Math.max(0, score))
}

export function extractEntities(title) {
  return (title.match(/\b[A-Z][a-z]{2,}\b/g) || []).map(e => e.toLowerCase())
}

function extractUrlSlug(url) {
  if (!url) return ''
  try { const s = new URL(url).pathname.split('/').filter(Boolean); return (s[s.length-1]||'').replace(/[-_]/g,' ').replace(/\d+/g,'').trim().toLowerCase() }
  catch { return '' }
}

function titleJaccard(a, b) {
  const wa = normText(a).split(' ').filter(w => w.length > 3)
  const wb = normText(b).split(' ').filter(w => w.length > 3)
  const union = new Set([...wa,...wb]).size
  if (!union) return 0
  return wa.filter(w => wb.includes(w)).length / union
}

function checkDuplicate(article, seen) {
  const slug = extractUrlSlug(article.link), entities = extractEntities(article.title)
  for (const s of seen) {
    if (article.link && s.link && article.link === s.link) return {isDup:true,dupOf:s.title,reason:'Exact URL match'}
    if (slug && s._urlSlug && slug === s._urlSlug && article.source === s.source) return {isDup:true,dupOf:s.title,reason:'Matching URL slug'}
    const sim = titleJaccard(article.title, s.title)
    if (sim >= REJECT_THRESHOLDS.dupSimilarity) return {isDup:true,dupOf:s.title,reason:`Title similarity ${Math.round(sim*100)}%`}
    const shared = entities.filter(e => (s._entities||[]).includes(e))
    if (entities.length >= 2 && shared.length >= 3) return {isDup:true,dupOf:s.title,reason:`Shared entities: ${shared.slice(0,3).join(', ')}`}
  }
  return {isDup:false}
}

function isSameStory(a, b) {
  if (titleJaccard(a.title,b.title) >= 0.55) return true
  const ea = extractEntities(a.title), eb = extractEntities(b.title)
  return ea.length >= 2 && ea.filter(e => eb.includes(e)).length >= 2
}

function clusterStories(articles) {
  const clusters = []
  for (const art of articles) {
    let placed = false
    for (const cl of clusters) { if (isSameStory(art,cl[0])) { cl.push(art); placed=true; break } }
    if (!placed) clusters.push([art])
  }
  const clusteredOut = []
  const survivors = clusters.map(cl => {
    if (cl.length === 1) return cl[0]
    const best = cl.reduce((a,b) => {
      const sa = (a._scores?.authority||0)*0.4+(a._scores?.freshness||0)*0.35+(a._scores?.final||0)*0.25
      const sb = (b._scores?.authority||0)*0.4+(b._scores?.freshness||0)*0.35+(b._scores?.final||0)*0.25
      return sa >= sb ? a : b
    })
    cl.filter(a => a.title!==best.title).forEach(a => clusteredOut.push({...a,_pipelineStatus:'clustered_out',_clusteredWith:best.title}))
    return best
  })
  return { survivors, clusteredOut }
}

function scoreUserTopicFit(article, topicsStr) {
  if (!topicsStr?.trim()) return 0
  const topics = topicsStr.split(/[,;]+/).map(t => normText(t.trim())).filter(Boolean)
  if (!topics.length) return 0
  const tn = normText(article.title), dn = normText(article.desc||'')
  const tt = new Set(tn.split(/[^a-z0-9]+/).filter(Boolean)), dt = new Set(dn.split(/[^a-z0-9]+/).filter(Boolean))
  let hits = 0
  for (const topic of topics) {
    const single = !topic.includes(' ')
    const inTitle = single ? tt.has(topic) : tn.includes(topic)
    const inDesc  = single ? dt.has(topic) : dn.includes(topic)
    if (inTitle) hits += 2; else if (inDesc) hits += 1
  }
  return Math.min(100, Math.round((hits/(topics.length*2))*100))
}

const scoreConfidence = (nm,ut,fr,au) => Math.round((nm+ut+fr+au)/4)

function computeRouting(mediaFitScores, selectedMedia) {
  const sorted = selectedMedia.map(m=>[m,mediaFitScores[m]||0]).sort((a,b)=>b[1]-a[1])
  const total = sorted.reduce((s,[,v])=>s+v,0)
  if (total===0) return {primary_media:sorted[0][0],confidence:0,secondary_media:sorted[1]?.[0]||null,secondary_confidence:0}
  return {
    primary_media:        sorted[0][0],
    confidence:           Math.round((sorted[0][1]/total)*100)/100,
    secondary_media:      sorted[1]?.[0]||null,
    secondary_confidence: Math.round(((sorted[1]?.[1]||0)/total)*100)/100,
  }
}

export function preScore(articles, selectedMedia, topics) {
  const seenArticles=[], rejected={duplicate:0,noMediaFit:0,lowScore:0}, passed=[], allTracked=[]
  const hasTopics = !!(topics?.trim())
  for (const article of articles) {
    if (!article.title?.trim()) continue
    article._urlSlug  = extractUrlSlug(article.link)
    article._entities = extractEntities(article.title)
    const dupCheck = checkDuplicate(article, seenArticles)
    if (dupCheck.isDup) { rejected.duplicate++; allTracked.push({...article,_pipelineStatus:'duplicate',_dupOf:dupCheck.dupOf,_dupReason:dupCheck.reason,_scores:null,_keywords:null,_routing:null}); continue }
    seenArticles.push(article)
    const {scores:mediaFit,kwScores,keywords} = scoreMediaFitSemantic(article, selectedMedia)
    const topKwScore = Math.max(...selectedMedia.map(m=>kwScores[m]||0))
    const topMediaScore = Math.max(...selectedMedia.map(m=>mediaFit[m]||0))
    if (topKwScore < REJECT_THRESHOLDS.minTopMediaScore) { rejected.noMediaFit++; allTracked.push({...article,_pipelineStatus:'no_media_fit',_scores:{mediaFit,kwScores,userTopic:0,virality:0,freshness:0,authority:0,diversity:0,final:0},_keywords:keywords,_routing:null}); continue }
    const userTopic=scoreUserTopicFit(article,topics), virality=scoreVirality(article), freshness=scoreFreshness(article), authority=scoreAuthority(article)
    const diversity = passed.filter(a=>a.source===article.source).length === 0 ? 100 : passed.filter(a=>a.source===article.source).length === 1 ? 70 : passed.filter(a=>a.source===article.source).length === 2 ? 40 : 20
    const normMedia = Math.min(100, topMediaScore)
    const finalScore = hasTopics ? normMedia*0.35+userTopic*0.25+virality*0.18+freshness*0.12+authority*0.07+diversity*0.03 : normMedia*0.47+virality*0.24+freshness*0.16+authority*0.09+diversity*0.04
    if (finalScore < REJECT_THRESHOLDS.minFinalScore) { rejected.lowScore++; allTracked.push({...article,_pipelineStatus:'low_score',_scores:{mediaFit,kwScores,userTopic,virality,freshness,authority,diversity,final:finalScore},_keywords:keywords,_routing:null}); continue }
    const confidence=scoreConfidence(normMedia,userTopic,freshness,authority), routing=computeRouting(mediaFit,selectedMedia)
    passed.push({...article,_scores:{mediaFit,kwScores,userTopic,virality,freshness,authority,diversity,final:finalScore,confidence},_keywords:keywords,_routing:routing})
  }
  const {survivors:clusteredPassed,clusteredOut}=clusterStories(passed)
  clusteredOut.forEach(a=>allTracked.push({...a,_pipelineStatus:'clustered_out'}))
  const brandBuckets={}; selectedMedia.forEach(m=>{brandBuckets[m]=[]})
  for (const a of clusteredPassed) { const pm=a._routing.primary_media; if(brandBuckets[pm]) brandBuckets[pm].push(a) }
  const shortlisted=[], usedTitles=new Set()
  for (const m of selectedMedia) {
    brandBuckets[m].sort((a,b)=>b._scores.final-a._scores.final).slice(0,REJECT_THRESHOLDS.AI_PER_BRAND_CAP).forEach(a=>{shortlisted.push(a);usedTitles.add(a.title)})
  }
  for (const m of selectedMedia) {
    const have=shortlisted.filter(a=>a._routing.primary_media===m).length; if(have>=5) continue
    clusteredPassed.filter(a=>a._routing.secondary_media===m&&!usedTitles.has(a.title)).sort((a,b)=>b._scores.final-a._scores.final).slice(0,5-have).forEach(a=>{shortlisted.push({...a,_backfillMedia:m});usedTitles.add(a.title)})
  }
  const shortlistedSet=new Set(shortlisted.map(a=>a.title))
  shortlisted.forEach(a=>{ const status=a._rescued?'floor_rescued':a._backfillMedia?'backfilled_secondary':'selected'; allTracked.push({...a,_pipelineStatus:status}) })
  clusteredPassed.filter(a=>!shortlistedSet.has(a.title)).forEach(a=>allTracked.push({...a,_pipelineStatus:'cap_exceeded'}))
  return { shortlisted, rejected, total:articles.length, passed:passed.length, allTracked }
}



