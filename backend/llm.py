"""OpenRouter LLM helpers: chat (with JSON repair), image generation, and the
threaded single-editorial-model call. The OpenAI-SDK client is a process-wide
singleton here so all callers share one connection pool.
"""
import json
import re
import sys
import threading
import time

import requests
import openai as _openai_sdk

from config import OPENROUTER_KEY, ORIGIN, OPENROUTER_IMAGE_MODELS

# TEMPORARY session-capture instrumentation (see backend/session_log.py).
from session_log import log as _sess_log


def _repair_json(raw):
    """Strip markdown fences, then parse JSON; if truncated, salvage partial content."""
    # Strip <think>...</think> reasoning blocks (DeepSeek and other reasoning models)
    s = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
    # Also handle unclosed <think> blocks (model cut off mid-reasoning)
    s = re.sub(r'<think>.*$', '', s, flags=re.DOTALL)
    s = s.strip()
    raw = s if s else raw
    # Strip ```json ... ``` or ``` ... ``` wrappers
    s = raw.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[-1]          # drop first line (```json)
        s = s.rsplit('```', 1)[0].strip() # drop closing ```
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raw = s  # work on stripped version for repair attempts
    # Try appending common closing sequences to fix truncation
    for ending in (']}}}', ']}}', '}}', '}'):
        try:
            return json.loads(raw + ending)
        except json.JSONDecodeError:
            pass
    # Find the last complete `]` and close from there
    last_bracket = raw.rfind(']')
    if last_bracket > 0:
        trimmed = raw[:last_bracket + 1]
        for ending in ('}', '}}', '}}}'):
            try:
                return json.loads(trimmed + ending)
            except json.JSONDecodeError:
                pass
    # Also try stripping markdown fences that appear mid-string (model added preamble text)
    fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)```', raw)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Last resort: try every '{' position left-to-right until one parses
    # (handles reasoning models that prepend preamble text before the JSON)
    for m in re.finditer(r'\{', raw):
        candidate = raw[m.start():]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        for ending in (']}}}', ']}}', '}}', '}'):
            try:
                return json.loads(candidate + ending)
            except json.JSONDecodeError:
                pass

    # Model ignored the "respond with JSON" instruction and just wrote the post directly —
    # if there's no '{' anywhere, there's no JSON to recover; treat the prose itself as the copy.
    if '{' not in raw and raw.strip():
        return {'copy': raw.strip(), 'hashtags': []}

    preview = raw[:300].replace('\n', ' ')
    print(f'[JSON REPAIR FAILED] len={len(raw)} preview: {preview}', file=sys.stderr)
    raise ValueError(f'Could not parse or repair JSON response (len={len(raw)})')

_openrouter_client = None
_openrouter_client_lock = threading.Lock()
def _get_openrouter_client():
    global _openrouter_client
    if _openrouter_client is None:
        with _openrouter_client_lock:
            if _openrouter_client is None:
                _openrouter_client = _openai_sdk.OpenAI(
                    base_url='https://openrouter.ai/api/v1',
                    api_key=OPENROUTER_KEY,
                    default_headers={
                        'HTTP-Referer': ORIGIN if ORIGIN != '*' else 'https://rzwire.local',
                        'X-Title':      'RZWire Editorial AI',
                    },
                    timeout=180,
                    max_retries=3,
                )
    return _openrouter_client

# When a reasoning model (e.g. Gemini Flash, DeepSeek, GPT-5.x) burns its token
# budget on internal "thinking" and returns ZERO visible content with
# finish_reason=length, transparently retry with a doubled budget. Without this,
# the image pipeline surfaces "Image generation failed: Model returned empty
# content (finish_reason=length)" to the user.
#
# IMPORTANT — wall-clock budget: each retry is itself a full LLM call that can
# run up to the client timeout (180s). Left uncapped, the chain can stall for
# several minutes, which the browser/proxy kills as "Failed to fetch" before
# the backend finishes. So we enforce a hard total deadline (default 45s) and
# shrink each attempt's timeout to whatever time remains. For call sites that
# have a deterministic fallback (Art Director image pipeline), a short deadline
# is strictly better than a long one: the fallback takes over quickly.
_EMPTY_LENGTH_RETRIES = 3
_DEFAULT_RETRY_DEADLINE_SEC = 45


def _chat_with_length_retry(client, model_id, messages, temperature, max_tokens, *,
                            label='', deadline_sec=_DEFAULT_RETRY_DEADLINE_SEC):
    """Call the chat endpoint; if the reply is empty due to finish_reason=length,
    double max_tokens and retry. Total wall-clock time across all attempts is
    bounded by `deadline_sec`. Returns the non-empty content string."""
    started = time.monotonic()
    budget = max_tokens
    for attempt in range(_EMPTY_LENGTH_RETRIES):
        remaining = deadline_sec - (time.monotonic() - started)
        if remaining <= 1:
            break  # no time for another full attempt — let the caller's fallback handle it
        # Keep the singleton's HTTP connection pool while applying a tight
        # timeout to this attempt. Creating a new OpenAI client here used to
        # discard connection reuse on every request, adding a fresh TLS setup
        # to latency-sensitive calls such as the in-app chatbot.
        scoped = client.with_options(
            timeout=min(remaining, 30),
            max_retries=0,
        )
        try:
            resp = scoped.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=budget,
            )
        except Exception as exc:
            # Time-budget exhaustion or transport error — stop retrying and let
            # the caller decide (Art Director falls back to the deterministic brief).
            print(f'[{label or "chat"}] attempt {attempt+1} error: {exc}', file=sys.stderr)
            raise ValueError(f'Model call failed during retry: {exc}')

        raw = resp.choices[0].message.content or ''
        if raw:
            return raw
        finish = resp.choices[0].finish_reason
        if finish != 'length':
            raise ValueError(f'Model returned empty content (finish_reason={finish}).')
        budget *= 2
        print(f'[{label or "chat"}] empty reply (finish_reason=length) — retry {attempt+1}/'
              f'{_EMPTY_LENGTH_RETRIES} with max_tokens={budget}', file=sys.stderr)
    raise ValueError(
        f'Model returned empty content (finish_reason=length); retry budget '
        f'({deadline_sec}s) exhausted. Falling back if available.'
    )


def _classify_stage(messages) -> str:
    """TEMPORARY: tag a chat call as 'editorial' or 'copy_x'/'copy_telegram'
    by sniffing the system prompt, so the session log groups calls by stage."""
    sys_msg = ''
    for m in messages:
        if m.get('role') == 'system':
            sys_msg = m.get('content', '') or ''
            break
    low = sys_msg.lower()
    if 'senior crypto news editor' in low or 'independent editorial decisions' in low:
        return 'editorial_select'
    if 'telegram channel editor' in low or ('telegram' in low and 'copy' in low):
        return 'copy_telegram'
    if 'senior social media editor' in low or 'scroll-stopping one-liner' in low:
        return 'copy_x'
    if 'instagram editor' in low:
        return 'copy_instagram'
    if 'test assistant' in low:
        return 'editorial_select_test'
    return 'chat_other'


def openrouter_chat(model_id, messages, temperature=0.30, max_tokens=3500, *, deadline_sec=None):
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')
    client = _get_openrouter_client()
    kw = {'label': 'chat'}
    if deadline_sec is not None:
        kw['deadline_sec'] = deadline_sec
    raw = _chat_with_length_retry(client, model_id, messages, temperature, max_tokens, **kw)
    # TEMPORARY: capture the verbatim prompt + RAW model reply (before _repair_json).
    try:
        _sess_log(_classify_stage(messages), 'llm_call',
                  model=model_id, temperature=temperature, max_tokens=max_tokens,
                  messages=messages, raw_reply=raw)
    except Exception:
        pass
    return _repair_json(raw)


def openrouter_chat_text(model_id, messages, temperature=0.4, max_tokens=1200, *, deadline_sec=None):
    """Conversational variant of openrouter_chat: returns the raw reply text as-is,
    without forcing JSON parsing. Used by the in-app chat assistant."""
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')
    client = _get_openrouter_client()
    kw = {'label': 'chat-text'}
    if deadline_sec is not None:
        kw['deadline_sec'] = deadline_sec
    raw = _chat_with_length_retry(client, model_id, messages, temperature, max_tokens, **kw)
    return raw.strip()


def _editorial_call_one(model_key, model_cfg, system_prompt, user_prompt):
    """Called in a thread — returns (model_key, result_dict)."""
    msgs = [{'role': 'system', 'content': system_prompt},
            {'role': 'user',   'content': user_prompt}]
    try:
        result = openrouter_chat(model_cfg['id'], msgs, model_cfg['temperature'], model_cfg['max_tokens'])
        return model_key, {
            'model':  model_cfg['display'],
            'brands': result.get('brands', {}),
            'error':  None,
        }
    except Exception as exc:
        return model_key, {
            'model':  model_cfg['display'],
            'brands': {},
            'error':  str(exc),
        }

# ── OpenRouter image generation ───────────────────────────────────────────────
_IMAGE_FALLBACK_MODEL = 'openai/gpt-5.4-image-2'


def _extract_openrouter_image(data):
    choice = (data.get('choices') or [{}])[0]
    msg = choice.get('message') or {}
    images = msg.get('images') or []
    if images:
        image_url = (images[0].get('image_url') or {}).get('url', '')
        if image_url:
            return image_url.split(',', 1)[1] if ',' in image_url else image_url
    content = msg.get('content', '')
    if isinstance(content, str) and content.startswith('data:'):
        return content.split(',', 1)[1] if ',' in content else content
    return '', choice.get('finish_reason'), str(content or '')[:160]


def openrouter_image(prompt, model, ref_images=None):
    """Generate an image with retry and cross-model fallback.

    Preview image providers occasionally return HTTP 200 with finish_reason=stop
    but no image. Retry the requested model once, then use the production fallback
    so a transient provider miss does not surface to the user.
    """
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')

    models = [model, model]
    if model != _IMAGE_FALLBACK_MODEL:
        models.append(_IMAGE_FALLBACK_MODEL)
    errors = []
    headers = {
        'Authorization': f'Bearer {OPENROUTER_KEY}',
        'Content-Type': 'application/json',
        'HTTP-Referer': ORIGIN if ORIGIN != '*' else 'https://rzwire.local',
        'X-Title': 'RZWire Editorial AI',
    }

    for attempt, attempt_model in enumerate(models):
        retry_note = '' if attempt == 0 else (
            ' Generate exactly one finished image now. Return an image output, not a text description.'
        )
        attempt_prompt = prompt + retry_note
        if ref_images:
            content = [{'type': 'text', 'text': attempt_prompt}]
            content.extend({'type': 'image_url', 'image_url': {'url': url}} for url in ref_images)
        else:
            content = attempt_prompt
        try:
            response = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                json={
                    'model': attempt_model,
                    'messages': [{'role': 'user', 'content': content}],
                    'modalities': OPENROUTER_IMAGE_MODELS.get(attempt_model, ['image', 'text']),
                },
                headers=headers,
                timeout=150,
            )
            response.raise_for_status()
            data = response.json()
            extracted = _extract_openrouter_image(data)
            if isinstance(extracted, str):
                print(f'[image] generated with {attempt_model} on attempt {attempt + 1}', file=sys.stderr)
                return extracted, attempt_model
            _, finish, text_reply = extracted
            detail = f'no image (finish_reason={finish})'
            if text_reply:
                detail += f': {text_reply}'
            errors.append(f'{attempt_model}: {detail}')
            print(f'[image] {detail}; retrying', file=sys.stderr)
        except Exception as exc:  # provider/network failures should also reach fallback
            errors.append(f'{attempt_model}: {exc}')
            print(f'[image] {attempt_model} attempt {attempt + 1} failed: {exc}', file=sys.stderr)

    raise ValueError('All image generation attempts failed. ' + ' | '.join(errors))
