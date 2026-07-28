"""Publishing: Telegram channel posts + X (Twitter) OAuth-1.0a posts."""
import base64
import hashlib
import hmac
import html
import random
import re
import string
import time
import urllib.parse

import requests
from config import (PUBLISHING_ENABLED, TELEGRAM_TOKEN, TELEGRAM_CHANNEL, TELEGRAM_PROXY,
                    X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC,
                    brand_tag_for, prepend_brand_tag)

# TEMPORARY session-capture instrumentation (see backend/session_log.py).
from session_log import log as _sess_log


def _telegram_result(response, action):
    """Return Telegram's reply or preserve its human-readable rejection reason."""
    try:
        result = response.json()
    except ValueError:
        response.raise_for_status()
        raise ValueError(f'Telegram {action} returned an invalid response')
    if not response.ok or not result.get('ok'):
        raise ValueError(result.get('description', f'Telegram {action} failed'))
    return result


def _x_result(response, action):
    """Return X's JSON reply or raise its most useful API error message."""
    try:
        result = response.json()
    except ValueError:
        response.raise_for_status()
        raise ValueError(f'X {action} returned an invalid response')
    if not response.ok:
        detail = result.get('detail') or result.get('title')
        if not detail and result.get('errors'):
            first = result['errors'][0]
            detail = first.get('message') or first.get('detail') or str(first)
        raise ValueError(detail or f'X {action} failed with status {response.status_code}')
    return result


def _raw_image_b64(value):
    """Accept either raw base64 or a browser data URL."""
    if not value:
        return ''
    return value.split(',', 1)[1] if value.startswith('data:') and ',' in value else value


_PERSIAN_TEXT_RE = re.compile(r'[\u0600-\u06ff]')
_RTL_ISOLATE = '\u2067'
_POP_ISOLATE = '\u2069'
_PERSIAN_BRAND_HASHTAGS = {
    'mgccoin': '#متا_گیمز_کوین',
    'rankingplatform': '#رنکینگ_گیم',
    'oasiscoin': '#آر_زد_اوسیس',
    'jewelrycoin': '#جولری_توکن',
}


def _contains_persian(value):
    return bool(_PERSIAN_TEXT_RE.search(value or ''))


def _prepend_brand_tag_for_language(hashtags, media, is_persian):
    if not is_persian:
        return prepend_brand_tag(hashtags, media)
    media_key = re.sub(r'\s+', '', str(media or '')).lower()
    brand_tag = _PERSIAN_BRAND_HASHTAGS.get(media_key)
    if not brand_tag:
        return prepend_brand_tag(hashtags, media)
    english_tag = brand_tag_for(media)
    aliases = {
        re.sub(r'[#_\s]+', '', str(tag)).casefold()
        for tag in (brand_tag, english_tag) if tag
    }
    others = [
        tag for tag in (hashtags or [])
        if re.sub(r'[#_\s]+', '', str(tag)).casefold() not in aliases
    ]
    return [brand_tag] + others


def _rtl_isolate_paragraphs(value):
    """Keep Persian paragraphs RTL even when emoji/Markdown/numbers come first."""
    lines = (value or '').split('\n')
    return '\n'.join(
        f'{_RTL_ISOLATE}{line}{_POP_ISOLATE}' if _contains_persian(line) else line
        for line in lines
    )


def _strip_markdown_markers(value):
    """Posts are plain prose: never send Markdown asterisks to social platforms."""
    return re.sub(r'\*+', '', str(value or '')).strip()


