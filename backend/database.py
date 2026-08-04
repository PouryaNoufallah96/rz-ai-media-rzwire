"""
RZWire — SQLite persistence for user accounts and sessions.

Opens a fresh connection per call (safe for ThreadingHTTPServer). Database file
lives at backend/data/app.db (gitignored).
"""

import json
import sqlite3
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / 'data' / 'app.db'

SESSION_TTL_DAYS = 30
CHAT_INACTIVITY_MINUTES = 60


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 5000')
    return conn


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def init_db():
    conn = _connect()
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                brand TEXT NOT NULL,
                platform TEXT NOT NULL,
                model_display TEXT NOT NULL,
                headline TEXT NOT NULL,
                action TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_activity_log_user_time ON activity_log (user_id, created_at)')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS saved_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                card_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                platform TEXT NOT NULL,
                model_display TEXT,
                model_color TEXT,
                headline TEXT NOT NULL,
                copy TEXT,
                hashtags TEXT,
                sentiment TEXT,
                suitability INTEGER,
                impact INTEGER,
                virality INTEGER,
                source TEXT,
                source_link TEXT,
                initials TEXT,
                src_color TEXT,
                image_b64 TEXT,
                status TEXT NOT NULL DEFAULT 'saved',
                variants TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_saved_cards_user_status ON saved_cards (user_id, status, created_at)')
        try:
            conn.execute('ALTER TABLE saved_cards ADD COLUMN variants TEXT')
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute('ALTER TABLE saved_cards ADD COLUMN image_b64 TEXT')
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS keyword_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                keyword TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_keyword_log_user_time ON keyword_log (user_id, created_at)')
        try:
            conn.execute("ALTER TABLE keyword_log ADD COLUMN brand TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        conn.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                saved_card_id INTEGER,
                card_id TEXT NOT NULL,
                brand TEXT NOT NULL,
                platform TEXT NOT NULL,
                model_display TEXT,
                headline TEXT NOT NULL,
                copy TEXT,
                hashtags TEXT,
                sentiment TEXT,
                suitability INTEGER,
                impact INTEGER,
                virality INTEGER,
                source TEXT,
                source_link TEXT,
                image_b64 TEXT,
                image_url TEXT,
                scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error TEXT,
                created_at TEXT NOT NULL,
                posted_at TEXT
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_scheduled_posts_due ON scheduled_posts (status, scheduled_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_scheduled_posts_user ON scheduled_posts (user_id, created_at)')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        chat_message_columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(chat_messages)').fetchall()
        }
        if 'metadata_json' not in chat_message_columns:
            conn.execute('ALTER TABLE chat_messages ADD COLUMN metadata_json TEXT')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_messages_user_time ON chat_messages (user_id, created_at)')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS analytics_chart_defaults (
                user_id INTEGER NOT NULL REFERENCES users(id),
                brand_id TEXT NOT NULL,
                style_json TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, brand_id)
            )
        ''')
        conn.commit()
    finally:
        conn.close()


def _user_to_dict(row):
    return {
        'id': row['id'],
        'username': row['username'],
        'email': row['email'],
        'createdAt': row['created_at'],
    }


def create_user(username, email, password_hash):
    conn = _connect()
    try:
        try:
            cur = conn.execute(
                'INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)',
                (username, email, password_hash, _now_iso())
            )
        except sqlite3.IntegrityError:
            raise ValueError('Username or email already in use')
        conn.commit()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (cur.lastrowid,)).fetchone()
        return _user_to_dict(row)
    finally:
        conn.close()


def set_password(user_id, password_hash):
    conn = _connect()
    try:
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


def get_user_by_identifier(identifier):
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT * FROM users WHERE username = ? OR email = ?', (identifier, identifier)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = _connect()
    try:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return _user_to_dict(row) if row else None
    finally:
        conn.close()


def get_analytics_chart_default(user_id, brand_id):
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT style_json, updated_at FROM analytics_chart_defaults WHERE user_id = ? AND brand_id = ?',
            (user_id, brand_id),
        ).fetchone()
        if not row:
            return None
        return {
            'style': json.loads(row['style_json']),
            'updatedAt': row['updated_at'],
        }
    finally:
        conn.close()


def save_analytics_chart_default(user_id, brand_id, style):
    updated_at = _now_iso()
    encoded = json.dumps(style, ensure_ascii=False, separators=(',', ':'))
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO analytics_chart_defaults (user_id, brand_id, style_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, brand_id) DO UPDATE SET
                style_json = excluded.style_json,
                updated_at = excluded.updated_at
            ''',
            (user_id, brand_id, encoded, updated_at),
        )
        conn.commit()
        return {'style': style, 'updatedAt': updated_at}
    finally:
        conn.close()


