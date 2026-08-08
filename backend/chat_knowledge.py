"""Reviewed knowledge corpus and local BM25 retrieval for the chat assistant.

The corpus is built from the configured brand sources, the documented website
overview, and reviewed Markdown/DOCX/PDF files under ``brand_docs/chat``.  This
module never calls an external service.  Semantic vectors are managed by
``chat_index`` so BM25 remains available when EmbeddingGemma is offline.
"""

import hashlib
import math
import re
import sys
from pathlib import Path

from config import BRAND_PROMO_PITCH, MEDIA_LIST

try:
    import brand_docs as _brand_docs
    _BRAND_DOCS_OK = True
except Exception as exc:  # noqa: BLE001
    print(f'[chat_knowledge] brand docs unavailable: {exc}', file=sys.stderr)
    _BRAND_DOCS_OK = False


_DROPIN_DIR = Path(__file__).parent / 'brand_docs' / 'chat'
_PERSIAN_RE = re.compile(r'[\u0600-\u06ff]')

RZWIRE_PLATFORM_OVERVIEW = """\
RZWire is an AI-powered, multi-brand social publishing workspace. It accepts a
topic or source feed, routes material across six distinct projects, and prepares
brand-aware copy and images for Telegram, X/Twitter, and Instagram drafts.

The configured brands include:
- MGC Coin: the reward and utility token of the RZ gaming ecosystem.
- Ranking Platform: a competitive gaming platform, not a token.
- Oasis Coin: the planned gaming and metaverse utility token for RZOASIS Galaxy.
- Jewelry Coin: the proposed utility token for a digital-jewelry gaming platform.
- Industrial Token: the proposed BEP-20 utility token for an ecosystem combining
  gamified industrial marketing, industrial services, education, and
  sustainability incentives.
- Real Estate Token: the proposed BEP-20 property ecosystem for real-world and
  digital property experiences, transparent ownership records, fractional
  participation, and community-led real estate activity.

Workspace flow:
1. In the sidebar, enter a topic or import RSS, choose platforms, media brands,
   sources, and editorial models, then select Analyze.
2. Analyze scores and routes stories to the most suitable brand and platform.
3. Cards can generate platform-specific copy and a promotional image.
4. The Preview panel can edit copy, regenerate variants or images, and save
   approved local work. External posting and Sheets writes are disabled until
   the new RZWire integrations are configured.
5. The Account page shows activity, saved cards, scheduled posts, and stats.
6. The integration status endpoint shows whether publishing and Sheets are enabled.

The assistant explains documented features and current card context. It cannot
click controls, publish, schedule, edit, or otherwise act for the user.
"""

# Kept for compatibility with callers that import this constant. No remote LLM
# receives it in the local-RAG implementation.
SYSTEM_PROMPT = """\
Answer only from reviewed RZWire website and brand knowledge. Do not
invent facts or claim to perform actions. Respond in Persian when the question
uses Persian script; otherwise respond in English.
"""

_BRAND_ALIASES = {
    'MGC Coin': [
        'mgc coin', 'mgc', 'meta games coin', 'metagamescoin',
        'metagamesc', 'metagamescoin_io',
    ],
    'Ranking Platform': ['ranking platform', 'ranking.game', 'ranking game', 'rankingdotgame'],
    'Oasis Coin': [
        'oasis coin', 'oasis token', 'rzoasis', 'rz oasis galaxy', 'oasis_rz',
        'rzoasis_channel',
    ],
    'Jewelry Coin': [
        'jewelry coin', 'jewellery coin', 'jewelry token', 'jewellery token',
        'jewelry game', 'jewellery game', 'jewellery.game', 'jewelry_token',
    ],
    'Industrial Token': [
        'industrial token', 'industrial.game', 'industrial game',
        'industrial ecosystem', 'industrial_token', 'industrial',
    ],
    'Real Estate Token': [
        'real estate token', 'realestate token', 'realestate', 'real-estate.game',
        'property tokenization', 'digital real estate', 'real_estate_token',
    ],
}
_DROPIN_BRANDS = {
    'mgc-coin': 'MGC Coin',
    'mgc': 'MGC Coin',
    'ranking-platform': 'Ranking Platform',
    'ranking': 'Ranking Platform',
    'oasis-coin': 'Oasis Coin',
    'oasis': 'Oasis Coin',
    'jewelry-coin': 'Jewelry Coin',
    'jewellery-coin': 'Jewelry Coin',
    'industrial-token': 'Industrial Token',
    'industrial': 'Industrial Token',
    'real-estate-token': 'Real Estate Token',
    'real-estate': 'Real Estate Token',
    'realestate': 'Real Estate Token',
}


