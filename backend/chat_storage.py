"""SQLite storage for approved chatbot FAQs, answer cache, and question stats."""
import json
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime, timezone

import database
from chat_faq_data import FAQ_SEEDS as APPROVED_FAQ_SEEDS


_INIT_LOCK = threading.Lock()
_INITIALIZED_DB = None
_PERMANENT_EXPIRY = '9999-12-31T23:59:59+00:00'
_FAQ_MATCH_STOPWORDS = {
    'a', 'about', 'an', 'and', 'are', 'can', 'do', 'does', 'for', 'how', 'i', 'in',
    'is', 'it', 'me', 'my', 'of', 'on', 'or', 'the', 'this', 'to', 'what',
    'tell', 'where', 'which', 'with', 'you', 'your',
    'Ø§Ø²', 'Ø§Ø³Øª', 'Ø§ÛŒÙ†', 'Ø¨Ø§', 'Ø¨Ø±Ø§ÛŒ', 'Ø¨Ù‡', 'Ú†Ù‡', 'Ú†Ú¯ÙˆÙ†Ù‡', 'Ú†ÛŒØ³Øª', 'Ø¯Ø±',
    'Ø±Ø§', 'Ø±ÙˆÛŒ', 'Ù…Ù†', 'Ù…ÛŒ', 'Ùˆ', 'ÛŒØ§', 'Ú©Ø¬Ø§', 'Ú©Ù‡',
}
_FAQ_CONTEXT_ONLY_PHRASES = {'mgc coin', 'ranking platform', 'oasis coin', 'jewelry coin'}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _supported_language(value):
    return 'fa' if value == 'fa' else 'en'


def normalize_question(value):
    text = unicodedata.normalize('NFKC', value or '').lower().strip()
    replacements = {
        'rz wire': 'rzwire',
        'metagamescoin': 'meta games coin',
        'ranking.game': 'ranking platform',
        'jewellery coin': 'jewelry coin',
        'jewellery token': 'jewelry token',
        'twitter': 'x',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'[^\w\u0600-\u06ff]+', ' ', text, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', text).strip()


_FAQ_SEEDS = APPROVED_FAQ_SEEDS


def _connect():
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout = 5000')
    return conn


def ensure_tables():
    global _INITIALIZED_DB
    db_key = str(database.DB_PATH.resolve())
    if _INITIALIZED_DB == db_key:
        return
    with _INIT_LOCK:
        if _INITIALIZED_DB == db_key:
            return
        conn = _connect()
        try:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_faq (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    canonical_question TEXT NOT NULL,
                    normalized_question TEXT NOT NULL,
                    aliases_json TEXT NOT NULL DEFAULT '[]',
                    keywords_json TEXT NOT NULL DEFAULT '[]',
                    answer TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'en',
                    brand TEXT NOT NULL DEFAULT '',
                    approved INTEGER NOT NULL DEFAULT 1,
                    active INTEGER NOT NULL DEFAULT 1,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    priority INTEGER NOT NULL DEFAULT 50,
                    managed_key TEXT,
                    last_used_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(normalized_question, language, brand)
                )
            ''')
            faq_columns = {
                row['name'] for row in conn.execute('PRAGMA table_info(chat_faq)').fetchall()
            }
            if 'keywords_json' not in faq_columns:
                conn.execute("ALTER TABLE chat_faq ADD COLUMN keywords_json TEXT NOT NULL DEFAULT '[]'")
            if 'priority' not in faq_columns:
                conn.execute('ALTER TABLE chat_faq ADD COLUMN priority INTEGER NOT NULL DEFAULT 50')
            if 'managed_key' not in faq_columns:
                conn.execute('ALTER TABLE chat_faq ADD COLUMN managed_key TEXT')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_answer_cache (
                    cache_key TEXT PRIMARY KEY,
                    normalized_question TEXT NOT NULL,
                    context_key TEXT NOT NULL,
                    language TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    knowledge_version TEXT NOT NULL,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_chat_cache_expiry ON chat_answer_cache (expires_at)')
            # Migrate every existing temporary cache entry to permanent storage.
            conn.execute(
                'UPDATE chat_answer_cache SET expires_at = ? WHERE expires_at <> ?',
                (_PERMANENT_EXPIRY, _PERMANENT_EXPIRY),
            )
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_question_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_question TEXT NOT NULL,
                    example_question TEXT NOT NULL,
                    context_key TEXT NOT NULL,
                    language TEXT NOT NULL,
                    ask_count INTEGER NOT NULL DEFAULT 0,
                    ai_count INTEGER NOT NULL DEFAULT 0,
                    faq_hit_count INTEGER NOT NULL DEFAULT 0,
                    cache_hit_count INTEGER NOT NULL DEFAULT 0,
                    local_reply_count INTEGER NOT NULL DEFAULT 0,
                    last_source TEXT NOT NULL,
                    first_asked_at TEXT NOT NULL,
                    last_asked_at TEXT NOT NULL,
                    UNIQUE(normalized_question, context_key, language)
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_term_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_term TEXT NOT NULL,
                    target_term TEXT NOT NULL,
                    language TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    seen_count INTEGER NOT NULL DEFAULT 1,
                    approved INTEGER NOT NULL DEFAULT 0,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    UNIQUE(source_term, target_term, language)
                )
            ''')
            now = _now_iso()
            conn.execute('UPDATE chat_faq SET active = 0 WHERE managed_key IS NOT NULL')
            for faq in _FAQ_SEEDS:
                conn.execute(
                    '''
                    INSERT INTO chat_faq
                    (canonical_question, normalized_question, aliases_json, keywords_json,
                     answer, language, brand, approved, active, priority, managed_key,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, '', 1, 1, ?, ?, ?, ?)
                    ON CONFLICT(normalized_question, language, brand) DO UPDATE SET
                        canonical_question = excluded.canonical_question,
                        aliases_json = excluded.aliases_json,
                        keywords_json = excluded.keywords_json,
                        answer = excluded.answer,
                        approved = 1,
                        active = 1,
                        priority = excluded.priority,
                        managed_key = excluded.managed_key,
                        updated_at = excluded.updated_at
                    ''',
                    (
                        faq['question'], normalize_question(faq['question']),
                        json.dumps(faq.get('aliases', []), ensure_ascii=False),
                        json.dumps(faq.get('keywords', []), ensure_ascii=False),
                        faq['answer'], faq['language'], faq.get('priority', 50),
                        faq['managedKey'], now, now,
                    ),
                )
            conn.commit()
            _INITIALIZED_DB = db_key
        finally:
            conn.close()


