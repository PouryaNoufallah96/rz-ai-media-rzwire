"""Reliable, bounded RSS fetching for the Multimedia news importer."""

from __future__ import annotations

from dataclasses import dataclass
import html
import re
import threading
import time
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/142.0.0.0 Safari/537.36"
)
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}

MAX_REDIRECTS = 5
MAX_FEED_BYTES = 5 * 1024 * 1024
FRESH_CACHE_SECONDS = 5 * 60
STALE_CACHE_SECONDS = 24 * 60 * 60

# The endpoint is intentionally limited to feeds configured in mmStore.js. This
# prevents the public proxy route from being used to reach private services.
ALLOWED_RSS_HOSTS = {
    "ambcrypto.com",
    "beincrypto.com",
    "bitcoinmagazine.com",
    "blockworks.co",
    "blog.chain.link",
    "blog.chainalysis.com",
    "chain.link",
    "chainalysis.com",
    "coindesk.com",
    "cointelegraph.com",
    "crypto.news",
    "cryptopotato.com",
    "cryptoslate.com",
    "decrypt.co",
    "dlnews.com",
    "news.google.com",
    "newsbtc.com",
    "theblock.co",
    "thedefiant.io",
    "u.today",
    "www.ambcrypto.com",
    "www.beincrypto.com",
    "www.bitcoinmagazine.com",
    "www.blockworks.co",
    "www.chainalysis.com",
    "www.coindesk.com",
    "www.cointelegraph.com",
    "www.cryptopotato.com",
    "www.cryptoslate.com",
    "www.decrypt.co",
    "www.dlnews.com",
    "www.newsbtc.com",
    "www.theblock.co",
    "www.thedefiant.io",
}

# These publishers block the VPS address. Google News provides recent RSS for
# the same publisher domain and is reachable from production. The original feed
# remains first choice when it works.
FEED_FALLBACKS = {
    "https://www.theblock.co/rss.xml": (
        "https://news.google.com/rss/search?q=site%3Atheblock.co%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen"
    ),
    "https://blockworks.co/feed/": (
        "https://news.google.com/rss/search?q=site%3Ablockworks.co%20when%3A30d&hl=en-US&gl=US&ceid=US%3Aen"
    ),
    "https://cryptoslate.com/feed/": (
        "https://news.google.com/rss/search?q=site%3Acryptoslate.com%20when%3A7d&hl=en-US&gl=US&ceid=US%3Aen"
    ),
}


class RSSFetchError(Exception):
    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class RSSFetchResult:
    body: bytes
    content_type: str
    cache_status: str
    used_fallback: bool = False


@dataclass(frozen=True)
class _CacheEntry:
    body: bytes
    content_type: str
    fetched_at: float
    used_fallback: bool


_cache: dict[str, _CacheEntry] = {}
_cache_lock = threading.Lock()


def _validated_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise RSSFetchError("Invalid feed URL.", 400) from exc

    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host or port not in {None, 80, 443}:
        raise RSSFetchError("Only approved HTTP(S) feed URLs are supported.", 400)
    if host not in ALLOWED_RSS_HOSTS:
        raise RSSFetchError("This feed host is not approved.", 400)
    return url


def _looks_like_feed(body: bytes) -> bool:
    sample = body[:256 * 1024].lower()
    return any(marker in sample for marker in (b"<rss", b"<feed", b"<item", b"<entry"))