def _slug(value):
    value = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return value or hashlib.sha256(value.encode('utf-8')).hexdigest()[:12]


def _language(text):
    return 'fa' if _PERSIAN_RE.search(text or '') else 'en'


def _tokenize(value):
    """Unicode-aware word tokenizer supporting English and Persian."""
    return re.findall(r'[^\W_]+', (value or '').lower(), flags=re.UNICODE)


def _split_chunks(text, max_chars=1700, overlap=180):
    """Split at paragraphs/headings, with a bounded overlap for long sections."""
    if not text:
        return []
    paragraphs = [part.strip() for part in re.split(r'\n\s*\n', text) if part.strip()]
    chunks = []
    buffer = ''
    for paragraph in paragraphs:
        if buffer and _language(paragraph) != _language(buffer):
            chunks.append(buffer.strip())
            buffer = paragraph
            continue
        if len(paragraph) > max_chars:
            step = max_chars - overlap
            for start in range(0, len(paragraph), step):
                piece = paragraph[start:start + max_chars].strip()
                if piece:
                    chunks.append(piece)
            continue
        candidate = f'{buffer}\n\n{paragraph}' if buffer else paragraph
        if buffer and len(candidate) > max_chars:
            chunks.append(buffer.strip())
            tail = buffer[-overlap:].strip()
            buffer = f'{tail}\n\n{paragraph}'.strip() if tail else paragraph
        else:
            buffer = candidate
    if buffer.strip():
        chunks.append(buffer.strip())
    return chunks


def _section_title(text, fallback):
    for line in (text or '').splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            return stripped.lstrip('#').strip() or fallback
    return fallback


def _infer_dropin_brand(path):
    stem = path.stem.lower()
    return next((brand for prefix, brand in _DROPIN_BRANDS.items() if stem.startswith(prefix)), None)


def _load_documents():
    documents = []
    configured_brands = list(MEDIA_LIST)
    if _BRAND_DOCS_OK and hasattr(_brand_docs, 'available_brands'):
        configured_brands.extend(_brand_docs.available_brands())
    for brand in dict.fromkeys(configured_brands):
        fallback = BRAND_PROMO_PITCH.get(brand, '')
        if _BRAND_DOCS_OK and hasattr(_brand_docs, 'get_brand_documents'):
            brand_sources = _brand_docs.get_brand_documents(brand)
        else:
            text = _brand_docs.get_brand_doc(brand, fallback=fallback) if _BRAND_DOCS_OK else fallback
            source_filename = (
                _brand_docs.get_brand_source_path(brand)
                if _BRAND_DOCS_OK and hasattr(_brand_docs, 'get_brand_source_path')
                else f'{_slug(brand)}.docx'
            )
            brand_sources = ((source_filename, text),)
        if not brand_sources and fallback:
            brand_sources = ((f'{_slug(brand)}-fallback.txt', fallback),)
        for source_filename, text in brand_sources:
            documents.append({
                'sourceId': f'brand-source-{_slug(brand)}-{_slug(source_filename)}',
                'title': f'{brand} source: {Path(source_filename).stem}',
                'brand': brand,
                'sourcePath': f'brand_docs/{source_filename}',
                'content': text,
            })

    documents.append({
        'sourceId': 'website-overview',
        'title': 'RZWire website overview',
        'brand': '',
        'sourcePath': 'chat_knowledge.py',
        'content': RZWIRE_PLATFORM_OVERVIEW,
    })

    if _DROPIN_DIR.is_dir():
        for path in sorted(_DROPIN_DIR.iterdir()):
            if path.name.lower() == 'readme.md':
                continue
            try:
                if path.suffix.lower() == '.md':
                    content = path.read_text(encoding='utf-8')
                elif path.suffix.lower() == '.docx':
                    from docx import Document
                    content = '\n'.join(p.text for p in Document(str(path)).paragraphs)
                elif path.suffix.lower() == '.pdf':
                    from pypdf import PdfReader
                    content = '\n\n'.join(
                        f'[Page {index}]\n{page_text}'
                        for index, page in enumerate(PdfReader(str(path)).pages, start=1)
                        if (page_text := (page.extract_text() or '').strip())
                    )
                else:
                    continue
                documents.append({
                    'sourceId': f'reviewed-{_slug(path.stem)}',
                    'title': path.stem.replace('-', ' ').title(),
                    'brand': _infer_dropin_brand(path) or '',
                    'sourcePath': f'brand_docs/chat/{path.name}',
                    'content': content,
                })
            except Exception as exc:  # noqa: BLE001
                print(f'[chat_knowledge] could not read {path.name}: {exc}', file=sys.stderr)
    return documents