def handle_telegram_post(body):
    if not PUBLISHING_ENABLED:
        raise ValueError('RZWire publishing is disabled for local review')
    if not TELEGRAM_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN not set in .env')
    image_b64 = _raw_image_b64(body.get('imageB64', ''))
    headline  = body.get('headline', '')
    copy_text = _strip_markdown_markers(body.get('copy', ''))
    hashtags  = body.get('hashtags', [])
    link      = body.get('link', '')
    media     = body.get('mediaBrand', '')
    tg_base   = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}'
    tg_proxies = {'https': TELEGRAM_PROXY} if TELEGRAM_PROXY else None

    is_persian = _contains_persian(headline) or _contains_persian(copy_text)
    # Guarantee the language-appropriate brand identity hashtag is first.
    hashtags = _prepend_brand_tag_for_language(hashtags, media, is_persian)
    hashtag_line = ' '.join(hashtags)
    if hashtag_line:
        # The AI-generated copy often already ends with its own hashtags (e.g. folded into a
        # "Source: ... · #Tag1 #Tag2" line) — strip a trailing run so they aren't duplicated.
        copy_text = re.sub(r'\s*[·\-—|:]?\s*(?:#\w+\s*)+$', '', copy_text)
    source_label = 'مشاهده خبر کامل' if is_persian else 'Read full story'
    source_line = (
        f'\n\n<a href="{html.escape(link, quote=True)}">{source_label}</a>'
        if link and link != '#' else ''
    )

    if image_b64:
        img_bytes = base64.b64decode(image_b64)
        safe_headline = html.escape(_rtl_isolate_paragraphs(headline) if is_persian else headline)
        # Build suffix (hashtags + link) — always kept intact
        safe_hashtags = _rtl_isolate_paragraphs(hashtag_line) if is_persian else hashtag_line
        suffix_parts = [p for p in [html.escape(safe_hashtags), source_line.strip()] if p]
        suffix = '\n\n'.join(suffix_parts)
        head = f'<b>{safe_headline}</b>' if safe_headline else ''
        # How much room is left for the body copy?
        # Format: head + \n\n + copy + \n\n + suffix  (omit empty parts)
        overhead = len(head) + (2 if head else 0) + (2 + len(suffix) if suffix else 0)
        available = 1024 - overhead
        body = copy_text[:available].rstrip() if len(copy_text) > available else copy_text
        if body and len(copy_text) > available:
            body = body[:body.rfind(' ')] + '…' if ' ' in body else body + '…'
        safe_body = _rtl_isolate_paragraphs(body) if is_persian else body
        parts = [p for p in [head, html.escape(safe_body), suffix] if p]
        caption = '\n\n'.join(parts)
        # TEMPORARY: capture the exact text shipped to Telegram (with image).
        try:
            _sess_log('publish_telegram', 'post_final',
                      mediaBrand=media, has_image=True, headline=headline,
                      published_text=caption, hashtags=hashtags, link=link)
        except Exception:
            pass
        r = requests.post(f'{tg_base}/sendPhoto',
                          data={'chat_id': TELEGRAM_CHANNEL, 'caption': caption,
                                'parse_mode': 'HTML'},
                          files={'photo': ('image.png', img_bytes, 'image/png')},
                          # Telegram accepts the upload before its response is returned.
                          # Keep the upstream wait comfortably below the gateway timeout.
                          proxies=tg_proxies, timeout=(15, 150))
        return _telegram_result(r, 'sendPhoto')
    else:
        safe_headline = html.escape(_rtl_isolate_paragraphs(headline) if is_persian else headline)
        safe_copy = _rtl_isolate_paragraphs(copy_text) if is_persian else copy_text
        safe_hashtags = _rtl_isolate_paragraphs(hashtag_line) if is_persian else hashtag_line
        message_parts = [html.escape(safe_copy), html.escape(safe_hashtags), source_line.strip()]
        message_body = '\n\n'.join(part for part in message_parts if part)
        message = f'<b>{safe_headline}</b>\n\n{message_body}' if safe_headline else message_body
        # TEMPORARY: capture the exact text shipped to Telegram (text-only).
        try:
            _sess_log('publish_telegram', 'post_final',
                      mediaBrand=media, has_image=False, headline=headline,
                      published_text=message, hashtags=hashtags, link=link)
        except Exception:
            pass
        r = requests.post(f'{tg_base}/sendMessage',
                          data={'chat_id': TELEGRAM_CHANNEL, 'text': message,
                                'parse_mode': 'HTML',
                                'disable_web_page_preview': 'false'},
                          proxies=tg_proxies, timeout=30)
        return _telegram_result(r, 'sendMessage')


