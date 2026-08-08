"""
Central configuration & shared constants for the RZWire backend.
All env-derived settings and the small platform/model lookup dicts live here
so every other module can `from config import *` (or named imports).
"""
import os
import re
from pathlib import Path
from datetime import datetime as _datetime, date as _date, timedelta as _timedelta, timezone as _timezone

# ── Load .env ──────────────────────────────────────────────────────────────────
ENV_PATH = Path(__file__).parent / '.env'
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip())

SCRIPT_URL      = os.environ.get('GOOGLE_APPS_SCRIPT_URL', '')
PORT            = int(os.environ.get('PORT', 3001))
ORIGIN          = os.environ.get('FRONTEND_ORIGIN', '*')
COOKIE_SECURE   = os.environ.get('COOKIE_SECURE', '').lower() in ('1', 'true', 'yes')

def _env_flag(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')

# Outbound actions are deliberately opt-in. Local RZWire can analyze, create,
# save, and download without ever contacting a publishing or archive account.
PUBLISHING_ENABLED = _env_flag('RZWIRE_PUBLISHING_ENABLED', False)
SHEETS_ENABLED     = _env_flag('RZWIRE_SHEETS_ENABLED', False)

# Keep in sync with frontend/src/store/mmStore.js MEDIA_LIST
MEDIA_LIST = ['MGC Coin', 'Ranking Platform', 'Oasis Coin', 'Jewelry Coin', 'Industrial Token']
X_API_KEY       = os.environ.get('X_API_KEY', '')
X_API_SECRET    = os.environ.get('X_API_SECRET', '')
X_TOKEN         = os.environ.get('X_ACCESS_TOKEN', '')
X_TOKEN_SEC     = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
OPENROUTER_KEY   = os.environ.get('OPENROUTER_API_KEY', '')
TELEGRAM_TOKEN   = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL = os.environ.get('TELEGRAM_CHANNEL', '')
TELEGRAM_PROXY   = os.environ.get('TELEGRAM_PROXY', '')   # e.g. http://127.0.0.1:10808
DRIVE_FOLDER_URL = os.environ.get('GOOGLE_DRIVE_FOLDER_URL', '')

OPENROUTER_URL  = 'https://openrouter.ai/api/v1/chat/completions'
# ── Editorial AI models (all routed through OpenRouter) ───────────────────────
EDITORIAL_MODELS = {
    'gpt': {
        'id':          'openai/gpt-5.5',
        'display':     'GPT-5.5',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
    'gemini': {
        'id':          'google/gemini-3.1-pro-preview',
        'display':     'Gemini 3.1 Pro Preview',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
    'claude': {
        'id':          'anthropic/claude-opus-4.8',
        'display':     'Claude Opus 4.8',
        'temperature': 0.30,
        'max_tokens':  8000,
        'api':         'openrouter',
    },
    'deepseek': {
        'id':          'deepseek/deepseek-v4-flash',
        'display':     'DeepSeek V4 Flash',
        'temperature': 0.30,
        'max_tokens':  16000,
        'api':         'openrouter',
    },
}

# ── Chat assistant model (cheap + fast, for the in-app chatbot) ────────────────
# Routed through OpenRouter like everything else. Swap the id here if you'd rather
# use a different cheap-fast model (e.g. 'google/gemini-2.0-flash',
# 'deepseek/deepseek-v4-flash'). Free models on OpenRouter use the ':free' suffix.
CHAT_MODEL = {
    'id':          'openai/gpt-5.4-mini',
    'display':     'GPT-5.4 mini',
    'temperature': 0.4,
    'max_tokens':  1200,
    'api':         'openrouter',
}

# ── Platform rules ─────────────────────────────────────────────────────────────
# ── Topic-anchored emoji suggestions (keeps emoji placement semantic, not random) ──
EMOJI_LEXICON = {'markets': '📈📉', 'crypto': '₿🪙', 'politics': '🏛️🗳️', 'breaking': '🚨⚡️'}
_EMOJI_HINT = ', '.join(f'{k}→{v}' for k, v in EMOJI_LEXICON.items())

_FACT_RULE = 'HARD RULE: use only facts present in the provided article. Do not invent figures, quotes, names, or outcomes.'

def _sibling_block(sibling_copy, other_label):
    if not sibling_copy:
        return ''
    return (f'\nFor reference, here is the {other_label} version already published for this same story — '
            f'make this version structurally and tonally distinct, not a re-flow of it:\n"{sibling_copy}"')

PLAT_RULES = {
    'X': {
        'maxChars': 280, 'maxTokens': 500, 'temperature': 0.35,
        'emoji_policy': 'none — zero emojis, journalist tone only',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the senior social media editor for {brand}, a premium crypto news brand, known for scroll-stopping one-liners. Sentiment: {sent}.\n'
            'PERSONA: sharp, fast, opinionated-but-factual — the post a trader screenshots before reading the full article.\n'
            'STRUCTURE: one scroll-stopping unit — a hook line that states the news, optionally one short line of context/stakes.\n'
            'HARD RULE: the "copy" field must be PURE PROSE with ZERO hashtags in it. Put your 2-3 hashtags (ticker/topic tags, not generic ones) ONLY in the separate "hashtags" array — they are appended to the post automatically.\n'
            'HARD RULE: response must be ≤ 280 characters total including spaces and hashtags.\n'
            'EMOJI POLICY: none — zero emojis on X, ever.\n'
            f'{_FACT_RULE}\n'
            'EXAMPLES OF THE VOICE (do not reuse content, only mirror tone/structure). Note: copy has NO hashtags — they live in the array:\n'
            '- { "copy": "BlackRock just filed for a spot Solana ETF. The Bitcoin ETF playbook is repeating — and this time the SEC clock is already ticking.", "hashtags": ["#Solana","#ETF"] }\n'
            '- { "copy": "Binance freezes $80M in wallets linked to a North Korean laundering ring. Compliance teams everywhere just got a new case study.", "hashtags": ["#Binance","#Crypto"] }\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1","#Tag2"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
        'variant_angles': [
            {'label': 'Breaking', 'instruction': 'ANGLE: lead with urgency and the key number — one scroll-stopping hook framed as urgent, breaking news.'},
            {'label': 'Question', 'instruction': 'ANGLE: open or close with one genuine question that invites replies — make the reader want to respond, not just read.'},
            {'label': 'Take',     'instruction': 'ANGLE: one confident, opinionated-but-factual framing — sharp analysis, not hype.'},
        ],
    },
    'Telegram': {
        'minChars': 300, 'maxChars': 600, 'maxTokens': 700, 'temperature': 0.5,
        'emoji_policy': 'sparing, structural — e.g. 📌 for bullet markers, 🚨 only for genuinely breaking news',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the Telegram channel editor for {brand}, writing for an audience that wants the full story without leaving the app. Sentiment: {sent}.\n'
            'STRUCTURE: a bold headline line, then a short body that covers what happened and why it matters.\n'
            'HARD RULE: the "copy" field must be PURE PROSE with ZERO hashtags in it. Put your 3-5 hashtags ONLY in the separate "hashtags" array — they are appended to the post automatically.\n'
            'HARD RULE: response must be 300-600 characters total, including spaces, line breaks, emoji and hashtags.\n'
            'HARD RULE: do NOT include any "Source:", "Subject:", "Flag:", "Caveat:" or any "📌 Label: value" labeled bullets — no attribution lines of any kind.\n'
            'EMOJI POLICY: sparing and structural — 📌 for bullets only if the angle calls for it, 🚨 only for breaking news, nothing decorative.\n'
            f'Suggested topic→emoji anchors (use only if relevant, never force them): {_EMOJI_HINT}.\n'
            f'{_FACT_RULE}\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
        'variant_angles': [
            {'label': 'Viral',        'instruction': 'ANGLE: write this to go viral — bold provocative headline that stops the scroll, then 1-2 sentences that build tension or surprise, a short punchy closing line that makes people want to share or comment. Tone: energetic, opinionated, slightly dramatic but fact-grounded. No labeled bullets, no source line.'},
            {'label': 'Analysis',     'instruction': 'ANGLE: critical analyst voice — go beyond the headline, explain the deeper implications, challenge the obvious reading, or frame what most people are missing. Tone: sharp, skeptical, intellectually honest. No labeled bullets, no source line.'},
            {'label': 'To the point', 'instruction': 'ANGLE: maximum brevity — one bold headline, then 2-3 tight sentences that say exactly what happened and why it matters, nothing else. No bullet points, no labeled fields, no source line. Aim for the lower end of the character range.'},
        ],
    },
    'Instagram': {
        'maxChars': 2200, 'maxTokens': 700, 'temperature': 0.4,
        'emoji_policy': 'liberal but purposeful, semantically matched to topic — never decorative spam',
        'system': lambda brand, sent, sibling_copy=None: (
            f'You are the Instagram editor for {brand}, writing captions for a visual-first, scroll-fast audience. Sentiment: {sent}.\n'
            'PERSONA: energetic storyteller — makes a market headline feel like a moment worth stopping for.\n'
            'STRUCTURE: a strong opening hook line, a short storytelling body that builds context and stakes, a clear closing CTA (e.g. "Tap in for the full breakdown" / "Where do you stand?").\n'
            'HARD RULE: the "copy" field must be PURE PROSE with ZERO hashtags in it. Put your 5-10 discovery hashtags ONLY in the separate "hashtags" array — they are appended to the caption automatically.\n'
            'EMOJI POLICY: liberal but purposeful — pick emojis that semantically match the topic, never spam the same emoji repeatedly.\n'
            f'Suggested topic→emoji anchors (use only if relevant): {_EMOJI_HINT}.\n'
            f'{_FACT_RULE}\n'
            'EXAMPLE OF THE VOICE (do not reuse content, only mirror tone/structure). Note: copy has NO hashtags — they live in the array:\n'
            '{ "copy": "Ethereum just flipped a 3-year resistance level into support 📈\\n\\nWhile most were watching Bitcoin, ETH quietly built the kind of base that precedes real moves — and on-chain data shows whales are accumulating again.\\n\\nIs this the setup before the next leg up, or another fakeout? Drop your call below 👇", "hashtags": ["#Ethereum","#ETH","#CryptoMarkets","#Web3","#OnChainData","#BullMarket","#DeFi"] }\n'
            'Respond with JSON: { "copy": "...", "hashtags": ["#Tag1"] }'
            + _sibling_block(sibling_copy, 'X')
        ),
    },
}

# ── Emoji cleanup: collapse runs and cap counts per platform ──────────────────
_EMOJI_RE = re.compile(
    '([\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF\U0001F1E6-\U0001F1FF])'
)
_EMOJI_CAP = {'X': 0, 'Telegram': 3, 'Instagram': 8}

def clean_emojis(text, platform):
    if not text:
        return text
    # collapse runs of 3+ identical emoji into a single instance
    text = re.sub(r'(' + _EMOJI_RE.pattern + r')\1{2,}', r'\1', text)
    cap = _EMOJI_CAP.get(platform)
    if cap is None:
        return text
    seen = 0
    out = []
    for ch in text:
        if _EMOJI_RE.fullmatch(ch):
            if seen >= cap:
                continue
            seen += 1
        out.append(ch)
    return ''.join(out)

def smart_truncate(text, limit=280):
    """Cut to the last full word/token (never mid-word, mid-hashtag, or mid-$TICKER)."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(' ', 1)[0]
    return cut.rstrip(' .,;:–—-') + '…'


# ── Hashtag cleanup: copy body must be pure prose, tags live only in the array ─
_HASHTAG_RE = re.compile(r'#[\w]+(?:[/_-][\w]+)*')
# A trailing run of hashtags is often glued to the copy with a label/separator
# the model invents ("Topics:", "Tags:", "·", "—", "|"). Strip that too so the
# body ends on a clean sentence, not a dangling "Topics:".
_TRAILING_GLUE_RE = re.compile(
    r'\s*[·\-—|:]?\s*(?:Topics?|Tags?|Hashtags?)?\s*[:\-—]?\s*$',
    re.IGNORECASE,
)


def strip_hashtags_from_copy(copy, hashtags=None):
    """Return (clean_copy, merged_hashtags).

    The `copy` body must NEVER contain hashtags — they belong only in the
    separate `hashtags` array (which the post handler appends as its own block).
    Models routinely fold tags into the body anyway, so this is the single source
    of truth that enforces the contract. Any hashtags found in the body are
    extracted, de-duplicated (case-insensitive), and appended to the array in
    their original order of appearance — so nothing the model wrote is lost.
    """
    if not copy:
        return copy, list(hashtags or [])
    body_tags = _HASHTAG_RE.findall(copy)
    clean = _HASHTAG_RE.sub('', copy)
    # Collapse the double-spaces / dangling separators left behind, and trim.
    clean = re.sub(r'[ \t]{2,}', ' ', clean)
    clean = re.sub(r'\s*\n\s*', '\n', clean)
    clean = _TRAILING_GLUE_RE.sub('', clean).strip(' \t\n·—-|:')
    # Merge body tags into the array (existing array first, then new ones),
    # dedup case-insensitive so a tag can't appear twice.
    merged = list(hashtags or [])
    seen = {t.lower() for t in merged}
    for t in body_tags:
        if t.lower() not in seen:
            merged.append(t)
            seen.add(t.lower())
    return clean, merged

# ── Brand visual tones for image generation ─────────────────────────────────
BRAND_VISUAL_TONE = {
    'MGC Coin':         'high-energy gaming utility, black and signal-yellow palette, competitive digital worlds',
    'Ranking Platform': 'playful competitive gaming editorial, deep aubergine with hot pink, mint, orange, and white sticker graphics',
    'Oasis Coin':       'restrained monochrome cosmic editorial, absolute black, graphite, lunar silver, and source-verified emerald data',
    'Jewelry Coin':     'bright pearl-lavender crystal luxury, platinum jewelry, glass capsules, and creator-led digital-to-physical craft',
    'Industrial Token': 'premium Industry 4.0 editorial, deep indigo and ultraviolet atmosphere, metallic gold machinery, realistic infrastructure, and clear factual hierarchy',
}

# ── Per-brand identity hashtag, always prepended to generated copy hashtags ──
BRAND_HASHTAGS = {
    'MGC Coin':         '#MetaGamesCoin',
    'Ranking Platform': '#RankingGame',
    'Oasis Coin':       '#RZOasis',
    'Jewelry Coin':     '#JewelryToken',
    'Industrial Token': '#IndustrialToken',
}

# Case- and space-insensitive index of BRAND_HASHTAGS. Built once at import.
_BRAND_TAG_INDEX = {k.replace(' ', '').lower(): v for k, v in BRAND_HASHTAGS.items()}


def brand_tag_for(media):
    """Canonical identity hashtag for a brand value, or None if unknown.

    Tolerant to spacing and case. Shared by copy generation and the post handlers
    so both layers agree on the media-name hashtag.
    """
    if not media:
        return None
    return _BRAND_TAG_INDEX.get(str(media).replace(' ', '').lower())


def prepend_brand_tag(hashtags, media):
    """Force the brand identity hashtag to position 0, de-duplicating any copy.

    Used at both generation time (copy.py) and post time (social.py) as
    defence-in-depth: a stale/empty hashtags array or a brand-name spelling
    mismatch can never drop the media-name tag.
    """
    brand_tag = brand_tag_for(media)
    if not brand_tag:
        return list(hashtags or [])
    others = [t for t in (hashtags or []) if str(t).lower() != brand_tag.lower()]
    return [brand_tag] + others

# ── Promotional copy: per-brand product pitch injected when promoMode=True ────
BRAND_PROMO_PITCH = {
    'MGC Coin': (
        "Meta Games Coin (MGC) is the reward and utility token at the center of the RZ Ecosystem. "
        "Born alongside Ranking.Game, it is designed to reward participation, performance, and "
        "contribution across connected gaming and community experiences."
    ),
    'Ranking Platform': (
        "Ranking is a competitive gaming platform, not a token. It connects players, teams, "
        "organizers, referees, fans, and venues through profiles, PvP matches, tournaments, "
        "game-specific rankings, communities, and eligible MGC rewards."
    ),
    'Oasis Coin': (
        "OASIS is the planned gaming and metaverse utility token for the long-term RZOASIS Galaxy. "
        "The complete metaverse is still in development and the token does not yet have active "
        "ecosystem utility; its intended uses are designed to grow with future games and worlds."
    ),
    'Jewelry Coin': (
        "Jewelry Token is the proposed BEP-20 utility token for a blockchain gaming platform built "
        "around virtual gem extraction, digital jewelry design, NFT minting, an in-game marketplace, "
        "and a planned path from eligible digital designs to physical jewelry."
    ),
    'Industrial Token': (
        "Industrial Token (INDUSTRIAL) is a BEP-20 ecosystem positioned around gamified industrial "
        "marketing, global rankings, educational simulations, decentralized industrial services, and "
        "sustainability incentives. Roadmap and whitepaper features must be framed as proposed unless "
        "a current approved source confirms they are live."
    ),
}

# ── OpenRouter image generation model modalities ──────────────────────────────
OPENROUTER_IMAGE_MODELS = {
    'google/gemini-3.1-flash-image-preview':['image', 'text'],
    'google/gemini-3-pro-image-preview':    ['image', 'text'],
    'openai/gpt-5.4-image-2':              ['image', 'text'],
    'recraft/recraft-v4-pro':              ['image'],
}

# ── Art Director tunables (used by image_pipeline) ────────────────────────────
# Note: reasoning models (GPT-5.x, DeepSeek, Gemini Flash) spend tokens on
# internal "thinking"; if the budget is too small they burn it all on reasoning
# and emit ZERO visible content (finish_reason=length), which is the error that
# surfaces in the UI as "Image generation failed". 4000 leaves comfortable room.
ART_DIRECTOR_TEMPERATURE = 0.95
ART_DIRECTOR_MAX_TOKENS = 4000

_CORE_AXES = ('environment', 'camera', 'energy', 'mood_accent')

# ── Brief validation guardrails (used by image_pipeline) ──────────────────────
_BANNED_SUBJECT_TERMS = [
    'text', 'label', 'logo', 'watermark', 'rzwire', 'mgc coin', 'meta games coin',
    'ranking platform', 'ranking.game', 'oasis coin', 'rzoasis', 'jewelry coin',
    'jewelry token', 'industrial token', 'industrial.game',
]
_WALLET_ADDRESS_RE = re.compile(r'0x[a-fA-F0-9]{6,}')

# ── Activity batching window (used by handlers.account) ───────────────────────
BATCH_WINDOW = _timedelta(minutes=10)
VALID_ACTIONS = {'approved', 'scheduled'}

# ── Background scheduler ──────────────────────────────────────────────────────
SCHEDULER_INTERVAL_SEC = 30
