"""Social-copy generation: platform prompts, length enforcement, variants."""
import re
import sys

from config import (PLAT_RULES, EDITORIAL_MODELS, BRAND_PROMO_PITCH,
                    _EMOJI_RE, _EMOJI_CAP, clean_emojis, smart_truncate, _sibling_block,
                    brand_tag_for, prepend_brand_tag, strip_hashtags_from_copy)
from llm import openrouter_chat
from _branddoc import _brand_doc

# TEMPORARY session-capture instrumentation (see backend/session_log.py).
from session_log import log as _sess_log


_PERSIAN_HASHTAG_MODEL = 'google/gemini-2.5-flash-lite'
_PERSIAN_CHAR_RE = re.compile(r'[\u0600-\u06ff]')
_LATIN_CHAR_RE = re.compile(r'[A-Za-z]')
_PERSIAN_BRAND_HASHTAGS = {
    'mgccoin': '#متا_گیمز_کوین',
    'rankingplatform': '#رنکینگ_گیم',
    'oasiscoin': '#آر_زد_اوسیس',
    'jewelrycoin': '#جولری_توکن',
}


# A few models occasionally put their hidden planning notes into the public
# `copy` field. Treat that as a failed generation, never as a publishable post.
_COPY_ARTIFACT_RE = re.compile(
    r'(?:\blength\s*calculation\s*:|\bcharacter\s*count\s*:|\btoken\s*count\s*:|'
    r'\bheadline\s*:\s*\d{1,5}\b|^\s*(?:analysis|reasoning|scratchpad)\s*:)',
    re.IGNORECASE,
)
_EMPTY_JSON_ARRAY_RE = re.compile(r'\[\s*(?:(?:""|\'\')\s*,\s*)+(?:""|\'\')\s*\]')


def _plain_social_copy(value):
    """Return reader-facing plain text, never Markdown emphasis markers.

    Telegram and X display asterisks literally, so a model response such as
    ``**Important update**`` must become ``Important update`` before it reaches
    the editor, a saved card, or a publishing endpoint.  Remove every asterisk
    rather than only valid paired Markdown; this also covers malformed output.
    """
    return re.sub(r'\*+', '', str(value or '')).strip()


def _is_usable_copy(value):
    """Reject model scratch work and malformed structured-output residue."""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False

    # Remove Markdown emphasis before inspecting so `*Length calculation:*`
    # cannot bypass the guard.
    inspection = re.sub(r'[`*_]+', '', text)
    if _COPY_ARTIFACT_RE.search(inspection) or _EMPTY_JSON_ARRAY_RE.search(inspection):
        return False

    # A post needs actual reader-facing words. This still supports Persian and
    # other Unicode scripts through Python's Unicode-aware \w matching.
    return len(re.findall(r'\w+', inspection, flags=re.UNICODE)) >= 3


def _validate_copy_result(result):
    """Normalize a model result only after confirming its copy is publishable."""
    if not isinstance(result, dict):
        raise ValueError('Model response was not a copy object')

    copy = _plain_social_copy(result.get('copy', ''))
    if not _is_usable_copy(copy):
        raise ValueError('Model returned planning notes or unusable copy')

    hashtags = result.get('hashtags', [])
    if isinstance(hashtags, str):
        hashtags = [hashtags]
    if not isinstance(hashtags, list):
        hashtags = []
    hashtags = [str(tag).strip() for tag in hashtags if str(tag).strip()]
    return {'copy': copy, 'hashtags': hashtags}


def _fallback_copy(article, platform):
    """Last-resort clean copy when every model attempt is malformed."""
    title = re.sub(r'\s+', ' ', str(article.get('title', '') or '')).strip()
    description = re.sub(r'\s+', ' ', str(article.get('desc', '') or '')).strip()
    if not _is_usable_copy(title):
        title = ''
    if not _is_usable_copy(description):
        description = ''

    if platform == 'X':
        text = '. '.join(part.rstrip('. ') for part in (title, description) if part)
        return smart_truncate(text or 'Market update in focus.', 240)

    parts = [part for part in (title, description) if part]
    if not parts:
        return 'Market update in focus. Follow for the next confirmed development.'
    if platform == 'Instagram':
        parts.append('Follow for the next update.')
    return '\n\n'.join(parts)


def _media_key(media):
    return re.sub(r'\s+', '', str(media or '')).lower()


def _hashtag_key(value):
    return re.sub(r'[#_\s]+', '', str(value or '')).casefold()


