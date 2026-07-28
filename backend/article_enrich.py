"""
Article enrichment: fetch each shortlisted article's source page, extract its
readable body, and produce a tight factual summary so the AI editorial-select
model sees more of the story than the ~220-char RSS lede.

Graceful fallback chain (the pipeline is NEVER worse off than today):
  summary (LLM)  →  raw body chunk  →  raised-cap RSS lede (desc[:450])

Resilience:
  - Any per-article error is caught; the item always gets SOME text.
  - The whole enrich step is best-effort: an unexpected exception leaves the
    shortlist untouched and the existing pipeline runs exactly as before.
  - Summaries are cached in-memory per URL for the life of the process, so
    re-analyzing the same articles is instant.

No new pip dependencies — reuses already-installed `requests` and `lxml`.
"""
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import requests

try:
    from lxml import html as _lxml_html
    _LXML_OK = True
except Exception as _e:  # pragma: no cover
    print(f'[article_enrich] lxml not available, will fall back to regex: {_e}', file=sys.stderr)
    _LXML_OK = False

from config import CHAT_MODEL, OPENROUTER_KEY
from llm import openrouter_chat_text

# Browser-like headers reduce the chance of being blocked as a bot.
_HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

_FETCH_TIMEOUT = 6          # seconds per article fetch
_MAX_BODY_CHARS = 2000      # cap on extracted body text passed to the summarizer
_FALLBACK_CAP = 450         # raised RSS-lede cap used when scraping fails
_MAX_WORKERS = 6            # parallel fetch + summarize

# ── In-memory summary cache (URL → enriched text) ───────────────────────────
_cache: dict[str, str] = {}
_cache_lock = threading.Lock()


# ── Body fetching + extraction ───────────────────────────────────────────────
def _strip_tags_regex(html: str) -> str:
    """Last-resort text extraction when lxml can't parse — drop tags, scripts, styles."""
    html = re.sub(r'<(script|style|nav|header|footer)[^>]*>.*?</\1>', ' ', html,
                  flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()


def _extract_text(html: str) -> str:
    """Pull readable article text from HTML, preferring <p>/<article> content."""
    if not _LXML_OK:
        return _strip_tags_regex(html)[:_MAX_BODY_CHARS]
    try:
        doc = _lxml_html.fromstring(html)
        # Drop obvious non-content nodes before extracting text.
        for bad in doc.xpath('//script | //style | //nav | //header | //footer | //aside | //form'):
            bad.getparent().remove(bad)
        # Prefer paragraph text — it carries the actual story.
        paras = doc.xpath('//p//text() | //article//text()')
        text = ' '.join(t.strip() for t in paras if t and t.strip())
        if len(text) < 120:
            # Too little paragraph text (SPA / paywall) — fall back to full doc text.
            text = doc.text_content()
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:_MAX_BODY_CHARS]
    except Exception:
        return _strip_tags_regex(html)[:_MAX_BODY_CHARS]


def fetch_article_body(url: str) -> str | None:
    """Fetch a single article page and return readable text, or None on any failure."""
    if not url or not url.startswith('http'):
        return None
    try:
        r = requests.get(url, headers=_HEADERS, timeout=_FETCH_TIMEOUT, allow_redirects=True)
        if r.status_code != 200 or not r.text:
            return None
        # Skip obviously non-HTML responses (PDFs, JSON, etc.)
        ctype = r.headers.get('Content-Type', '').lower()
        if 'html' not in ctype and 'xml' not in ctype and 'text' not in ctype:
            return None
        text = _extract_text(r.text)
        return text if len(text) >= 120 else None
    except Exception:
        return None


# ── Summarization ────────────────────────────────────────────────────────────
def summarize_body(body: str, title: str) -> str:
    """One cheap-LLM call to condense the body into a tight factual summary."""
    if not body:
        return ''
    sys_msg = (
        'You are a news summarizer for a crypto editorial team. Summarize the article body '
        'into a dense ~120-word factual brief: what happened, the key numbers, who is involved, '
        'and why it matters. '
        'HARD RULE: use only facts present in the text. Do not invent figures, quotes, names, or outcomes. '
        'Plain prose, no headings, no bullet points, no hashtags.'
    )
    user_msg = f'Title: {title}\n\nArticle body:\n{body}'
    return openrouter_chat_text(
        CHAT_MODEL['id'],
        [{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': user_msg}],
        temperature=0.2,
        max_tokens=300,
    ).strip()


# ── Per-article enrichment worker ────────────────────────────────────────────
def _enrich_one(item: dict) -> None:
    """Populate item['_enriched'] with a summary, or a fallback. Never raises."""
    url = item.get('link') or item.get('url') or ''
    desc = (item.get('desc') or '').replace('\n', ' ').strip()

    # Cache hit (same URL seen earlier this process) — reuse.
    if url:
        with _cache_lock:
            if url in _cache:
                item['_enriched'] = _cache[url]
                return

    enriched = ''
    body = fetch_article_body(url) if url else None
    if body and len(body) >= 120:
        # We got real body text — try to summarize it.
        try:
            summary = summarize_body(body, item.get('title', ''))
            if summary and len(summary) >= 40:
                enriched = summary
            else:
                enriched = body[:_FALLBACK_CAP]   # summary came back empty → raw chunk
        except Exception as e:
            print(f'[article_enrich] summarize failed for {url}: {e}', file=sys.stderr)
            enriched = body[:_FALLBACK_CAP]       # LLM error → raw chunk
    else:
        # Fetch failed/blocked — fall back to the raised-cap RSS lede.
        enriched = desc[:_FALLBACK_CAP]

    item['_enriched'] = enriched
    if url and enriched:
        with _cache_lock:
            _cache[url] = enriched


def enrich_shortlist(shortlist: list[dict]) -> None:
    """Mutate each shortlist item in place, adding an '_enriched' text field.

    Best-effort: any unexpected exception leaves the shortlist unchanged so the
    existing editorial pipeline runs exactly as before.
    """
    if not shortlist:
        return
    if not OPENROUTER_KEY:
        # No API key → summarization can't run; just raise the lede cap as fallback.
        for item in shortlist:
            item['_enriched'] = (item.get('desc') or '')[:_FALLBACK_CAP]
        return
    try:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            list(pool.map(_enrich_one, shortlist))
    except Exception as e:
        print(f'[article_enrich] enrich_shortlist failed, leaving shortlist unchanged: {e}',
              file=sys.stderr)