def cleanup_expired_sessions():
    conn = _connect()
    try:
        conn.execute('DELETE FROM sessions WHERE expires_at < ?', (_now_iso(),))
        conn.commit()
    finally:
        conn.close()


def create_session(user_id, ttl_days=SESSION_TTL_DAYS):
    cleanup_expired_sessions()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=ttl_days)).isoformat()
    conn = _connect()
    try:
        conn.execute(
            'INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
            (token, user_id, now.isoformat(), expires_at)
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_id_for_session(token):
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT user_id, expires_at FROM sessions WHERE token = ?', (token,)
        ).fetchone()
        if not row:
            return None
        expires_at = datetime.fromisoformat(row['expires_at'])
        if expires_at < datetime.now(timezone.utc):
            return None
        return row['user_id']
    finally:
        conn.close()


def delete_session(token):
    conn = _connect()
    try:
        conn.execute('DELETE FROM sessions WHERE token = ?', (token,))
        conn.commit()
    finally:
        conn.close()


def log_activity(user_id, brand, platform, model_display, headline, action):
    conn = _connect()
    try:
        conn.execute(
            'INSERT INTO activity_log (user_id, brand, platform, model_display, headline, action, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, brand, platform, model_display, headline, action, _now_iso())
        )
        conn.commit()
    finally:
        conn.close()


def count_activity(user_id, action=None):
    conn = _connect()
    try:
        if action:
            row = conn.execute('SELECT COUNT(*) AS c FROM activity_log WHERE user_id = ? AND action = ?', (user_id, action)).fetchone()
        else:
            row = conn.execute('SELECT COUNT(*) AS c FROM activity_log WHERE user_id = ?', (user_id,)).fetchone()
        return row['c']
    finally:
        conn.close()


def get_brand_stats(user_id):
    """Returns {brand: {'generated': N, 'scheduled': N}}."""
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT brand, action, COUNT(*) AS c FROM activity_log WHERE user_id = ? GROUP BY brand, action',
            (user_id,)
        ).fetchall()
        out = {}
        for r in rows:
            b = out.setdefault(r['brand'], {'generated': 0, 'scheduled': 0})
            if r['action'] == 'scheduled':
                b['scheduled'] = r['c']
            b['generated'] += r['c']
        return out
    finally:
        conn.close()