def _normalize_persian_hashtag(value):
    body = str(value or '').strip().lstrip('#').strip()
    body = re.sub(r'[\s\u200c-]+', '_', body)
    body = re.sub(r'[^\w\u0600-\u06ff]', '', body, flags=re.UNICODE)
    body = re.sub(r'_+', '_', body).strip('_')
    return f'#{body}' if body else ''


def _persianize_variant_hashtags(variants, media):
    """Translate all topic tags in one fast call and force a Persian brand tag first."""
    persian_brand = _PERSIAN_BRAND_HASHTAGS.get(_media_key(media))
    english_brand = brand_tag_for(media)
    brand_keys = {_hashtag_key(tag) for tag in (persian_brand, english_brand) if tag}

    unique_topics = []
    seen_topics = set()
    for variant in variants:
        for raw_tag in variant.get('hashtags') or []:
            raw_tag = str(raw_tag or '').strip()
            key = _hashtag_key(raw_tag)
            if not raw_tag or key in brand_keys or key in seen_topics:
                continue
            seen_topics.add(key)
            unique_topics.append(raw_tag)

    localized = {}
    needs_translation = []
    for tag in unique_topics:
        normalized = _normalize_persian_hashtag(tag)
        if normalized and _PERSIAN_CHAR_RE.search(normalized) and not _LATIN_CHAR_RE.search(normalized):
            localized[_hashtag_key(tag)] = normalized
        else:
            needs_translation.append(tag)

    if needs_translation:
        entries = [{'index': index, 'hashtag': tag} for index, tag in enumerate(needs_translation)]
        system = (
            'Convert every hashtag into one natural Persian-script hashtag. Translate concepts and '
            'phonetically transliterate names, brands, projects, and tickers. Use an underscore between '
            'words. Every result must start with #, contain Persian letters, and contain no Latin A-Z '
            'characters. Return ONLY JSON: {"items":[{"index":0,"hashtag":"#..."}]}.'
        )
        translated_items = []
        for _attempt in range(2):
            try:
                result = openrouter_chat(
                    _PERSIAN_HASHTAG_MODEL,
                    [{'role': 'system', 'content': system},
                     {'role': 'user', 'content': str(entries)}],
                    temperature=0,
                    max_tokens=1200,
                )
                translated_items = result.get('items', []) if isinstance(result, dict) else []
                if translated_items:
                    break
            except Exception:
                translated_items = []

        by_index = {
            item.get('index'): item.get('hashtag', '')
            for item in translated_items if isinstance(item, dict)
        }
        for index, original in enumerate(needs_translation):
            translated = _normalize_persian_hashtag(by_index.get(index, ''))
            if translated and _PERSIAN_CHAR_RE.search(translated) and not _LATIN_CHAR_RE.search(translated):
                localized[_hashtag_key(original)] = translated

    for variant in variants:
        final_tags = [persian_brand] if persian_brand else []
        seen_final = {_hashtag_key(tag) for tag in final_tags}
        for raw_tag in variant.get('hashtags') or []:
            key = _hashtag_key(raw_tag)
            if key in brand_keys:
                continue
            translated = localized.get(key)
            translated_key = _hashtag_key(translated)
            if translated and translated_key not in seen_final:
                final_tags.append(translated)
                seen_final.add(translated_key)
        variant['hashtags'] = final_tags


