"""Public Telegram channel web-page extractor.

Reads public https://t.me/s/<channel> pages and returns RSS-shaped news items:
title, desc, link, pubDate, source.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urlparse


DEFAULT_TELEGRAM_SOURCES = {
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

# Telegram's modern usernames have a five-character minimum, but established
# public legacy channels such as @gram are four characters long.
_CHANNEL_RE = re.compile(r'^[A-Za-z0-9_]{4,32}$')
_SPACE_RE = re.compile(r'[ \t\r\f\v]+')
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')
_LEADING_EDITORIAL_LABEL_RE = re.compile(
    r'^(?:[\U0001F1E6-\U0001F1FF\U0001F300-\U0001FAFF\U00002600-\U000027BF]\ufe0f?\s*)*'
    r'(?:[A-Z][A-Z0-9&/.-]{1,24}(?:\s+[A-Z][A-Z0-9&/.-]{1,24}){0,3})\s*:\s+'
)
_FOOTER_LINES = {
    'News | Markets | YouTube',
    'News|Markets|YouTube',
}
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; RZWire/1.0; +https://rzwire.local)',
    'Accept': 'text/html,application/xhtml+xml',
}


@dataclass
class TelegramPost:
    channel: str
    source: str
    title: str
    desc: str
    link: str
    pubDate: str
    message_id: str
    telegramText: str
    views: int | None = None
    viewsLabel: str = ''

    def as_article(self) -> dict:
        return {
            'title': self.title,
            'desc': self.desc,
            'link': self.link,
            'pubDate': self.pubDate,
            'source': self.source,
            'channel': self.channel,
            'messageId': self.message_id,
            'telegramText': self.telegramText,
            'sourceType': 'telegram',
            'views': self.views,
            'viewsLabel': self.viewsLabel,
        }


def normalize_channel(value: str) -> str:
    raw = (value or '').strip()
    if not raw:
        raise ValueError('channel is required')

    if raw.startswith('@'):
        raw = raw[1:]
    elif raw.startswith(('http://', 'https://')):
        parsed = urlparse(raw)
        host = parsed.netloc.lower()
        if host not in ('t.me', 'telegram.me'):
            raise ValueError('only t.me public Telegram URLs are supported')
        parts = [p for p in parsed.path.split('/') if p]
        if parts and parts[0] == 's':
            parts = parts[1:]
        raw = parts[0] if parts else ''

    if raw.startswith('+') or raw.lower().startswith(('joinchat', 'c/')):
        raise ValueError('private or invite-only Telegram channels are not supported')
    if not _CHANNEL_RE.fullmatch(raw):
        raise ValueError('invalid Telegram public channel name')
    return raw


def public_channel_url(channel: str) -> str:
    return f'https://t.me/s/{normalize_channel(channel)}'


class _TelegramPageParser(HTMLParser):
    def __init__(self, channel: str, source: str):
        super().__init__(convert_charrefs=True)
        self.channel = channel
        self.source = source
        self.posts: list[TelegramPost] = []
        self._current: dict | None = None
        self._message_depth = 0
        self._text_depth = 0
        self._views_depth = 0
        self._views_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        attr = {k: v or '' for k, v in attrs}
        classes = set((attr.get('class') or '').split())

        if tag == 'div' and 'tgme_widget_message' in classes and attr.get('data-post'):
            data_post = attr['data-post']
            message_id = data_post.rsplit('/', 1)[-1]
            self._current = {
                'message_id': message_id,
                'link': f'https://t.me/{data_post}',
                'pubDate': '',
            }
            self._message_depth = 1
            self._text_depth = 0
            self._views_depth = 0
            self._views_parts = []
            self._text_parts = []
            return

        if not self._current:
            return

        if tag == 'br' and self._text_depth:
            self._text_parts.append('\n')
            return

        self._message_depth += 1

        if tag == 'a' and 'tgme_widget_message_date' in classes and attr.get('href'):
            self._current['link'] = attr['href']

        if tag == 'time' and attr.get('datetime'):
            self._current['pubDate'] = _normalize_datetime(attr['datetime'])

        if tag == 'div' and 'tgme_widget_message_text' in classes:
            self._text_depth = 1
        elif self._text_depth:
            self._text_depth += 1

        if tag == 'span' and 'tgme_widget_message_views' in classes:
            self._views_depth = 1
        elif self._views_depth:
            self._views_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        if tag == 'br' and self._current and self._text_depth:
            self._text_parts.append('\n')
            return
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str):
        if not self._current:
            return

        if self._text_depth:
            self._text_depth -= 1
        if self._views_depth:
            self._views_depth -= 1

        self._message_depth -= 1
        if self._message_depth <= 0:
            self._commit_current()

    def handle_data(self, data: str):
        if self._current and self._text_depth and data:
            self._text_parts.append(data)
        if self._current and self._views_depth and data:
            self._views_parts.append(data)

    def _commit_current(self):
        assert self._current is not None
        text = clean_text(''.join(self._text_parts))
        display_text = strip_leading_editorial_label(text)
        views_label = ''.join(self._views_parts).strip()
        if display_text and self._current.get('pubDate'):
            self.posts.append(TelegramPost(
                channel=self.channel,
                source=self.source,
                title=make_title(display_text),
                desc=display_text[:400],
                link=self._current.get('link') or '',
                pubDate=self._current['pubDate'],
                message_id=self._current.get('message_id') or '',
                telegramText=text,
                views=parse_view_count(views_label),
                viewsLabel=views_label,
            ))
        self._current = None
        self._message_depth = 0
        self._text_depth = 0
        self._views_depth = 0
        self._views_parts = []
        self._text_parts = []


def clean_text(text: str) -> str:
    lines = []
    for line in text.replace('\xa0', ' ').splitlines():
        line = _SPACE_RE.sub(' ', line).strip()
        if line and line not in _FOOTER_LINES:
            lines.append(line)
    return '\n'.join(lines).strip()


def make_title(text: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), '')
    first_line = re.sub(r'https?://\S+', '', first_line).strip()
    if len(first_line) <= 140:
        return first_line
    first_sentence = _SENTENCE_RE.split(first_line, 1)[0].strip()
    if 20 <= len(first_sentence) <= 140:
        return first_sentence
    return first_line[:137].rstrip() + '...'


def strip_leading_editorial_label(text: str) -> str:
    lines = (text or '').splitlines()
    for idx, line in enumerate(lines):
        if not line.strip():
            continue
        cleaned = _LEADING_EDITORIAL_LABEL_RE.sub('', line.strip(), count=1).strip()
        lines[idx] = cleaned or line.strip()
        break
    return '\n'.join(lines).strip()


def parse_view_count(raw: str) -> int | None:
    value = (raw or '').strip().replace(',', '')
    if not value:
        return None
    match = re.fullmatch(r'(\d+(?:\.\d+)?)([KMB]?)', value, flags=re.I)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2).upper()
    multiplier = {'': 1, 'K': 1_000, 'M': 1_000_000, 'B': 1_000_000_000}[suffix]
    return int(number * multiplier)


def parse_telegram_public_html(html: str, channel: str, source: str | None = None) -> list[dict]:
    channel = normalize_channel(channel)
    parser = _TelegramPageParser(channel, source or channel)
    parser.feed(html or '')
    parser.close()
    return [post.as_article() for post in parser.posts]


def fetch_telegram_public_posts(
    channel: str,
    *,
    source: str | None = None,
    hours: int | None = None,
    limit: int = 30,
    session=None,
) -> list[dict]:
    import requests

    channel = normalize_channel(channel)
    client = session or requests
    response = client.get(public_channel_url(channel), headers=_HEADERS, timeout=15)
    response.raise_for_status()

    posts = parse_telegram_public_html(response.text, channel, source=source)
    posts = filter_posts_by_hours(posts, hours)
    posts.sort(key=lambda post: post.get('pubDate') or '', reverse=True)
    return posts[:max(1, min(int(limit or 30), 100))]


def fetch_many_telegram_public_posts(
    channels: Iterable[str],
    *,
    hours: int | None = None,
    limit_per_channel: int = 20,
) -> dict:
    results = []
    errors = {}
    source_lookup = {v.lower(): k for k, v in DEFAULT_TELEGRAM_SOURCES.items()}

    for value in channels:
        try:
            channel = normalize_channel(value)
            source = source_lookup.get(channel.lower(), channel)
            results.extend(fetch_telegram_public_posts(
                channel,
                source=source,
                hours=hours,
                limit=limit_per_channel,
            ))
        except Exception as exc:
            errors[str(value)] = str(exc)

    results.sort(key=lambda post: post.get('pubDate') or '', reverse=True)
    return {'articles': results, 'errors': errors}


def rank_telegram_posts(body: dict) -> dict:
    channels = body.get('channels') or list(DEFAULT_TELEGRAM_SOURCES.values())
    if isinstance(channels, str):
        channels = [c.strip() for c in channels.split(',') if c.strip()]
    hours = int(body.get('hours') or body.get('recencyHours') or 24)
    sort_mode = (body.get('sortMode') or 'views').strip()
    top_n = max(1, min(int(body.get('topN') or 20), 20))

    fetched = fetch_many_telegram_public_posts(
        channels,
        hours=hours,
        limit_per_channel=100,
    )
    articles = fetched.get('articles', [])
    if sort_mode in ('keywords', 'matching_keywords', 'keyword'):
        keywords = _parse_keywords(body.get('topics') or body.get('keywords') or '')
        if len(keywords) < 2:
            raise ValueError('Add at least 2 keywords to use Telegram keyword matching.')
        ranked = rank_by_keyword_match(articles, keywords)[:top_n]
        mode = 'keywords'
    elif sort_mode in ('views_per_source', 'per_source_views', 'source_views'):
        ranked = rank_per_source_rounds(
            articles,
            top_n,
            key=lambda a: (a.get('views') or 0, a.get('pubDate') or ''),
        )
        mode = 'views_per_source'
    elif sort_mode in ('latest_per_source', 'per_source_latest', 'source_latest'):
        ranked = rank_per_source_rounds(
            articles,
            top_n,
            key=lambda a: a.get('pubDate') or '',
        )
        mode = 'latest_per_source'
    elif sort_mode in ('latest', 'date', 'publish_date', 'published'):
        ranked = sorted(
            articles,
            key=lambda a: a.get('pubDate') or '',
            reverse=True,
        )[:top_n]
        mode = 'latest'
    else:
        ranked = sorted(
            articles,
            key=lambda a: (a.get('views') or 0, a.get('pubDate') or ''),
            reverse=True,
        )[:top_n]
        mode = 'views'

    return {
        'articles': ranked,
        'errors': fetched.get('errors', {}),
        'sortMode': mode,
        'topN': len(ranked),
        'fetchedTotal': len(articles),
    }


def rank_per_source_rounds(articles: list[dict], top_n: int, key) -> list[dict]:
    """Return one post per source per round, ordered inside each round by ``key``."""
    posts_by_source: dict[str, list[dict]] = {}
    for article in articles:
        source_key = str(article.get('channel') or article.get('source') or 'unknown')
        posts_by_source.setdefault(source_key, []).append(article)

    for posts in posts_by_source.values():
        posts.sort(key=key, reverse=True)

    ranked = []
    round_index = 0
    while len(ranked) < top_n:
        round_posts = [posts[round_index] for posts in posts_by_source.values() if len(posts) > round_index]
        if not round_posts:
            break
        round_posts.sort(key=key, reverse=True)
        ranked.extend(round_posts[:top_n - len(ranked)])
        round_index += 1
    return ranked


def rank_by_keyword_match(articles: list[dict], keywords: list[str], embedder=None) -> list[dict]:
    if not articles:
        return []
    query = ', '.join(keywords)
    texts = [f"{a.get('title','')}\n{a.get('desc','')}".strip() for a in articles]
    if embedder is None:
        from filtering.embedder import Embedder
        embedder = Embedder()
    embed_result = embedder.embed([query] + texts)
    vectors = embed_result[0] if isinstance(embed_result, tuple) else embed_result
    q_vec = vectors[0]
    ranked = []
    for article, vec in zip(articles, vectors[1:]):
        score = _cosine(q_vec, vec)
        ranked.append({
            **article,
            'keywordScore': round(score, 6),
            'matchedKeywords': keywords,
        })
    ranked.sort(key=lambda a: (a.get('keywordScore') or 0, a.get('views') or 0), reverse=True)
    return ranked


def _parse_keywords(raw: str | list[str]) -> list[str]:
    if isinstance(raw, list):
        parts = raw
    else:
        parts = re.split(r'[,;\n]+', raw or '')
    seen = set()
    keywords = []
    for part in parts:
        word = _SPACE_RE.sub(' ', str(part).strip())
        key = word.lower()
        if word and key not in seen:
            seen.add(key)
            keywords.append(word)
    return keywords


def _cosine(a, b) -> float:
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = sum(float(x) * float(x) for x in a) ** 0.5
    nb = sum(float(y) * float(y) for y in b) ** 0.5
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def filter_posts_by_hours(posts: list[dict], hours: int | None) -> list[dict]:
    if not hours:
        return posts
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours)))
    filtered = []
    for post in posts:
        parsed = _parse_datetime(post.get('pubDate') or '')
        if parsed is None or parsed >= cutoff:
            filtered.append(post)
    return filtered


def _normalize_datetime(raw: str) -> str:
    parsed = _parse_datetime(raw)
    if parsed is None:
        return raw.strip()
    return parsed.isoformat().replace('+00:00', 'Z')


def _parse_datetime(raw: str) -> datetime | None:
    value = (raw or '').strip()
    if not value:
        return None
    if value.endswith('Z'):
        value = value[:-1] + '+00:00'
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
