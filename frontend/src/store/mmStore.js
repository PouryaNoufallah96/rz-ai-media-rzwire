import { create } from 'zustand'

// ── Constants ─────────────────────────────────────────────────────────────────
export const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? `http://${window.location.hostname}:3001`
  : ''

export const MM_SOURCES = {
  'CoinDesk':      'https://www.coindesk.com/arc/outboundfeeds/rss/',
  'Cointelegraph': 'https://cointelegraph.com/rss',
  'Decrypt':       'https://decrypt.co/feed',
  'CryptoSlate':   'https://cryptoslate.com/feed/',
  'The Block':     'https://www.theblock.co/rss.xml',
  'Blockworks':    'https://blockworks.co/feed/',
  'Bitcoin Mag':   'https://bitcoinmagazine.com/.rss/full/',
  'BeInCrypto':    'https://beincrypto.com/feed/',
  'Crypto.News':   'https://crypto.news/feed/',
  'U.Today':       'https://u.today/rss',
  'NewsBTC':       'https://www.newsbtc.com/feed/',
  'CryptoPotato':  'https://cryptopotato.com/feed/',
  'The Defiant':   'https://thedefiant.io/feed',
  'AMBCrypto':     'https://ambcrypto.com/feed/',
  'Chainlink Blog':'https://blog.chain.link/rss/',
  'DL News':       'https://dlnews.com/arc/outboundfeeds/rss/',
  'Chainalysis Blog':'https://blog.chainalysis.com/feed/',
}

export const TELEGRAM_SOURCES = {
  'Cointelegraph': 'cointelegraph',
  'Coingraph News': 'CoingraphNews',
  'CoinDesk Global': 'CoinDeskGlobal',
  'The Block Crypto': 'the_block_crypto',
  'Decrypt News': 'DecryptNews',
  'Lookonchain': 'lookonchainchannel',
  'Whale Alert': 'whale_alert_io',
  'CoinMarketCap Announcements': 'CoinMarketCapAnnouncements',
  'CoinMarketCap': 'CoinMarketCap',
  'Watcher Guru': 'WatcherGuru',
  'Wu Blockchain': 'wublockchainenglish',
  'Binance Announcements': 'binance_announcements',
  'OKX Announcements': 'OKXAnnouncements',
  'CryptoQuant': 'cryptoquant_official',
  'Glassnode': 'glassnode',
  'Crypto News': 'crypto_news',
  'CryptoDiffer': 'cryptodiffer',
  'CryptoRank News': 'CryptoRankNews',
  'DWF Labs': 'dwflabs',
  'Gamee': 'gameechannel',
  'Polymarket Now': 'polymarketnow',
  'InnMind': 'innmind',
  'Chainalysis': 'chainalysisinc',
  'Hacken': 'hackenai',
  'DHL Logistics': 'lotdhl',
  'MultiBank Group': 'MultiBankio_Announcements',
  'Coins.ph Announcements': 'coinsph_announcements',
  'Gram': 'gram',
  'Unfolded': 'unfolded',
}