def get_recent_activity(user_id, limit=200):
    """Raw rows, most-recent first, for grouping into batches."""
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT brand, platform, model_display, headline, action, created_at '
            'FROM activity_log WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def log_keywords(user_id, keywords, brand=''):
    """keywords: list[str], already trimmed/non-empty."""
    if not keywords:
        return
    conn = _connect()
    try:
        now = _now_iso()
        conn.executemany(
            'INSERT INTO keyword_log (user_id, keyword, brand, created_at) VALUES (?, ?, ?, ?)',
            [(user_id, kw, brand, now) for kw in keywords]
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_keywords(user_id, limit=12):
    """Most-recently-used distinct keywords, case-insensitive de-dup, most recent first."""
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT keyword, MAX(created_at) AS last_used FROM keyword_log '
            'WHERE user_id = ? GROUP BY LOWER(keyword) ORDER BY last_used DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [r['keyword'] for r in rows]
    finally:
        conn.close()


def get_brand_keywords(user_id, brands, limit=10):
    """Most recent distinct keywords for given brands."""
    if not brands:
        return []
    conn = _connect()
    try:
        placeholders = ','.join('?' * len(brands))
        rows = conn.execute(
            f'SELECT keyword, MAX(created_at) AS last_used FROM keyword_log '
            f'WHERE user_id = ? AND brand IN ({placeholders}) '
            f'GROUP BY LOWER(keyword) ORDER BY last_used DESC LIMIT ?',
            (user_id, *brands, limit)
        ).fetchall()
        return [r['keyword'] for r in rows]
    finally:
        conn.close()


def create_saved_card(user_id, card):
    conn = _connect()
    try:
        cur = conn.execute(
            'INSERT INTO saved_cards (user_id, card_id, brand, platform, model_display, model_color, '
            'headline, copy, hashtags, sentiment, suitability, impact, virality, source, source_link, '
            'initials, src_color, image_b64, status, variants, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                user_id, card.get('id', ''), card.get('media', ''), card.get('platform', ''),
                card.get('modelDisplay', ''), card.get('modelColor', ''),
                card.get('headline', ''), card.get('copy', ''),
                json.dumps(card.get('hashtags', [])),
                card.get('sentiment', 'Neutral'),
                card.get('suitability'), card.get('impact'), card.get('virality'),
                card.get('source', ''), card.get('link', ''),
                card.get('initials', ''), card.get('srcColor', ''),
                card.get('imageB64', ''), 'saved', json.dumps(card.get('variants', [])), _now_iso()
            )
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _saved_card_to_dict(row):
    d = dict(row)
    try:
        d['hashtags'] = json.loads(d.get('hashtags') or '[]')
    except (ValueError, TypeError):
        d['hashtags'] = []
    try:
        d['variants'] = json.loads(d.get('variants') or '[]')
    except (ValueError, TypeError):
        d['variants'] = []
    return d


def get_saved_cards(user_id, status='saved'):
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT * FROM saved_cards WHERE user_id = ? AND status = ? ORDER BY created_at DESC',
            (user_id, status)
        ).fetchall()
        return [_saved_card_to_dict(r) for r in rows]
    finally:
        conn.close()


def count_saved_cards(user_id, status='saved'):
    conn = _connect()
    try:
        row = conn.execute('SELECT COUNT(*) AS c FROM saved_cards WHERE user_id = ? AND status = ?', (user_id, status)).fetchone()
        return row['c']
    finally:
        conn.close()


