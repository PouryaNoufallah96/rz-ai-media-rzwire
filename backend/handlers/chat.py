"""Local, extractive RAG chatbot for RZWire."""

import re
import sys
import time

import chat_cache
import chat_index
import chat_knowledge
import chat_normalizer
import chat_policy
import chat_storage
import database
from config import MEDIA_LIST


MAX_CHAT_MESSAGE_CHARS = 2000
PROMPT_HISTORY_MESSAGES = 8
PROMPT_HISTORY_CHARS = 6000
PROMPT_MESSAGE_CHARS = 3000

_PERSIAN_RE = re.compile(r'[\u0600-\u06ff]')


def _selected_media(context):
    raw = context.get('selectedMedia') if isinstance(context, dict) else []
    if not isinstance(raw, list):
        return []
    return list(dict.fromkeys(brand for brand in raw if brand in MEDIA_LIST))


def _context_text(context, key, limit):
    value = context.get(key)
    return value.strip()[:limit] if isinstance(value, str) else ''


def _sanitized_context(raw_context):
    context = raw_context if isinstance(raw_context, dict) else {}
    brand = _context_text(context, 'brand', 80)
    return {
        'selectedMedia': context.get('selectedMedia', []),
        'brand': brand if brand in MEDIA_LIST else '',
        'platform': _context_text(context, 'platform', 40),
        'headline': _context_text(context, 'headline', 300),
        'copy': _context_text(context, 'copy', 600),
    }


def _prompt_history(history):
    """Compatibility helper that keeps a bounded, complete history window."""
    selected = []
    used_chars = 0
    for item in reversed(history[-PROMPT_HISTORY_MESSAGES:]):
        role = item.get('role')
        content = item.get('content')
        if role not in ('user', 'assistant') or not isinstance(content, str):
            continue
        content = content[:PROMPT_MESSAGE_CHARS]
        if selected and used_chars + len(content) > PROMPT_HISTORY_CHARS:
            break
        selected.append({'role': role, 'content': content})
        used_chars += len(content)
    selected.reverse()
    while selected and selected[0]['role'] == 'assistant':
        selected.pop(0)
    return selected


def _source(chunk):
    return {
        'id': chunk['id'],
        'title': chunk['title'],
        'brand': chunk.get('brand', ''),
        'section': chunk.get('section', chunk['title']),
    }


def _response(reply, expires_at, answer_source, confidence, sources=None,
              suggestions=None, policy='allow', interpreted_as=None):
    return {
        'reply': reply,
        'expiresAt': expires_at,
        'tokenUsed': False,
        'policy': policy,
        'answerSource': answer_source,
        'confidence': confidence,
        'sources': sources or [],
        'suggestions': suggestions or [],
        'knowledgeVersion': chat_knowledge.knowledge_version(),
        'interpretedAs': interpreted_as,
    }


def _persist_turn(user_id, message, reply, metadata):
    return database.add_chat_turn(
        user_id,
        message,
        reply,
        assistant_metadata={
            'answerSource': metadata['answerSource'],
            'confidence': metadata['confidence'],
            'sources': metadata['sources'],
            'suggestions': metadata['suggestions'],
            'tokenUsed': False,
            'knowledgeVersion': metadata['knowledgeVersion'],
        },
    )['expiresAt']


def _finish(user_id, message, reply, answer_source, confidence, context,
            selected_media, sources=None, suggestions=None, policy='allow',
            interpreted_as=None):
    payload = _response(
        reply, None, answer_source, confidence, sources, suggestions, policy,
        interpreted_as,
    )
    payload['expiresAt'] = _persist_turn(user_id, message, reply, payload)
    chat_cache.record(message, context, selected_media, answer_source, interpreted_as)
    return payload


def _is_persian(message):
    return bool(_PERSIAN_RE.search(message or ''))