def _chainlink_blog_html_to_rss(body: bytes) -> bytes:
    """Convert the new Chainlink Webflow blog cards into the legacy RSS shape."""
    page = body.decode("utf-8", errors="replace")
    card_pattern = re.compile(
        r'<a\b(?=[^>]*\bhref="(/blog/[^"?#]+)")(?=[^>]*\bclass="[^"]*media-card[^"]*")[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    title_pattern = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)

    articles: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in card_pattern.finditer(page):
        path = html.unescape(match.group(1))
        title_match = title_pattern.search(match.group(2))
        if not title_match or path in seen:
            continue
        title_html = re.sub(r"<[^>]+>", " ", title_match.group(1))
        title = html.unescape(re.sub(r"\s+", " ", title_html)).strip()
        if not title:
            continue
        seen.add(path)
        articles.append((title, urljoin("https://chain.link/blog", path)))
        if len(articles) >= 30:
            break

    if not articles:
        raise RSSFetchError("Chainlink blog page contained no readable article cards.")

    root = ElementTree.Element("rss", {"version": "2.0"})
    channel = ElementTree.SubElement(root, "channel")
    ElementTree.SubElement(channel, "title").text = "Chainlink Blog"
    ElementTree.SubElement(channel, "link").text = "https://chain.link/blog"
    ElementTree.SubElement(channel, "description").text = "Latest official Chainlink blog articles"
    for title, link in articles:
        item = ElementTree.SubElement(channel, "item")
        ElementTree.SubElement(item, "title").text = title
        ElementTree.SubElement(item, "link").text = link
        ElementTree.SubElement(item, "guid").text = link
        ElementTree.SubElement(item, "description").text = title
    return ElementTree.tostring(root, encoding="utf-8", xml_declaration=True)


def _read_bounded(response: requests.Response) -> bytes:
    body = bytearray()
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > MAX_FEED_BYTES:
            raise RSSFetchError("Feed is larger than the 5 MB safety limit.")
    return bytes(body)


def _download_once(url: str) -> tuple[bytes, str]:
    current_url = _validated_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        response = requests.get(
            current_url,
            timeout=(4, 10),
            headers=REQUEST_HEADERS,
            allow_redirects=False,
            stream=True,
        )
        try:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location")
                if not location:
                    raise RSSFetchError("Feed returned an invalid redirect.")
                current_url = _validated_url(urljoin(current_url, location))
                continue

            response.raise_for_status()
            body = _read_bounded(response)
            if not _looks_like_feed(body):
                parsed = urlparse(current_url)
                if parsed.hostname == "chain.link" and parsed.path.rstrip("/") == "/blog":
                    body = _chainlink_blog_html_to_rss(body)
                else:
                    raise RSSFetchError("Publisher returned a web page instead of an RSS feed.")
            content_type = response.headers.get("Content-Type", "application/xml")
            if body.startswith(b"<?xml"):
                content_type = "application/rss+xml; charset=utf-8"
            return body, content_type
        finally:
            response.close()

    raise RSSFetchError("Feed redirected too many times.")


def _download_with_retry(url: str) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return _download_once(url)
        except requests.HTTPError as exc:
            last_error = exc
            status = exc.response.status_code if exc.response is not None else 0
            if status and status not in {408, 425, 429} and status < 500:
                break
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = exc
        except RSSFetchError:
            raise

        if attempt == 0:
            time.sleep(0.15)

    if isinstance(last_error, requests.HTTPError) and last_error.response is not None:
        raise RSSFetchError(f"Publisher rejected the feed request (HTTP {last_error.response.status_code}).")
    raise RSSFetchError("Publisher could not be reached in time.") from last_error


def fetch_rss_feed(raw_url: str) -> RSSFetchResult:
    """Fetch an approved feed, falling back and serving last-good data if needed."""
    url = _validated_url(raw_url)
    now = time.monotonic()

    with _cache_lock:
        cached = _cache.get(url)
    if cached and now - cached.fetched_at <= FRESH_CACHE_SECONDS:
        return RSSFetchResult(cached.body, cached.content_type, "hit", cached.used_fallback)

    candidates = (url, FEED_FALLBACKS[url]) if url in FEED_FALLBACKS else (url,)
    errors: list[str] = []
    for index, candidate in enumerate(candidates):
        try:
            body, content_type = _download_with_retry(candidate)
            entry = _CacheEntry(body, content_type, time.monotonic(), index > 0)
            with _cache_lock:
                _cache[url] = entry
            return RSSFetchResult(body, content_type, "miss", index > 0)
        except (RSSFetchError, requests.RequestException) as exc:
            errors.append(str(exc))

    if cached and now - cached.fetched_at <= STALE_CACHE_SECONDS:
        return RSSFetchResult(cached.body, cached.content_type, "stale", cached.used_fallback)

    reason = errors[-1] if errors else "Unknown publisher error."
    raise RSSFetchError(f"RSS fetch failed: {reason}")


def _clear_rss_cache_for_tests() -> None:
    with _cache_lock:
        _cache.clear()
