"""Safe FAQ and repeated-answer cache for the RZWire chatbot."""
import hashlib
import re

import chat_storage


_PERSIAN_RE = re.compile(r'[\u0600-\u06ff]')
_DYNAMIC_RE = re.compile(
    r"\b(?:latest|today|right now|currently|current price|live price|recent|"
    r"how many|show my|list my|what are my|my current|status of my|this card|"
    r"this article|this story|above|previous answer)\b|"
    r"(?:امروز|الان|لحظه.?ای|جدیدترین|اخیر|کارت فعلی|این کارت|این مقاله|پاسخ قبلی|"
    r"وضعیت من|لیست من|چند تا)",
    re.IGNORECASE,
)
_FOLLOW_UP_RE = re.compile(
    r"^(?:why|how|tell me more|explain more|continue|go on|what about it|"
    r"what about this|what about them|yes|no|چرا|چطور|بیشتر توضیح بده|ادامه بده)[?.!\s]*$",
    re.IGNORECASE,
)


def language_for(message):
    return 'fa' if _PERSIAN_RE.search(message or '') else 'en'


def context_key(context, selected_media):
    active_brand = (context or {}).get('brand') or ''
    if active_brand:
        return f'brand:{active_brand}'
    selected = sorted(set(selected_media or []))
    if len(selected) == 1:
        return f'brand:{selected[0]}'
    if selected:
        return 'media:' + '|'.join(selected)
    return 'general'


def _context_brand(key):
    return key[6:] if key.startswith('brand:') else ''


def cacheable_question(message, context=None):
    context = context or {}
    normalized = chat_storage.normalize_question(message)
    if not normalized or len(normalized) < 6 or len(normalized) > 400:
        return False
    if context.get('headline') or context.get('copy'):
        return False
    if _DYNAMIC_RE.search(message or '') or _FOLLOW_UP_RE.search(message or ''):
        return False
    return True


def _cache_key(normalized, key, language):
    raw = f'{language}|{key}|{normalized}'.encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


def lookup(message, context, selected_media, knowledge_version, interpreted_message=None):
    """Return approved FAQ answers only.

    Legacy generated-answer rows remain in SQLite for audit, but are never read
    by the local-RAG chatbot.
    """
    match_message = interpreted_message or message
    normalized = chat_storage.normalize_question(match_message)
    language = language_for(message)
    key = context_key(context, selected_media)
    faq = chat_storage.find_faq(normalized, language, _context_brand(key))
    if faq:
        return {
            'answer': faq['answer'],
            'source': 'faq',
            'normalized': normalized,
            'contextKey': key,
            'language': language,
            'faqId': faq['id'],
        }
    return None


def store_ai_answer(message, context, selected_media, answer, knowledge_version,
                    interpreted_message=None):
    if not cacheable_question(interpreted_message or message, context):
        return False
    normalized = chat_storage.normalize_question(interpreted_message or message)
    language = language_for(message)
    key = context_key(context, selected_media)
    chat_storage.save_cached_answer(
        _cache_key(normalized, key, language), normalized, key, language,
        answer, knowledge_version,
    )
    return True


def record(message, context, selected_media, source, interpreted_message=None):
    normalized = chat_storage.normalize_question(interpreted_message or message)
    if not normalized:
        return
    chat_storage.record_question(
        normalized, message, context_key(context, selected_media),
        language_for(message), source,
    )
