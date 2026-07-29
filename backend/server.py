"""
RZWire Backend — Python 3.11
Runs on port 3001. Proxies all OpenRouter (AI) and Google Apps Script calls server-side.
Start: python server.py

NOTE: business logic lives in the sibling modules (config, llm, image_pipeline,
brand_profiles, _branddoc, server_utils) and the handlers/ package. This file is
now just the HTTP layer (the Handler class) + the entry point.
"""

import json
import gzip
import sys
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

import auth
import database
from config import (
    PORT, ORIGIN, COOKIE_SECURE, OPENROUTER_KEY, SCRIPT_URL,
    PUBLISHING_ENABLED, SHEETS_ENABLED,
)
from server_utils import _json_default

# Handler functions — one import per domain module.
from handlers.copy import handle_generate_copy
from handlers.image import handle_promo_ideas, handle_generate_image
from handlers.editorial import (handle_editorial_select, handle_filter_pipeline,
                                handle_deepseek_filter)
from handlers.account import (build_account_summary, handle_log_action,
                              handle_log_keywords, handle_brand_keywords,
                              handle_saved_discard, handle_saved_update,
                              handle_saved_confirm_schedule)
from handlers.schedule import (handle_schedule_create, handle_schedule_list,
                               handle_schedule_cancel, handle_schedule_reschedule,
                               run_scheduler_loop)
from handlers.social import handle_telegram_post, handle_twitter_post
from handlers.sheets import handle_sheets
from handlers.chat import (
    chat_health_status,
    handle_chat,
    handle_chat_history,
    run_chat_cleanup_loop,
    start_chat_indexer,
)
from handlers.translation import handle_translate_cards
from handlers.market import handle_market_history
from telegram_public import DEFAULT_TELEGRAM_SOURCES, fetch_many_telegram_public_posts, rank_telegram_posts