def find_faq(normalized_question, language, brand=''):
    ensure_tables()
    language = _supported_language(language)
    conn = _connect()
    try:
        rows = conn.execute(
            '''
            SELECT * FROM chat_faq
            WHERE active = 1 AND approved = 1 AND language = ? AND brand IN ('', ?)
            ORDER BY priority DESC, CASE WHEN brand = ? THEN 0 ELSE 1 END, id
            ''',
            (language, brand, brand),
        ).fetchall()
        question_tokens = sorted(normalized_question.split())
        question_set = set(question_tokens)
        significant_question_set = question_set - _FAQ_MATCH_STOPWORDS
        best = None
        for row in rows:
            candidates = [row['normalized_question']]
            candidates.extend(normalize_question(alias) for alias in json.loads(row['aliases_json'] or '[]'))
            if normalized_question in candidates or any(
                question_tokens and question_tokens == sorted(candidate.split())
                for candidate in candidates
            ):
                best = (float('inf'), row)
                break

            score = row['priority'] / 100.0
            matched_tokens = set()
            strong_phrase = False
            single_keyword_match = False
            for keyword in json.loads(row['keywords_json'] or '[]'):
                phrase = normalize_question(keyword)
                phrase_tokens = set(phrase.split())
                if not phrase_tokens:
                    continue
                significant_phrase_tokens = phrase_tokens - _FAQ_MATCH_STOPWORDS
                if phrase in _FAQ_CONTEXT_ONLY_PHRASES:
                    if significant_question_set == significant_phrase_tokens:
                        score += 6 + len(phrase_tokens)
                        strong_phrase = True
                    continue
                overlap = significant_question_set & significant_phrase_tokens
                matched_tokens.update(overlap)
                if (
                    len(significant_phrase_tokens) == 1
                    and significant_question_set == significant_phrase_tokens
                ):
                    single_keyword_match = True
                if phrase in normalized_question:
                    score += 6 + len(phrase_tokens)
                    strong_phrase = strong_phrase or len(phrase_tokens) >= 2
                else:
                    score += len(overlap)

            qualifies = strong_phrase or len(matched_tokens) >= 2 or single_keyword_match
            if qualifies and (best is None or score > best[0]):
                best = (score, row)

        if not best:
            return None
        row = best[1]
        conn.execute(
            'UPDATE chat_faq SET hit_count = hit_count + 1, last_used_at = ? WHERE id = ?',
            (_now_iso(), row['id']),
        )
        conn.commit()
        return {'id': row['id'], 'answer': row['answer']}
    finally:
        conn.close()