def _clean_passage(content, limit=1400):
    lines = []
    for line in (content or '').splitlines():
        cleaned = re.sub(r'^\s*#{1,6}\s*', '', line).strip()
        if cleaned:
            lines.append(cleaned)
    text = '\n\n'.join(lines)
    if len(text) <= limit:
        return text
    shortened = text[:limit].rsplit(' ', 1)[0].rstrip(' ,;:-')
    return shortened + '…'


def _suggestions(hits, language):
    suggestions = []
    seen = set()
    for hit in hits:
        section = (hit.get('section') or hit.get('title') or '').strip()
        key = section.casefold()
        if not section or key in seen:
            continue
        seen.add(key)
        if language == 'fa':
            suggestions.append(f'درباره «{section}» بیشتر توضیح بده.')
        else:
            suggestions.append(f'Tell me more about {section}.')
        if len(suggestions) == 3:
            break
    return suggestions


def _active_context_answer(question, context, selected_media, language):
    lowered = question.casefold()
    card_reference = any(term in lowered for term in (
        'this card', 'current card', 'open card', 'this article', 'this story',
        'current headline', 'current copy', 'current platform', 'current brand',
        'این کارت', 'کارت فعلی', 'کارت باز', 'این خبر', 'این مطلب',
        'تیتر فعلی', 'متن فعلی', 'پلتفرم فعلی', 'برند فعلی',
    ))
    selected_reference = any(term in lowered for term in (
        'selected media', 'selected brand', 'which media', 'which brand',
        'رسانه انتخاب', 'برند انتخاب', 'کدام رسانه', 'کدام برند',
    ))
    if selected_reference and selected_media:
        joined = '، '.join(selected_media) if language == 'fa' else ', '.join(selected_media)
        reply = (
            f'رسانه‌های انتخاب‌شده: {joined}.'
            if language == 'fa'
            else f'Selected media: {joined}.'
        )
        return reply
    if not card_reference:
        return None

    brand = context.get('brand')
    platform = context.get('platform')
    headline = context.get('headline')
    copy = context.get('copy')
    if not any((brand, platform, headline, copy)):
        return (
            'در حال حاضر کارت بازی برای توضیح وجود ندارد.'
            if language == 'fa'
            else 'There is no open card in the current workspace context.'
        )

    if language == 'fa':
        rows = ['اطلاعات کارت فعلی:']
        if brand:
            rows.append(f'- برند: {brand}')
        if platform:
            rows.append(f'- پلتفرم: {platform}')
        if headline:
            rows.append(f'- تیتر: {headline}')
        if copy:
            rows.append(f'- متن فعلی: {copy}')
    else:
        rows = ['Current card information:']
        if brand:
            rows.append(f'- Brand: {brand}')
        if platform:
            rows.append(f'- Platform: {platform}')
        if headline:
            rows.append(f'- Headline: {headline}')
        if copy:
            rows.append(f'- Current copy: {copy}')
    return '\n'.join(rows)


def handle_chat_history(user_id):
    return database.get_chat_state(user_id, limit=15)