def update_saved_card_status(saved_id, user_id, status):
    """Returns True if a row was updated (existed and belonged to user_id)."""
    conn = _connect()
    try:
        cur = conn.execute('UPDATE saved_cards SET status = ? WHERE id = ? AND user_id = ?', (status, saved_id, user_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def update_saved_card(saved_id, user_id, data):
    fields = {
        'brand': data.get('media') or data.get('brand'),
        'platform': data.get('platform'),
        'model_display': data.get('modelDisplay'),
        'model_color': data.get('modelColor'),
        'headline': data.get('headline'),
        'copy': data.get('copy'),
        'hashtags': json.dumps(data.get('hashtags', [])) if 'hashtags' in data else None,
        'variants': json.dumps(data.get('variants', [])) if 'variants' in data else None,
    }
    updates = [(k, v) for k, v in fields.items() if v is not None]
    if not updates:
        return get_saved_card(saved_id, user_id)

    conn = _connect()
    try:
        set_clause = ', '.join(f'{k} = ?' for k, _ in updates)
        values = [v for _, v in updates] + [saved_id, user_id]
        cur = conn.execute(
            f'UPDATE saved_cards SET {set_clause} WHERE id = ? AND user_id = ?',
            values,
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        row = conn.execute('SELECT * FROM saved_cards WHERE id = ? AND user_id = ?', (saved_id, user_id)).fetchone()
        return _saved_card_to_dict(row) if row else None
    finally:
        conn.close()


def get_saved_card(saved_id, user_id):
    conn = _connect()
    try:
        row = conn.execute('SELECT * FROM saved_cards WHERE id = ? AND user_id = ?', (saved_id, user_id)).fetchone()
        return _saved_card_to_dict(row) if row else None
    finally:
        conn.close()


def create_scheduled_post(user_id, data):
    conn = _connect()
    try:
        cur = conn.execute(
            'INSERT INTO scheduled_posts (user_id, saved_card_id, card_id, brand, platform, model_display, '
            'headline, copy, hashtags, sentiment, suitability, impact, virality, source, source_link, '
            'image_b64, image_url, scheduled_at, status, created_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
                user_id, data.get('savedCardId'), data.get('cardId', ''), data.get('brand', ''),
                data.get('platform', ''), data.get('modelDisplay', ''),
                data.get('headline', ''), data.get('copy', ''),
                json.dumps(data.get('hashtags', [])),
                data.get('sentiment', 'Neutral'),
                data.get('suitability'), data.get('impact'), data.get('virality'),
                data.get('source', ''), data.get('sourceUrl', ''),
                data.get('imageB64', ''), data.get('imageUrl', ''),
                data['scheduledAt'], 'pending', _now_iso()
            )
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _scheduled_post_to_dict(row):
    d = dict(row)
    try:
        d['hashtags'] = json.loads(d.get('hashtags') or '[]')
    except (ValueError, TypeError):
        d['hashtags'] = []
    return d


def get_due_scheduled_posts(now_iso):
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT * FROM scheduled_posts WHERE status = ? AND scheduled_at <= ?',
            ('pending', now_iso)
        ).fetchall()
        return [_scheduled_post_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_scheduled_posts(user_id, limit=50):
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT * FROM scheduled_posts WHERE user_id = ? ORDER BY scheduled_at DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        return [_scheduled_post_to_dict(r) for r in rows]
    finally:
        conn.close()


def mark_scheduled_post(post_id, status, error=None):
    conn = _connect()
    try:
        conn.execute(
            'UPDATE scheduled_posts SET status = ?, error = ?, posted_at = ? WHERE id = ?',
            (status, error, _now_iso(), post_id)
        )
        conn.commit()
    finally:
        conn.close()


def cancel_scheduled_post(post_id, user_id):
    """Cancels a pending scheduled post owned by user_id. Returns the row as a
    dict if cancelled, or None if not found / not pending."""
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT * FROM scheduled_posts WHERE id = ? AND user_id = ? AND status = ?',
            (post_id, user_id, 'pending')
        ).fetchone()
        if not row:
            return None
        conn.execute('UPDATE scheduled_posts SET status = ? WHERE id = ?', ('cancelled', post_id))
        conn.commit()
        return _scheduled_post_to_dict(row)
    finally:
        conn.close()


def reschedule_scheduled_post(post_id, user_id, scheduled_at):
    """Updates scheduled_at for a pending scheduled post owned by user_id.
    Returns True if a row was updated."""
    conn = _connect()
    try:
        cur = conn.execute(
            'UPDATE scheduled_posts SET scheduled_at = ? WHERE id = ? AND user_id = ? AND status = ?',
            (scheduled_at, post_id, user_id, 'pending')
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ── Chat assistant persistence ────────────────────────────────────────────────

def add_chat_message(user_id, role, content):
    """role: 'user' or 'assistant'."""
    conn = _connect()
    try:
        created_at = _now_iso()
        conn.execute(
            'INSERT INTO chat_messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)',
            (user_id, role, content, created_at)
        )
        conn.commit()
        return created_at
    finally:
        conn.close()


def add_chat_turn(user_id, user_content, assistant_content, assistant_metadata=None):
    """Persist a complete chat turn in one transaction and return its expiry."""
    conn = _connect()
    try:
        user_created_at = _now_iso()
        assistant_created_at = _now_iso()
        conn.executemany(
            'INSERT INTO chat_messages '
            '(user_id, role, content, metadata_json, created_at) VALUES (?, ?, ?, ?, ?)',
            (
                (user_id, 'user', user_content, None, user_created_at),
                (
                    user_id, 'assistant', assistant_content,
                    json.dumps(assistant_metadata, ensure_ascii=False)
                    if assistant_metadata else None,
                    assistant_created_at,
                ),
            ),
        )
        conn.commit()
        expires_at = _chat_expiry(assistant_created_at)
        return {
            'lastMessageAt': assistant_created_at,
            'expiresAt': expires_at.isoformat() if expires_at else None,
        }
    finally:
        conn.close()


def _chat_expiry(last_message_at, inactivity_minutes=CHAT_INACTIVITY_MINUTES):
    if not last_message_at:
        return None
    last_message = datetime.fromisoformat(last_message_at)
    if last_message.tzinfo is None:
        last_message = last_message.replace(tzinfo=timezone.utc)
    return last_message.astimezone(timezone.utc) + timedelta(minutes=inactivity_minutes)


def get_chat_state(user_id, limit=15, inactivity_minutes=CHAT_INACTIVITY_MINUTES):
    """Return recent messages and delete the conversation after inactivity."""
    conn = _connect()
    try:
        latest = conn.execute(
            'SELECT MAX(created_at) AS last_message_at FROM chat_messages WHERE user_id = ?',
            (user_id,)
        ).fetchone()
        last_message_at = latest['last_message_at'] if latest else None
        expires_at = _chat_expiry(last_message_at, inactivity_minutes)

        if expires_at and datetime.now(timezone.utc) >= expires_at:
            conn.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
            conn.commit()
            return {'messages': [], 'lastMessageAt': None, 'expiresAt': None}

        rows = conn.execute(
            'SELECT role, content, metadata_json, created_at '
            'FROM chat_messages WHERE user_id = ? '
            'ORDER BY created_at DESC, id DESC LIMIT ?',
            (user_id, limit)
        ).fetchall()
        messages = []
        for row in reversed(rows):
            message = {
                'role': row['role'],
                'content': row['content'],
                'createdAt': row['created_at'],
            }
            if row['metadata_json']:
                try:
                    metadata = json.loads(row['metadata_json'])
                    if isinstance(metadata, dict):
                        message.update(metadata)
                except (TypeError, ValueError):
                    pass
            messages.append(message)
        return {
            'messages': messages,
            'lastMessageAt': last_message_at,
            'expiresAt': expires_at.isoformat() if expires_at else None,
        }
    finally:
        conn.close()


def get_recent_chat(user_id, limit=15):
    """Most recent turns, oldest-first (so they read in order into the API).
    Returns list of {'role','content'}."""
    state = get_chat_state(user_id, limit=limit)
    return [{'role': message['role'], 'content': message['content']} for message in state['messages']]


def clear_expired_chats(inactivity_minutes=CHAT_INACTIVITY_MINUTES):
    """Delete inactive conversations for all users; returns deleted row count."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=inactivity_minutes)).isoformat()
    conn = _connect()
    try:
        cursor = conn.execute(
            '''
            DELETE FROM chat_messages
            WHERE user_id IN (
                SELECT user_id
                FROM chat_messages
                GROUP BY user_id
                HAVING MAX(created_at) <= ?
            )
            ''',
            (cutoff,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def clear_chat(user_id):
    conn = _connect()
    try:
        conn.execute('DELETE FROM chat_messages WHERE user_id = ?', (user_id,))
        conn.commit()
    finally:
        conn.close()