# ── X (Twitter) OAuth 1.0a ─────────────────────────────────────────────────────
def _oauth_header(method, url, extra_params, consumer_key, consumer_secret, token, token_secret):
    nonce     = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    timestamp = str(int(time.time()))
    oauth = {
        'oauth_consumer_key':     consumer_key,
        'oauth_nonce':            nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp':        timestamp,
        'oauth_token':            token,
        'oauth_version':          '1.0',
    }
    all_params = {**extra_params, **oauth}
    enc = lambda s: urllib.parse.quote(str(s), safe='')
    param_str = '&'.join(f'{enc(k)}={enc(v)}' for k, v in sorted(all_params.items()))
    base = '&'.join([method.upper(), enc(url), enc(param_str)])
    key  = f'{enc(consumer_secret)}&{enc(token_secret)}'
    sig  = base64.b64encode(hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    oauth['oauth_signature'] = sig
    return 'OAuth ' + ', '.join(f'{enc(k)}="{enc(v)}"' for k, v in sorted(oauth.items()))


def handle_twitter_post(body):
    if not PUBLISHING_ENABLED:
        raise ValueError('RZWire publishing is disabled for local review')
    if not all([X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC]):
        raise ValueError('X API credentials not fully configured in .env')
    if X_TOKEN.startswith('PASTE_') or X_TOKEN_SEC.startswith('PASTE_'):
        raise ValueError('X Access Token not yet set — paste real values in .env')

    image_b64 = _raw_image_b64(body.get('imageB64', ''))
    copy_text = _strip_markdown_markers(body.get('copy', ''))
    hashtags  = body.get('hashtags', [])
    media     = body.get('mediaBrand', '')

    is_persian = _contains_persian(copy_text) or any(
        _contains_persian(str(tag)) for tag in (hashtags or [])
    )
    # Guarantee the language-appropriate brand identity hashtag is first.
    hashtags = _prepend_brand_tag_for_language(hashtags, media, is_persian)
    hashtag_str = ' '.join(hashtags) if isinstance(hashtags, list) else str(hashtags)
    tweet_text = f'{copy_text}\n\n{hashtag_str}'.strip()
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + '…'

    media_id = None
    if image_b64:
        upload_url = 'https://upload.twitter.com/1.1/media/upload.json'
        auth = _oauth_header('POST', upload_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
        # multipart keeps the large base64 out of the OAuth signature base string
        ur = requests.post(upload_url,
                           files=[('media_data', (None, image_b64))],
                           headers={'Authorization': auth}, timeout=90)
        upload_data = _x_result(ur, 'media upload')
        media_id = upload_data.get('media_id_string')
        if not media_id:
            raise ValueError('X media upload succeeded without a media ID')

    tweet_url = 'https://api.twitter.com/2/tweets'
    auth = _oauth_header('POST', tweet_url, {}, X_API_KEY, X_API_SECRET, X_TOKEN, X_TOKEN_SEC)
    # TEMPORARY: capture the exact tweet text shipped to X (after brand-tag prepend + 280 trim).
    try:
        _sess_log('publish_x', 'post_final',
                  mediaBrand=media, has_image=bool(image_b64),
                  published_text=tweet_text, hashtags=hashtags,
                  char_count=len(tweet_text), truncated=len(tweet_text) >= 280)
    except Exception:
        pass
    tweet_body = {'text': tweet_text}
    if media_id:
        tweet_body['media'] = {'media_ids': [media_id]}
    tr = requests.post(tweet_url, json=tweet_body,
                       headers={'Authorization': auth, 'Content-Type': 'application/json'},
                       timeout=30)
    data = _x_result(tr, 'post')
    tweet_id = data.get('data', {}).get('id', '')
    if not tweet_id:
        raise ValueError('X accepted the request but did not return a post ID')
    return {'success': True, 'tweetId': tweet_id, 'mediaId': media_id}
