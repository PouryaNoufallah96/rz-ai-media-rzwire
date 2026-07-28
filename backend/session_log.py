"""
TEMPORARY — SESSION CAPTURE LOGGER
==================================
Purpose: record what the AI pipeline does during a real session so the
operator can inspect (verbatim):
  - the exact system + user prompt sent to each LLM call
  - the RAW model reply BEFORE _repair_json / emoji / hashtag / length cleanup
  - the cleaned copy variants the user sees in the UI
  - the final text actually shipped to Telegram / X

This file is throwaway scaffolding. To fully revert the codebase to its
pre-instrumentation state:
  1. delete this file (backend/session_log.py)
  2. remove every `from session_log import log_*` and `log_*(...)` line
     from llm.py, handlers/copy.py, handlers/social.py, handlers/editorial.py
It writes nothing else to disk and changes no runtime behaviour.

Output: one JSONL file per session, at  backend/logs/session_<UTC timestamp>.jsonl
Each line is one event: {"ts":..., "stage":..., "event":..., "payload":{...}}
"""

import json
import os
import threading
import time
from pathlib import Path

_LOG_DIR = Path(__file__).parent / 'logs'
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_lock = threading.Lock()
# Set lazily on first write so each session = one file, stamped with its
# start time (not import time — the server process may run for hours).
_path: str | None = None


def _current_path() -> str:
    global _path
    if _path is None:
        ts = time.strftime('%Y%m%d_%H%M%S', time.gmtime())
        _path = str(_LOG_DIR / f'session_{ts}.jsonl')
    return _path


def log(stage: str, event: str, **payload):
    """Append one event to the session log. Best-effort: never raises."""
    try:
        line = {
            'ts':    time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'stage': stage,
            'event': event,
            'payload': payload,
        }
        with _lock:
            with open(_current_path(), 'a', encoding='utf-8') as f:
                f.write(json.dumps(line, ensure_ascii=False, default=str) + '\n')
    except Exception as e:  # pragma: no cover — logging must never break the request
        print(f'[session_log] write failed: {e}', file=sys.stderr)


def log_path() -> str:
    """Path to the active session file (for the operator to find it)."""
    return _current_path()