def handle_chat(user_id, body):
    if not isinstance(body, dict):
        raise ValueError('Invalid chat request')
    raw_message = body.get('message')
    if raw_message is not None and not isinstance(raw_message, str):
        raise ValueError('Message must be text')
    message = (raw_message or '').strip()
    if not message:
        raise ValueError('Message is required')
    if len(message) > MAX_CHAT_MESSAGE_CHARS:
        raise ValueError(f'Message must be {MAX_CHAT_MESSAGE_CHARS} characters or fewer')

    context = _sanitized_context(body.get('context'))
    selected_media = _selected_media(context)
    understanding = chat_normalizer.understand(message)
    interpreted_message = understanding['interpreted'] or message
    language = understanding.get('language') or ('fa' if _is_persian(message) else 'en')
    interpreted_as = interpreted_message if understanding['corrections'] else None
    chat_storage.record_corrections(understanding['corrections'], language)

    history = database.get_chat_state(user_id, limit=15)['messages']
    policy = chat_policy.classify(
        interpreted_message,
        history=history,
        selected_media=selected_media,
        has_active_card=bool(context.get('headline') or context.get('copy')),
        reply_message=message,
    )
    if policy['kind'] != 'allow':
        return _finish(
            user_id, message, policy['reply'], 'policy', 'high', context,
            selected_media, policy=policy['kind'], interpreted_as=interpreted_as,
        )

    stored = chat_cache.lookup(
        message, context, selected_media, chat_knowledge.knowledge_version(),
        interpreted_message,
    )
    if stored:
        faq_source = {
            'id': f"faq-{stored['faqId']}",
            'title': 'Approved FAQ',
            'brand': context.get('brand', ''),
            'section': 'FAQ',
        }
        suggestions = (
            ['چطور یک پست را زمان‌بندی کنم؟', 'Analyze چگونه کار می‌کند؟']
            if language == 'fa'
            else ['How do I schedule a post?', 'How does Analyze work?']
        )
        return _finish(
            user_id, message, stored['answer'], 'faq', 'high', context,
            selected_media, [faq_source], suggestions,
            interpreted_as=interpreted_as,
        )

    if understanding['confidence'] == 'medium':
        return _finish(
            user_id, message, chat_normalizer.clarification_reply(understanding),
            'policy', 'medium', context, selected_media, policy='clarify',
            interpreted_as=interpreted_message,
        )

    context_reply = _active_context_answer(
        interpreted_message, context, selected_media, language,
    )
    if context_reply:
        source = {
            'id': 'active-workspace-context',
            'title': 'Current workspace context',
            'brand': context.get('brand', ''),
            'section': 'Open card',
        }
        return _finish(
            user_id, message, context_reply, 'context', 'high', context,
            selected_media, [source], interpreted_as=interpreted_as,
        )

    active_brand = context.get('brand') if context.get('brand') in MEDIA_LIST else None
    brand_hint = active_brand or (selected_media[0] if len(selected_media) == 1 else None)
    hits = chat_index.retrieve(interpreted_message, k=4, brand_hint=brand_hint)
    if not hits:
        reply = (
            'پاسخ مستندی برای این پرسش در دانش RZWire پیدا نکردم.'
            if language == 'fa'
            else 'I could not find a documented answer in the RZWire knowledge base.'
        )
        return _finish(
            user_id, message, reply, 'closest_passage', 'low', context,
            selected_media, interpreted_as=interpreted_as,
        )

    best = hits[0]
    confidence = chat_index.confidence_for(best['score'])
    passage = _clean_passage(best['content'])
    if confidence == 'low':
        warning = (
            'ممکن است پاسخ دقیق نباشد؛ این نزدیک‌ترین اطلاعات در پایگاه دانش RZWire است:'
            if language == 'fa'
            else (
                'I may not have an exact answer, but this is the closest information '
                'in the RZWire knowledge base:'
            )
        )
        reply = f'{warning}\n\n{passage}'
        answer_source = 'closest_passage'
    else:
        reply = passage
        answer_source = 'knowledge'

    sources = [_source(hit) for hit in hits[:3]]
    suggestions = _suggestions(hits[1:], language)
    return _finish(
        user_id, message, reply, answer_source, confidence, context,
        selected_media, sources, suggestions, interpreted_as=interpreted_as,
    )


def chat_health_status():
    return chat_index.status(check_service=True)


def start_chat_indexer():
    chat_index.start_background_sync()


def run_chat_cleanup_loop(interval_seconds=60):
    # The existing production server already starts this loop after database
    # initialization, making it a safe compatibility hook for the local index.
    chat_index.start_background_sync()
    while True:
        try:
            database.clear_expired_chats()
        except Exception as exc:  # noqa: BLE001
            print(f'[chat cleanup] {exc}', file=sys.stderr)
        time.sleep(interval_seconds)
