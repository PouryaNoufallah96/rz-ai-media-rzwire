"""Strict localhost client for the EmbeddingGemma llama.cpp service."""

import json
import os
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class EmbeddingUnavailable(RuntimeError):
    """Raised when the private embedding service is unavailable or malformed."""


EMBEDDING_BASE_URL = os.getenv(
    'CHAT_EMBEDDING_URL', 'http://127.0.0.1:8081',
).rstrip('/')
EMBEDDING_TIMEOUT_SECONDS = float(os.getenv('CHAT_EMBEDDING_TIMEOUT', '3'))
EMBEDDING_DIMENSION = int(os.getenv('CHAT_EMBEDDING_DIMENSION', '768'))
_LOOPBACK_HOSTS = {'127.0.0.1', 'localhost', '::1'}


def _validate_loopback():
    parsed = urlparse(EMBEDDING_BASE_URL)
    if parsed.scheme != 'http' or parsed.hostname not in _LOOPBACK_HOSTS:
        raise EmbeddingUnavailable(
            'CHAT_EMBEDDING_URL must use a private localhost HTTP address'
        )


def _extract_embedding(payload):
    candidate = payload
    if isinstance(payload, dict) and isinstance(payload.get('data'), list):
        candidate = payload['data'][0] if payload['data'] else None
    elif isinstance(payload, list):
        candidate = payload[0] if payload else None
    if isinstance(candidate, dict):
        candidate = candidate.get('embedding', candidate.get('embeddings'))
    if (
        isinstance(candidate, list)
        and candidate
        and isinstance(candidate[0], list)
    ):
        candidate = candidate[0]
    if not isinstance(candidate, list) or not candidate:
        raise EmbeddingUnavailable('Embedding service returned no vector')
    try:
        vector = [float(value) for value in candidate]
    except (TypeError, ValueError) as exc:
        raise EmbeddingUnavailable('Embedding service returned an invalid vector') from exc
    if len(vector) != EMBEDDING_DIMENSION:
        raise EmbeddingUnavailable(
            f'Expected {EMBEDDING_DIMENSION} dimensions, received {len(vector)}'
        )
    return vector


def _embed(prompt):
    _validate_loopback()
    try:
        request = Request(
            f'{EMBEDDING_BASE_URL}/embedding',
            data=json.dumps({'input': prompt, 'embd_normalize': 2}).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urlopen(request, timeout=EMBEDDING_TIMEOUT_SECONDS) as response:
            return _extract_embedding(json.load(response))
    except EmbeddingUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EmbeddingUnavailable(f'Local EmbeddingGemma request failed: {exc}') from exc


def embed_query(question):
    return _embed(f'task: question answering | query: {question.strip()}')


def embed_document(title, content):
    return _embed(f'title: {title.strip()} | text: {content.strip()}')


def health(timeout_seconds=0.5):
    """Return a safe health snapshot without exposing model or filesystem data."""
    started = time.monotonic()
    try:
        _validate_loopback()
        request = Request(f'{EMBEDDING_BASE_URL}/health', method='GET')
        with urlopen(request, timeout=timeout_seconds) as response:
            ok = response.status == 200
        return {
            'status': 'ok' if ok else 'unavailable',
            'latencyMs': round((time.monotonic() - started) * 1000),
        }
    except Exception:  # noqa: BLE001
        return {
            'status': 'unavailable',
            'latencyMs': round((time.monotonic() - started) * 1000),
        }