def get_cached_answer(cache_key, knowledge_version):
    ensure_tables()
    now = _now_iso()
    conn = _connect()
    try:
        row = conn.execute(
            'SELECT answer FROM chat_answer_cache WHERE cache_key = ? AND knowledge_version = ?',
            (cache_key, knowledge_version),
        ).fetchone()
        if not row:
            conn.commit()
            return None
        conn.execute(
            'UPDATE chat_answer_cache SET hit_count = hit_count + 1, updated_at = ? WHERE cache_key = ?',
            (now, cache_key),
        )
        conn.commit()
        return row['answer']
    finally:
        conn.close()


def save_cached_answer(cache_key, normalized_question, context_key, language, answer,
                       knowledge_version):
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO chat_answer_cache
            (cache_key, normalized_question, context_key, language, answer, knowledge_version,
             expires_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                answer = excluded.answer,
                knowledge_version = excluded.knowledge_version,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            ''',
            (
                cache_key, normalized_question, context_key, language, answer,
                knowledge_version, _PERMANENT_EXPIRY, now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_question(normalized_question, example_question, context_key, language, source):
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    counters = {
        'ai': (1, 0, 0, 0),
        'faq': (0, 1, 0, 0),
        'cache': (0, 0, 1, 0),
        'local_policy': (0, 0, 0, 1),
    }
    ai, faq, cache, local = counters.get(source, (0, 0, 0, 1))
    conn = _connect()
    try:
        conn.execute(
            '''
            INSERT INTO chat_question_stats
            (normalized_question, example_question, context_key, language, ask_count,
             ai_count, faq_hit_count, cache_hit_count, local_reply_count, last_source,
             first_asked_at, last_asked_at)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(normalized_question, context_key, language) DO UPDATE SET
                example_question = excluded.example_question,
                ask_count = ask_count + 1,
                ai_count = ai_count + excluded.ai_count,
                faq_hit_count = faq_hit_count + excluded.faq_hit_count,
                cache_hit_count = cache_hit_count + excluded.cache_hit_count,
                local_reply_count = local_reply_count + excluded.local_reply_count,
                last_source = excluded.last_source,
                last_asked_at = excluded.last_asked_at
            ''',
            (
                normalized_question, example_question[:500], context_key, language,
                ai, faq, cache, local, source, now, now,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def record_corrections(corrections, language):
    if not corrections:
        return
    ensure_tables()
    language = _supported_language(language)
    now = _now_iso()
    conn = _connect()
    try:
        for correction in corrections:
            conn.execute(
                '''
                INSERT INTO chat_term_corrections
                (source_term, target_term, language, kind, confidence, seen_count,
                 approved, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(source_term, target_term, language) DO UPDATE SET
                    kind = excluded.kind,
                    confidence = excluded.confidence,
                    seen_count = seen_count + 1,
                    last_seen_at = excluded.last_seen_at
                ''',
                (
                    correction['source'], correction['target'], language,
                    correction['kind'], correction['confidence'],
                    1 if correction['kind'] == 'phonetic' else 0, now, now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def top_questions(limit=50):
    ensure_tables()
    conn = _connect()
    try:
        rows = conn.execute(
            'SELECT * FROM chat_question_stats ORDER BY ask_count DESC, last_asked_at DESC LIMIT ?',
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