export const TELEGRAM_SOURCE_PROFILES = {
  cointelegraph: { category:'news', focus:'Breaking crypto news, markets, and policy.', tags:['News', 'Markets', 'Policy'], brands:['Oasis Coin', 'MGC Coin'] },
  CoingraphNews: { category:'news', focus:'Fast market headlines and crypto trend updates.', tags:['News', 'Markets', 'Trends'], brands:['Oasis Coin'] },
  CoinDeskGlobal: { category:'institutional', focus:'Institutional markets, policy, and industry reporting.', tags:['Institutional', 'Markets', 'Policy'], brands:['Oasis Coin', 'MGC Coin'] },
  the_block_crypto: { category:'research', focus:'Research-led crypto coverage and industry reporting.', tags:['Research', 'Markets', 'Policy'], brands:['Oasis Coin'] },
  DecryptNews: { category:'news', focus:'Web3, culture, and accessible crypto reporting.', tags:['Web3', 'Culture', 'News'], brands:['Ranking Platform', 'Oasis Coin', 'Jewelry Coin'] },
  lookonchainchannel: { category:'onchain', focus:'Wallet movements, whale activity, and on-chain signals.', tags:['On-chain', 'Whales', 'Alerts'], brands:['MGC Coin', 'Oasis Coin'] },
  whale_alert_io: { category:'onchain', focus:'Large transfers and supply movement alerts.', tags:['Whales', 'Alerts', 'Flows'], brands:['MGC Coin', 'Oasis Coin'] },
  CoinMarketCapAnnouncements: { category:'exchange', focus:'Listings, token events, and platform campaigns.', tags:['Listings', 'Campaigns', 'Tokens'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  CoinMarketCap: { category:'data', focus:'Broad market data and ecosystem updates.', tags:['Data', 'Markets', 'Tokens'], brands:['Oasis Coin', 'MGC Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  WatcherGuru: { category:'news', focus:'Fast crypto, macro, and market headlines.', tags:['News', 'Macro', 'Markets'], brands:['Oasis Coin'] },
  wublockchainenglish: { category:'research', focus:'Asia, mining, exchange, and policy developments.', tags:['Asia', 'Mining', 'Policy'], brands:['Oasis Coin', 'MGC Coin'] },
  binance_announcements: { category:'exchange', focus:'Exchange products, listings, campaigns, and launches.', tags:['Exchange', 'Listings', 'Campaigns'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  OKXAnnouncements: { category:'exchange', focus:'OKX product, listing, and ecosystem announcements.', tags:['Exchange', 'Listings', 'Web3'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  cryptoquant_official: { category:'data', focus:'On-chain metrics and market structure research.', tags:['On-chain', 'Data', 'Research'], brands:['Oasis Coin', 'MGC Coin'] },
  glassnode: { category:'data', focus:'Institutional-grade on-chain and market research.', tags:['On-chain', 'Research', 'Markets'], brands:['Oasis Coin', 'MGC Coin'] },
  crypto_news: { category:'news', focus:'Broad daily crypto news coverage.', tags:['News', 'Markets', 'Web3'], brands:['Oasis Coin', 'MGC Coin'] },
  cryptodiffer: { category:'data', focus:'Visual market intelligence and crypto research.', tags:['Data', 'Research', 'Markets'], brands:['Oasis Coin', 'MGC Coin'] },
  CryptoRankNews: { category:'data', focus:'Rankings, fundraising, token data, and market calendars.', tags:['Rankings', 'Funding', 'Data'], brands:['MGC Coin', 'Ranking Platform', 'Oasis Coin'] },
  dwflabs: { category:'funding', focus:'Market-maker, investment, and ecosystem activity.', tags:['Funding', 'Liquidity', 'Web3'], brands:['MGC Coin', 'Oasis Coin'] },
  gameechannel: { category:'gaming', focus:'Gaming, Telegram community, and engagement signals.', tags:['Gaming', 'Community', 'TON'], brands:['Ranking Platform', 'MGC Coin', 'Oasis Coin'] },
  polymarketnow: { category:'markets', focus:'Prediction-market odds and live event signals.', tags:['Prediction', 'Markets', 'Signals'], brands:['Ranking Platform', 'MGC Coin'] },
  innmind: { category:'funding', focus:'Web3 startups, fundraising, founders, and venture activity.', tags:['Startups', 'Funding', 'Founders'], brands:['Ranking Platform', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  chainalysisinc: { category:'security', focus:'Compliance, regulation, investigations, and risk.', tags:['Regulation', 'Compliance', 'Risk'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  hackenai: { category:'security', focus:'Smart-contract security, audits, and project risk.', tags:['Security', 'Audits', 'Risk'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token', 'Real Estate Token'] },
  lotdhl: { category:'logistics', focus:'Global logistics, supply chains, and trade signals.', tags:['Logistics', 'Supply chain', 'Trade'], brands:['Jewelry Coin', 'Industrial Token'] },
  MultiBankio_Announcements: { category:'institutional', focus:'Traditional finance, brokerage, and market activity.', tags:['Finance', 'Trading', 'Markets'], brands:['Oasis Coin', 'MGC Coin'] },
  coinsph_announcements: { category:'exchange', focus:'Regional exchange campaigns, launches, and adoption.', tags:['Exchange', 'Campaigns', 'Adoption'], brands:['MGC Coin', 'Oasis Coin', 'Jewelry Coin'] },
  gram: { category:'gaming', focus:'Telegram-native ecosystem and TON community signals.', tags:['TON', 'Community', 'Ecosystem'], brands:['Ranking Platform', 'MGC Coin', 'Oasis Coin'] },
  unfolded: { category:'markets', focus:'Macro context, market data, and visual explainers.', tags:['Macro', 'Data', 'Markets'], brands:['Oasis Coin', 'MGC Coin'] },
}

export const SRC_COLORS = {
  'CoinDesk':'#3d8ef0','Cointelegraph':'#f0a040','Decrypt':'#ef4455',
  'CryptoSlate':'#9b72f5','The Block':'#3d8ef0','Blockworks':'#00d4a0',
  'Bitcoin Mag':'#f0a040','BeInCrypto':'#9b72f5','Crypto.News':'#3d8ef0',
  'U.Today':'#00d4a0','NewsBTC':'#ef4455','CryptoPotato':'#f0a040',
  'The Defiant':'#00d4a0','AMBCrypto':'#9b72f5',
  'Chainlink Blog':'#375bd2','DL News':'#ef4455','Chainalysis Blog':'#00d4a0',
  'Coingraph News':'#f0a040','CoinDesk Global':'#3d8ef0','The Block Crypto':'#00d4a0',
  'Decrypt News':'#ef4455','Lookonchain':'#22d3ee','Whale Alert':'#9b72f5',
  'CoinMarketCap Announcements':'#f0b90b','CoinMarketCap':'#3861fb',
  'Watcher Guru':'#00d4a0','Wu Blockchain':'#22d3ee','Binance Announcements':'#f0b90b',
  'OKX Announcements':'#eeeae2','CryptoQuant':'#4ade80','Glassnode':'#3d8ef0','Crypto News':'#9b72f5',
  'CryptoDiffer':'#7c6cff','CryptoRank News':'#f0a040','DWF Labs':'#ff6b6b','Gamee':'#00d4a0',
  'Polymarket Now':'#eeeae2','InnMind':'#9b72f5','Chainalysis':'#375bd2','Hacken':'#4ade80',
  'DHL Logistics':'#f0b90b','MultiBank Group':'#00a6e8','Coins.ph Announcements':'#00d4a0',
  'Gram':'#22d3ee','Unfolded':'#ef4455',
}

export const MEDIA_LIST      = ['MGC Coin','Ranking Platform','Oasis Coin','Jewelry Coin','Industrial Token','Real Estate Token']
export const PLAT_LIST       = ['X','Telegram','Instagram']
export const MEDIA_COLORS    = {'MGC Coin':'#FFD21A','Ranking Platform':'#7568F0','Oasis Coin':'#18C7CF','Jewelry Coin':'#A89CFF','Industrial Token':'#F4C224','Real Estate Token':'#0B8F91'}
export const PLAT_COLORS     = {X:'#00d4ff',Telegram:'#00d4a0',Instagram:'#e1306c'}

export const IMAGE_MODEL_OPTIONS = [
  { value:'openai/gpt-5.4-image-2', label:'GPT-5.4 Image 2 (OpenAI)', tier:'Premium', description:'Highest-fidelity editorial concepts and complex prompts.', maxReferences:3 },
  { value:'google/gemini-3.1-flash-image-preview', label:'Gemini 3.1 Flash Image (Google)', tier:'Balanced', description:'Fast generation with strong prompt understanding.', maxReferences:3 },
  { value:'google/gemini-3-pro-image-preview', label:'Gemini 3 Pro Image (Google)', tier:'Premium', description:'Detailed compositions and advanced visual reasoning.', maxReferences:3 },
  { value:'recraft/recraft-v4-pro', label:'Recraft V4 Pro', tier:'Design', description:'Polished graphic design and high-resolution layouts.', maxReferences:1 },
]

export const EDITORIAL_MODEL_META = {
  gpt:      { display:'GPT-5.5',              color:'#10a37f', badge:'OpenAI',    desc:'Best general-purpose editorial AI' },
  gemini:   { display:'Gemini 3.1 Pro Preview',color:'#4285f4', badge:'Google',    desc:'Strong reasoning · multimodal' },
  claude:   { display:'Claude Opus 4.8',       color:'#d97706', badge:'Anthropic', desc:'Top reasoning benchmark score' },
  deepseek: { display:'DeepSeek V4 Flash',     color:'#22d3ee', badge:'DeepSeek',  desc:'Fast · cost-efficient · strong reasoning' },
}

export const mkey = m => m.toLowerCase().replace(/\s+/g,'-')
export const cacheKey = (articleId, platform, modelKey, mode) =>
  `${articleId}|${platform}|${modelKey}${mode ? `|${mode}` : ''}`

// True when ANY selected media brand has Promo Copy toggled on. When this is true the
// whole run is promo-only: news sources, filtering, and the editorial pipeline are all
// skipped — we only generate promo ideas from the brand bibles. Read via useMmStore.getState().
export const anyPromoOn = (state) =>
  !!state.selectedMedia.some(m => state.promoMode && state.promoMode[m])

function buildEmptyRouted() {
  const r = {}
  MEDIA_LIST.forEach(m => {
    r[m] = { suggested: [] }
    PLAT_LIST.forEach(p => { r[m][p] = [] })
  })
  return r
}

// ── Zustand store ─────────────────────────────────────────────────────────────
export const useMmStore = create((set, get) => ({
  selectedMedia:     [...MEDIA_LIST],
  selectedPlatforms: [...PLAT_LIST],
  selectedSources:   ['CoinDesk','Cointelegraph','The Block'],
  recencyHours:      24,
  enrichArticles:    true,   // fetch + summarize source articles for richer AI picks
  routed:            buildEmptyRouted(),
  activeCard:        null,
  editorial:         null,
  lastShortlist:     [],
  selectedModels:    ['gpt','gemini','claude','deepseek'],
  modelLanes:        { gpt:{}, gemini:{}, claude:{}, deepseek:{} },
  telegramLanes:     {},
  platformLanes:     {},
  copyCache:         {},
  promoMode:         {},
  promoPrompts:      {},
  progress:          { pct: 0, label: '' },
  analyzing:         false,
  errorMsg:          '',
  mmReport:          null,
  reportOpen:        false,
  useTelegramSources: false,
  telegramMode:      'both', // 'both' | 'telegram_only'
  telegramOnlySavedSources: [],
  telegramOnlySavedModels:  [],
  selectedTelegramSources: ['cointelegraph'],
  telegramSortMode:  'views',
  telegramTopN:      20,

  // ── Setters ──
  setSelectedMedia:     v  => set({ selectedMedia: v }),
  setSelectedPlatforms: v  => set({ selectedPlatforms: v }),
  setSelectedSources:   v  => set(s => s.telegramMode === 'telegram_only' ? {} : { selectedSources: v }),
  setRecencyHours:      h  => set({ recencyHours: h }),
  setEnrichArticles:    v  => set({ enrichArticles: typeof v === 'boolean' ? v : !get().enrichArticles }),
  setSelectedModels:    v  => set(s => s.telegramMode === 'telegram_only' ? { selectedModels: [v?.[0] || 'gpt'] } : { selectedModels: v }),
  setActiveCard:        c  => set({ activeCard: c }),
  setEditorial:         e  => set({ editorial: e }),
  setLastShortlist:     s  => set({ lastShortlist: s }),
  setModelLanes:        v  => set({ modelLanes: v }),
  setTelegramLanes:     v  => set({ telegramLanes: v }),
  setPlatformLanes:     v  => set({ platformLanes: v }),
  setProgress:          (pct, label) => set({ progress: { pct, label } }),
  setAnalyzing:         v  => set({ analyzing: v }),
  setErrorMsg:          v  => set({ errorMsg: v }),
  setMmReport:          v  => set({ mmReport: v }),
  setReportOpen:        v  => set({ reportOpen: v }),

  toggleMedia: (m) => set(s => {
    const arr = s.selectedMedia.includes(m)
      ? s.selectedMedia.filter(x => x !== m)
      : [...s.selectedMedia, m]
    return { selectedMedia: arr }
  }),
  togglePlatform: (p) => set(s => {
    const arr = s.selectedPlatforms.includes(p)
      ? s.selectedPlatforms.filter(x => x !== p)
      : [...s.selectedPlatforms, p]
    return { selectedPlatforms: arr }
  }),
  toggleSource: (src) => set(s => {
    if (s.telegramMode === 'telegram_only') return {}
    const arr = s.selectedSources.includes(src)
      ? s.selectedSources.filter(x => x !== src)
      : [...s.selectedSources, src]
    return { selectedSources: arr }
  }),
  setUseTelegramSources: v => set(s => {
    if (v) return { useTelegramSources: true }
    if (s.telegramMode !== 'telegram_only') return { useTelegramSources: false }
    return {
      useTelegramSources: false,
      telegramMode: 'both',
      selectedSources: s.telegramOnlySavedSources,
      selectedModels: s.telegramOnlySavedModels.length ? s.telegramOnlySavedModels : ['gpt'],
      telegramOnlySavedSources: [],
      telegramOnlySavedModels: [],
    }
  }),
  setTelegramMode: mode => set(s => {
    if (mode === 'telegram_only') {
      return {
        useTelegramSources: true,
        telegramMode: 'telegram_only',
        telegramOnlySavedSources: [...s.selectedSources],
        telegramOnlySavedModels: [...s.selectedModels],
        selectedSources: [],
        selectedModels: ['gpt'],
      }
    }
    if (s.telegramMode !== 'telegram_only') return { useTelegramSources: true, telegramMode: 'both' }
    return {
      useTelegramSources: true,
      telegramMode: 'both',
      selectedSources: s.telegramOnlySavedSources,
      selectedModels: s.telegramOnlySavedModels.length ? s.telegramOnlySavedModels : ['gpt'],
      telegramOnlySavedSources: [],
      telegramOnlySavedModels: [],
    }
  }),
  toggleTelegramSource: (src) => set(s => {
    const arr = s.selectedTelegramSources.includes(src)
      ? s.selectedTelegramSources.filter(x => x !== src)
      : [...s.selectedTelegramSources, src]
    return { selectedTelegramSources: arr }
  }),
  setTelegramSortMode: mode => set({ telegramSortMode: mode }),
  setTelegramTopN: n => set({ telegramTopN: Number(n) || 5 }),
  initPlatformLanes: () => set(s => {
    const pl = {}
    s.selectedMedia.forEach(brand => {
      pl[brand] = {}
      s.selectedPlatforms.forEach(p => { pl[brand][p] = [] })
    })
    return { platformLanes: pl }
  }),

  toggleModel: (key) => set(s => {
    if (s.telegramMode === 'telegram_only') return { selectedModels: [key] }
    if (s.selectedModels.includes(key)) {
      if (s.selectedModels.length === 1) return {}
      return { selectedModels: s.selectedModels.filter(k => k !== key) }
    }
    return { selectedModels: [...s.selectedModels, key] }
  }),

  updateCardStatus: (cardId, status, extra = {}) => set(s => {
    const activeCard = s.activeCard?.id === cardId ? { ...s.activeCard, status, ...extra } : s.activeCard
    // Update in modelLanes
    const modelLanes = { ...s.modelLanes }
    Object.keys(modelLanes).forEach(mk => {
      const lanes = { ...modelLanes[mk] }
      Object.keys(lanes).forEach(brand => {
        lanes[brand] = lanes[brand].map(c => c.id === cardId ? { ...c, status, ...extra } : c)
      })
      modelLanes[mk] = lanes
    })
    const telegramLanes = { ...s.telegramLanes }
    Object.keys(telegramLanes).forEach(brand => {
      telegramLanes[brand] = telegramLanes[brand].map(c => c.id === cardId ? { ...c, status, ...extra } : c)
    })
    // Update in platformLanes
    const platformLanes = { ...s.platformLanes }
    Object.keys(platformLanes).forEach(brand => {
      const lanes = { ...platformLanes[brand] }
      Object.keys(lanes).forEach(plat => {
        lanes[plat] = lanes[plat].map(c => c.id === cardId ? { ...c, status, ...extra } : c)
      })
      platformLanes[brand] = lanes
    })
    return { activeCard, modelLanes, telegramLanes, platformLanes }
  }),

  updateCard: (cardId, extra = {}) => set(s => {
    const activeCard = s.activeCard?.id === cardId ? { ...s.activeCard, ...extra } : s.activeCard
    const modelLanes = { ...s.modelLanes }
    Object.keys(modelLanes).forEach(mk => {
      const lanes = { ...modelLanes[mk] }
      Object.keys(lanes).forEach(brand => {
        lanes[brand] = lanes[brand].map(c => c.id === cardId ? { ...c, ...extra } : c)
      })
      modelLanes[mk] = lanes
    })
    const telegramLanes = { ...s.telegramLanes }
    Object.keys(telegramLanes).forEach(brand => {
      telegramLanes[brand] = telegramLanes[brand].map(c => c.id === cardId ? { ...c, ...extra } : c)
    })
    const platformLanes = { ...s.platformLanes }
    Object.keys(platformLanes).forEach(brand => {
      const lanes = { ...platformLanes[brand] }
      Object.keys(lanes).forEach(plat => {
        lanes[plat] = lanes[plat].map(c => c.id === cardId ? { ...c, ...extra } : c)
      })
      platformLanes[brand] = lanes
    })
    return { activeCard, modelLanes, telegramLanes, platformLanes }
  }),

  // Update only the unrouted source copies. Generated platform cards with the
  // same article id keep their own platform-specific copy and variants.
  updateSourceCard: (cardId, extra = {}) => set(s => {
    const activeCard = s.activeCard?.id === cardId && (!s.activeCard.platform || s.activeCard.platform === 'suggested')
      ? { ...s.activeCard, ...extra }
      : s.activeCard
    const modelLanes = { ...s.modelLanes }
    Object.keys(modelLanes).forEach(modelKey => {
      const lanes = { ...modelLanes[modelKey] }
      Object.keys(lanes).forEach(brand => {
        lanes[brand] = lanes[brand].map(card => card.id === cardId ? { ...card, ...extra } : card)
      })
      modelLanes[modelKey] = lanes
    })
    const telegramLanes = { ...s.telegramLanes }
    Object.keys(telegramLanes).forEach(brand => {
      telegramLanes[brand] = telegramLanes[brand].map(card => card.id === cardId ? { ...card, ...extra } : card)
    })
    return { activeCard, modelLanes, telegramLanes }
  }),

  // Like updateCard, but scoped to a single platform — the same article can be routed to
  // multiple platform lanes under the same card id, each with its own generated copy/variants;
  // matching on id alone would leak one platform's copy onto another's lane-card.
  updatePlatformCard: (cardId, platform, extra = {}) => set(s => {
    const matches = c => c.id === cardId && c.platform === platform
    const activeCard = (s.activeCard && matches(s.activeCard)) ? { ...s.activeCard, ...extra } : s.activeCard
    const platformLanes = { ...s.platformLanes }
    Object.keys(platformLanes).forEach(brand => {
      const lanes = { ...platformLanes[brand] }
      Object.keys(lanes).forEach(plat => {
        lanes[plat] = lanes[plat].map(c => matches(c) ? { ...c, ...extra } : c)
      })
      platformLanes[brand] = lanes
    })
    return { activeCard, platformLanes }
  }),

  togglePromoMode: (brand) => set(s => ({ promoMode: { ...s.promoMode, [brand]: !s.promoMode[brand] } })),
  setPromoPrompt: (brand, text) => set(s => ({ promoPrompts: { ...s.promoPrompts, [brand]: text } })),

  getCachedCopy: (articleId, platform, modelKey, mode) => get().copyCache[cacheKey(articleId, platform, modelKey, mode)] || null,
  setCachedCopy: (articleId, platform, modelKey, payload, mode) => set(s => ({
    copyCache: { ...s.copyCache, [cacheKey(articleId, platform, modelKey, mode)]: payload }
  })),
}))