def handle_generate_copy(body):
    article      = body.get('article', {})
    platform     = body.get('platform', '')
    media        = body.get('mediaBrand', '')
    sentiment    = body.get('sentiment', 'Neutral')
    model_key    = body.get('modelKey', 'gpt')   # 'gpt' | 'gemini' | 'claude'
    language     = body.get('language', 'en')
    sibling_copy = body.get('siblingCopy') or None
    variant_count = max(1, min(3, body.get('variantCount', 2)))
    is_promo = bool(body.get('promoMode'))
    # In promo mode, load the FULL brand bible so compliance guardrails bind the copy too
    # (not just the short pitch). Falls back to the short blurb if the doc is unavailable.
    promo_pitch = _brand_doc(media) if is_promo else ''

    if not article or not platform or not media:
        raise ValueError('Missing article, platform, or mediaBrand')

    rule = PLAT_RULES.get(platform)
    if not rule:
        raise ValueError(f'Unknown platform: {platform}')

    user_msg = (
        f"Article title: {article.get('title', '')}\n"
        f"Source: {article.get('source', '')}\n"
        f"Description: {article.get('desc', '')}\n"
        f"Keywords: {', '.join(article.get('matchedKeywords', []))}"
    )

    def call(extra='', requested_model_key=None):
        sys_prompt = rule['system'](media, sentiment, sibling_copy)
        sys_prompt += (
            '\nOUTPUT FORMAT: Plain text only. Never use Markdown, asterisks (*), '
            'bold markers, headings, or bullet markers in the copy.'
        )
        if language == 'fa':
            sys_prompt += ('\nMANDATORY OUTPUT LANGUAGE: Persian (Farsi). Write every reader-facing word in fluent Persian, '
                           'including all copy, hooks, calls to action, variants, explanations, and hashtags. '
                           'Use natural RTL sentence structure, Persian punctuation, and Persian digits. Do not output '
                           'English sentences. In prose only, crypto tickers, project names, media/brand names, model '
                           'names, and URLs may remain English. HASHTAG EXCEPTION: every hashtag must use Persian script; '
                           'translate concepts and transliterate tickers, projects, and brand names. Use underscores '
                           'between words and never put Latin A-Z characters inside a hashtag.')
        if promo_pitch:
            # Replace the editorial opening line with a promotional framing; keep all format rules.
            after_first = sys_prompt.split('\n', 1)
            promo_header = (
                f'You are writing promotional {platform} content for {media}. Sentiment: {sentiment}.\n'
                f'BRAND BIBLE (authoritative — respect its positioning, voice, and "do not say" '
                f'compliance rules; never use forbidden phrases or forbidden product framings):\n'
                f'{promo_pitch}\n\n'
                'YOUR JOB: Open with a hook that fits the post idea, then present the product in a way '
                'that is credible, mechanism-led, and fully on-brand. Stay compliant — no hype, no profit '
                'promises, no risk-free language, no forbidden vocabulary. End with the brand benefit. '
                'All platform format rules below still apply.\n'
            )
            sys_prompt = promo_header + (after_first[1] if len(after_first) > 1 else '')
        if extra:
            sys_prompt += '\n' + extra
        msgs = [{'role': 'system', 'content': sys_prompt},
                {'role': 'user',   'content': user_msg}]
        cfg = EDITORIAL_MODELS.get(requested_model_key or model_key, EDITORIAL_MODELS['gpt'])
        return openrouter_chat(cfg['id'], msgs, rule['temperature'], rule['maxTokens'])

    def safe_call(extra=''):
        """Return only usable copy, with strict repair attempts before giving up."""
        repair = (
            'STRICT OUTPUT REPAIR: Return ONLY one JSON object with exactly "copy" and "hashtags". '
            'The copy must be the final reader-facing social post. Do not include reasoning, calculations, '
            'character counts, labels, Markdown, blank JSON arrays, or an explanation of your work.'
        )
        attempts = [(model_key, ''), (model_key, repair)]
        if model_key != 'gpt':
            attempts.append(('gpt', repair))
        else:
            attempts.append((model_key, repair + ' This is the final retry.'))

        last_error = None
        for attempt_model, repair_note in attempts:
            try:
                extra_note = '\n'.join(part for part in (extra, repair_note) if part)
                return _validate_copy_result(call(extra_note, attempt_model))
            except Exception as exc:  # Try the repair path before source-based fallback.
                last_error = exc
        raise ValueError(f'No usable copy after repair attempts: {last_error}')

    angles = rule.get('variant_angles')

    def _assembled_length(copy, hashtags):
        """Length of the final post the social handler will actually ship.

        Mirrors handlers/social.py: it assembles `copy + "\\n\\n" + hashtag_line`.
        We include the brand identity tag (forced to position 0 at post time) so
        the budget accounts for the exact text the platform will receive — not just
        the bare copy. This is what stops X from truncating into the hashtag block.
        """
        full_tags = prepend_brand_tag(hashtags, media)
        hashtag_line = ' '.join(full_tags)
        sep = 2 if copy and hashtag_line else 0   # the "\n\n" between copy and tags
        return len(copy) + sep + len(hashtag_line)

    def _enforce_length(copy, hashtags, extra=''):
        """Re-roll toward the platform's char-count bounds; hard-truncate over the max as a last resort.

        The bound is measured on the ASSEMBLED post text (copy + separator + the
        brand-tag-prefixed hashtag line), so what the user picks in the panel is
        guaranteed to fit the platform's hard limit (X=280, Telegram caption=1024).
        """
        lo, hi = rule.get('minChars'), rule.get('maxChars')
        if hi is None:
            return copy, hashtags
        n = _assembled_length(copy, hashtags)
        if n <= hi and (lo is None or n >= lo):
            return copy, hashtags
        if lo is not None and n < lo:
            note = (f'Your previous attempt was only {n} characters (including hashtags) — too short. '
                    f'This format requires {lo}-{hi} characters total; add more relevant detail or context '
                    f'(do not invent facts) to reach at least {lo}.')
        else:
            note = (f'Your previous attempt was {n} characters (including hashtags) — too long. '
                    f'This format requires at most {hi} characters total; tighten it without dropping '
                    f'the key facts or the hashtags.')
        try:
            result = safe_call(f'{extra}\nIMPORTANT: {note}'.strip())
        except ValueError:
            # Couldn't get a usable re-roll — keep the original draft rather than losing the variant.
            return copy, hashtags
        copy     = clean_emojis(result.get('copy', copy), platform)
        hashtags = result.get('hashtags', hashtags)
        # A re-roll can re-introduce hashtags into the body — re-enforce the
        # "copy is pure prose" contract before any length measurement.
        copy, hashtags = strip_hashtags_from_copy(copy, hashtags)
        # Last-resort fit: trim the COPY only, never the hashtag line.
        full_tags = prepend_brand_tag(hashtags, media)
        hashtag_line = ' '.join(full_tags)
        budget = hi - (2 + len(hashtag_line)) if hashtag_line else hi
        if len(copy) > budget:
            copy = smart_truncate(copy, budget)
        return copy, hashtags

    variants = []
    if angles:
        # Each angle is a distinct, intentional framing — generate exactly one variant per angle.
        for angle in angles:
            try:
                result   = safe_call(angle['instruction'])
                copy     = clean_emojis(result.get('copy', ''), platform)
                hashtags = result.get('hashtags', [])
                # Enforce the "copy is pure prose" contract BEFORE length budgeting,
                # so _enforce_length measures clean text and the array holds every tag.
                copy, hashtags = strip_hashtags_from_copy(copy, hashtags)
                copy, hashtags = _enforce_length(copy, hashtags, angle['instruction'])
            except ValueError as e:
                # Never expose model scratch work or leave the panel blank. The
                # fallback uses only the article supplied to this request.
                print(f'[copy/generate] using fallback for {platform}/{angle["label"]}: {e}', file=sys.stderr)
                copy = _fallback_copy(article, platform)
                hashtags = []
            label = angle['label']
            if language == 'fa':
                label = {
                    'Breaking': 'فوری', 'Question': 'پرسشی', 'Take': 'دیدگاه',
                    'Viral': 'پربازدید', 'Analysis': 'تحلیل', 'To the point': 'خلاصه و مستقیم',
                }.get(label, label)
            variants.append({'copy': copy, 'hashtags': hashtags, 'label': label})

    else:
        for i in range(variant_count):
            try:
                result   = safe_call()
                copy     = clean_emojis(result.get('copy', ''), platform)
                hashtags = result.get('hashtags', [])
            except ValueError as e:
                print(f'[copy/generate] using fallback for {platform} variant {i + 1}: {e}', file=sys.stderr)
                copy = _fallback_copy(article, platform)
                hashtags = []
            copy, hashtags = strip_hashtags_from_copy(copy, hashtags)
            variants.append({'copy': copy, 'hashtags': hashtags})

    if language == 'fa':
        _persianize_variant_hashtags(variants, media)
        # Persian transliterations can be longer than their Latin originals. Refit
        # the final assembled post after localization so X still stays within 280.
        hi = rule.get('maxChars')
        if hi is not None:
            for variant in variants:
                while len(variant['hashtags']) > 1 and len(' '.join(variant['hashtags'])) + 2 >= hi:
                    variant['hashtags'].pop()
                hashtag_line = ' '.join(variant['hashtags'])
                budget = hi - (2 + len(hashtag_line)) if hashtag_line else hi
                if len(variant['copy']) > budget:
                    variant['copy'] = smart_truncate(variant['copy'], max(1, budget))
    else:
        # Force the English brand identity hashtag to position 0 of every variant.
        for variant in variants:
            variant['hashtags'] = prepend_brand_tag(variant['hashtags'], media)

    # Final defense for every path, including source-based fallback copy.
    for variant in variants:
        variant['copy'] = _plain_social_copy(variant.get('copy', ''))

    primary = variants[0]
    # TEMPORARY: log the final (cleaned, length-checked, brand-tagged) variants
    # so the operator can compare raw model output vs what the UI/publish step sees.
    try:
        _sess_log(f'copy_result_{platform}', 'variants_final',
                  mediaBrand=media, platform=platform, sentiment=sentiment,
                  model_key=model_key, article_title=article.get('title', ''),
                  promo_mode=is_promo, variants=variants)
    except Exception:
        pass
    return {
        'variants': variants,
        'copy': primary['copy'],
        'hashtags': primary['hashtags'],
        'charCount': len(primary['copy']),
        'platform': platform,
    }