def _build_index():
    chunks = []
    for document in _load_documents():
        for position, content in enumerate(_split_chunks(document['content'])):
            section = _section_title(content, document['title'])
            stable_key = f"{document['sourceId']}:{position}"
            chunk_id = hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:24]
            chunks.append({
                'id': chunk_id,
                'title': document['title'],
                'section': section,
                'brand': document['brand'],
                'language': _language(content),
                'sourcePath': document['sourcePath'],
                'content': content,
                'contentHash': hashlib.sha256(content.encode('utf-8')).hexdigest(),
            })

    postings = {}
    lengths = []
    for index, chunk in enumerate(chunks):
        tokens = _tokenize(chunk['content'])
        lengths.append(len(tokens))
        frequencies = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        for token, frequency in frequencies.items():
            postings.setdefault(token, {})[index] = frequency
    document_frequency = {token: len(rows) for token, rows in postings.items()}
    average_length = sum(lengths) / len(lengths) if lengths else 1.0
    return chunks, postings, document_frequency, lengths, average_length


_KNOWLEDGE, _POSTINGS, _DF, _CHUNK_LENGTHS, _AVERAGE_LENGTH = _build_index()
_KNOWLEDGE_VERSION = hashlib.sha256(
    '\n'.join(
        f"{chunk['id']}|{chunk['brand']}|{chunk['section']}|{chunk['contentHash']}"
        for chunk in _KNOWLEDGE
    ).encode('utf-8')
).hexdigest()[:20]

print(
    f'[chat_knowledge] indexed {len(_KNOWLEDGE)} reviewed chunks '
    f'(version {_KNOWLEDGE_VERSION})',
    file=sys.stderr,
)


def knowledge_version():
    return _KNOWLEDGE_VERSION


def knowledge_chunks():
    """Return shallow copies so index metadata cannot be mutated by callers."""
    return [dict(chunk) for chunk in _KNOWLEDGE]


def detect_brand(question):
    lowered = (question or '').lower()
    for brand, aliases in _BRAND_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            return brand
    return None


_BM25_K1 = 1.5
_BM25_B = 0.75


def bm25_results(question, k=10, brand_hint=None):
    """Return metadata-rich lexical results with scores normalized to 0..1."""
    tokens = _tokenize(question)
    if not tokens or not _KNOWLEDGE:
        return []
    brand = detect_brand(question) or brand_hint
    eligible = {
        index for index, chunk in enumerate(_KNOWLEDGE)
        if not brand or chunk['brand'] in ('', brand)
    }
    scores = [0.0] * len(_KNOWLEDGE)
    corpus_size = len(_KNOWLEDGE)
    for token in tokens:
        posting = _POSTINGS.get(token)
        if not posting:
            continue
        frequency = _DF[token]
        inverse_document_frequency = math.log(
            1 + (corpus_size - frequency + 0.5) / (frequency + 0.5)
        )
        for index, term_frequency in posting.items():
            if index not in eligible:
                continue
            denominator = term_frequency + _BM25_K1 * (
                1 - _BM25_B + _BM25_B * (_CHUNK_LENGTHS[index] / _AVERAGE_LENGTH)
            )
            scores[index] += inverse_document_frequency * (
                term_frequency * (_BM25_K1 + 1)
            ) / denominator

    ranked = [index for index in eligible if scores[index] > 0]
    ranked.sort(key=lambda index: scores[index], reverse=True)
    maximum = scores[ranked[0]] if ranked else 1.0
    results = []
    for index in ranked[:k]:
        result = dict(_KNOWLEDGE[index])
        result['bm25Score'] = scores[index] / maximum if maximum else 0.0
        result['bm25Raw'] = scores[index]
        results.append(result)
    return results


def retrieve(question, k=4, brand_hint=None):
    """Compatibility wrapper returning ``(title, content)`` tuples."""
    return [
        (result['title'], result['content'])
        for result in bm25_results(question, k=k, brand_hint=brand_hint)
    ]


def chunks_block(question, k=4, brand_hint=None):
    """Compatibility formatter retained for diagnostics and older tests."""
    hits = retrieve(question, k=k, brand_hint=brand_hint)
    if not hits:
        return ''
    parts = ['\n\nRelevant reviewed knowledge:']
    parts.extend(f'[{title}]\n{content}' for title, content in hits)
    return '\n\n'.join(parts)