# ── HTTP Request Handler ───────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        # self.command/self.path may be unset if the request line itself failed
        # to parse (malformed/truncated request) — send_error() still logs in
        # that case, so guard with getattr to avoid crashing the handler thread.
        cmd  = getattr(self, 'command', '?')
        path = getattr(self, 'path', '?')
        print(f'[{cmd}] {path} — {args[1] if len(args) > 1 else ""}')

    def send_cors(self):
        origin = self.headers.get('Origin')
        allow  = origin if (ORIGIN == '*' and origin) else ORIGIN
        self.send_header('Access-Control-Allow-Origin', allow)
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Content-Encoding')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            self._json({'ok': True, 'chat': chat_health_status()})
        elif self.path == '/api/integrations/status':
            self._json({
                'publishing': {'enabled': PUBLISHING_ENABLED},
                'sheets': {'enabled': SHEETS_ENABLED},
            })
        elif self.path.startswith('/api/market/history'):
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            params = parse_qs(urlparse(self.path).query)
            try:
                self._json(handle_market_history(params))
            except ValueError as exc:
                self._error(400, str(exc))
            except Exception as exc:
                self._error(502, f'Market data extraction failed: {exc}')
        elif self.path == '/api/auth/me':
            user = auth.get_current_user(self)
            if user is None:
                self._error(401, 'Not authenticated')
            else:
                self._json({'user': user})
        elif self.path == '/api/account/summary':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json(build_account_summary(user['id']))
        elif self.path.startswith('/api/account/brand-keywords'):
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            brands_param = params.get('brands', [''])[0]
            self._json(handle_brand_keywords(user['id'], brands_param))
        elif self.path == '/api/account/saved':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json({'cards': database.get_saved_cards(user['id'], status='saved')})
        elif self.path == '/api/schedule/list':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json(handle_schedule_list(user['id']))
        elif self.path.rstrip('/') == '/api/chat/history':
            user = auth.get_current_user(self)
            if user is None:
                return self._error(401, 'Not authenticated')
            self._json(handle_chat_history(user['id']))
        elif self.path.startswith('/api/rss'):
            from urllib.parse import urlparse, parse_qs, unquote
            params = parse_qs(urlparse(self.path).query)
            url    = unquote(params.get('url', [''])[0])
            if not url:
                return self._error(400, 'url parameter required')
            try:
                r = requests.get(url, timeout=15,
                                 headers={'User-Agent': 'Mozilla/5.0 (compatible; RZWire/1.0)'})
                r.raise_for_status()
                body = r.content
                self.send_response(200)
                self.send_cors()
                self.send_header('Content-Type', r.headers.get('Content-Type', 'application/xml'))
                accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '')
                if accepts_gzip and len(body) > 1024:
                    body = gzip.compress(body)
                    self.send_header('Content-Encoding', 'gzip')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)
            except Exception as e:
                self._error(502, f'RSS fetch failed: {e}')
        elif self.path.startswith('/api/telegram/public-posts'):
            from urllib.parse import urlparse, parse_qs
            params = parse_qs(urlparse(self.path).query)
            raw_channels = params.get('channels', [''])[0]
            channels = [c.strip() for c in raw_channels.split(',') if c.strip()]
            if not channels:
                channels = list(DEFAULT_TELEGRAM_SOURCES.values())
            try:
                hours = int(params.get('hours', ['24'])[0])
            except (TypeError, ValueError):
                hours = 24
            try:
                limit = int(params.get('limit', ['20'])[0])
            except (TypeError, ValueError):
                limit = 20
            try:
                self._json(fetch_many_telegram_public_posts(
                    channels,
                    hours=hours,
                    limit_per_channel=max(1, min(limit, 50)),
                ))
            except Exception as e:
                self._error(502, f'Telegram fetch failed: {e}')
        elif self.path == '/api/telegram/sources':
            self._json({'sources': DEFAULT_TELEGRAM_SOURCES})
        else:
            self._error(404, 'Not found')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw    = self.rfile.read(length)
        if 'gzip' in self.headers.get('Content-Encoding', ''):
            try:
                raw = gzip.decompress(raw)
            except OSError:
                return self._error(400, 'Invalid request encoding')
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._error(400, 'Invalid JSON')

        try:
            path = self.path.rstrip('/')
            if path == '/api/auth/login':
                identifier = (body.get('identifier') or '').strip()
                password   = body.get('password') or ''
                remember   = bool(body.get('rememberMe'))
                user = database.get_user_by_identifier(identifier) if identifier else None
                if not user or not auth.verify_password(password, user['password_hash']):
                    return self._error(401, 'Invalid username/email or password')
                ttl_days = database.SESSION_TTL_DAYS if remember else 1
                token = database.create_session(user['id'], ttl_days=ttl_days)
                self._json(
                    {'user': database.get_user_by_id(user['id'])},
                    extra_headers={'Set-Cookie': auth.make_session_cookie(token, COOKIE_SECURE, ttl_days=ttl_days, remember=remember)}
                )
            elif path == '/api/auth/logout':
                token = auth.get_session_token(self)
                if token:
                    database.delete_session(token)
                self._json({'ok': True}, extra_headers={'Set-Cookie': auth.make_clear_cookie(COOKIE_SECURE)})
            elif path == '/api/account/log-action':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_log_action(user['id'], body))
            elif path == '/api/account/log-keywords':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_log_keywords(user['id'], body))
            elif path == '/api/account/save':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json({'ok': True, 'id': database.create_saved_card(user['id'], body)})
            elif path == '/api/account/saved/discard':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_saved_discard(user['id'], body))
            elif path == '/api/account/saved/update':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_saved_update(user['id'], body))
            elif path == '/api/account/saved/confirm-schedule':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_saved_confirm_schedule(user['id'], body))
            elif path == '/api/schedule/create':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_create(user['id'], body))
            elif path == '/api/schedule/cancel':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_cancel(user['id'], body))
            elif path == '/api/schedule/reschedule':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_schedule_reschedule(user['id'], body))
            elif path == '/api/copy/generate':
                self._json(handle_generate_copy(body))
            elif path == '/api/promo/generate-ideas':
                self._json(handle_promo_ideas(body))
            elif path == '/api/image/generate':
                self._json(handle_generate_image(body))
            elif path == '/api/sheets/approve':
                self._json(handle_sheets('approve', body))
            elif path == '/api/sheets/schedule':
                self._json(handle_sheets('schedule', body))
            elif path == '/api/sheets/update':
                self._json(handle_sheets('update', body))
            elif path == '/api/sheets/upload-image':
                self._json(handle_sheets('uploadImage', body))
            elif path == '/api/twitter/post':
                self._json(handle_twitter_post(body))
            elif path == '/api/ai/editorial-select':
                gen = handle_editorial_select(body)
                first = next(gen)   # raises ValueError before any header is sent
                try:
                    self._stream_ndjson_start()
                    self._stream_ndjson_write({first[0]: first[1]})
                    for key, data in gen:
                        self._stream_ndjson_write({key: data})
                    self._stream_ndjson_end()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass   # client disconnected mid-stream — headers already sent, nothing more to do
                except Exception as e:
                    print(f'[ERROR] editorial-select stream: {e}', file=sys.stderr)
                return
            elif path == '/api/filter/pipeline':
                self._json(handle_filter_pipeline(body))
            elif path == '/api/filter/deepseek':
                self._json(handle_deepseek_filter(body))
            elif path == '/api/telegram/post':
                self._json(handle_telegram_post(body))
            elif path == '/api/telegram/rank':
                self._json(rank_telegram_posts(body))
            elif path == '/api/translate/cards':
                self._json(handle_translate_cards(body))
            elif path == '/api/chat':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                self._json(handle_chat(user['id'], body))
            elif path == '/api/chat/clear':
                user = auth.get_current_user(self)
                if user is None:
                    return self._error(401, 'Not authenticated')
                database.clear_chat(user['id'])
                self._json({'ok': True})
            else:
                self._error(404, f'Unknown route: {path}')
        except ValueError as e:
            self._error(400, str(e))
        except requests.HTTPError as e:
            self._error(502, f'Upstream error: {e}')
        except Exception as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            self._error(500, str(e))

    def _json(self, data, status=200, extra_headers=None):
        body = json.dumps(data, default=_json_default).encode()
        self.send_response(status)
        self.send_cors()
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header('Content-Type', 'application/json')
        # Large AI responses (100s of KB) can stall mid-transfer on networks with
        # MTU/PMTUD issues (VPNs, mobile, some ISPs). Gzip shrinks JSON ~70-85%,
        # which both speeds delivery and avoids tripping that black hole.
        accepts_gzip = 'gzip' in self.headers.get('Accept-Encoding', '')
        if accepts_gzip and len(body) > 1024:
            body = gzip.compress(body)
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        self._json({'error': msg}, code)

    def _stream_ndjson_start(self):
        self.send_response(200)
        self.send_cors()
        self.send_header('Content-Type', 'application/x-ndjson')
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()

    def _stream_ndjson_write(self, obj):
        line  = (json.dumps(obj, default=_json_default) + '\n').encode()
        chunk = f'{len(line):x}\r\n'.encode() + line + b'\r\n'
        self.wfile.write(chunk)
        self.wfile.flush()

    def _stream_ndjson_end(self):
        self.wfile.write(b'0\r\n\r\n')
        self.wfile.flush()


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    database.init_db()
    if not OPENROUTER_KEY:
        print('[WARN] OPENROUTER_API_KEY not set — AI routes will fail', file=sys.stderr)
    if SHEETS_ENABLED and (not SCRIPT_URL or SCRIPT_URL.startswith('PASTE_')):
        print('[WARN] GOOGLE_APPS_SCRIPT_URL not set — Sheets routes will fail', file=sys.stderr)

    if PUBLISHING_ENABLED:
        threading.Thread(target=run_scheduler_loop, daemon=True).start()
    threading.Thread(target=run_chat_cleanup_loop, daemon=True).start()
    start_chat_indexer()

    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    server.daemon_threads = True
    print(f'RZWire backend running at http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
