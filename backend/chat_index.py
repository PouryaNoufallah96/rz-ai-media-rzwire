"""Incremental SQLite vector index and hybrid retrieval for local chat RAG."""

import sqlite3
import struct
import sys
import threading
from datetime import datetime, timezone

import chat_embeddings
import chat_knowledge
import database


SEMANTIC_WEIGHT = 0.70
BM25_WEIGHT = 0.30
HIGH_CONFIDENCE = 0.78
MEDIUM_CONFIDENCE = 0.62

_LOCK = threading.RLock()
_INDEX = {}
_SYNC_THREAD = None
_STATUS = {
    'embedding': 'not_checked',
    'indexedChunks': 0,
    'totalChunks': len(chat_knowledge.knowledge_chunks()),
    'lastSuccessfulRebuild': None,
    'lastError': None,
}


def _connect():
    connection = sqlite3.connect(database.DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA busy_timeout = 5000')
    return connection


def _ensure_table(connection):
    connection.execute('''
        CREATE TABLE IF NOT EXISTS chat_knowledge_chunks (
            id TEXT PRIMARY KEY,
            knowledge_version TEXT NOT NULL,
            title TEXT NOT NULL,
            section TEXT NOT NULL,
            brand TEXT NOT NULL DEFAULT '',
            language TEXT NOT NULL,
            source_path TEXT NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            embedding BLOB NOT NULL,
            embedding_dim INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    connection.execute(
        'CREATE INDEX IF NOT EXISTS idx_chat_knowledge_version '
        'ON chat_knowledge_chunks (knowledge_version)'
    )


def _pack_vector(vector):
    return struct.pack(f'<{len(vector)}f', *vector)


def _unpack_vector(blob, dimension):
    expected = dimension * 4
    if not blob or len(blob) != expected:
        return None
    return struct.unpack(f'<{dimension}f', blob)


def _load_current_rows(connection, chunks):
    expected = {chunk['id']: chunk for chunk in chunks}
    loaded = {}
    rows = connection.execute('SELECT * FROM chat_knowledge_chunks').fetchall()
    for row in rows:
        chunk = expected.get(row['id'])
        if not chunk or row['content_hash'] != chunk['contentHash']:
            continue
        vector = _unpack_vector(row['embedding'], row['embedding_dim'])
        if not vector:
            continue
        loaded[row['id']] = {
            **chunk,
            'vector': vector,
        }
    with _LOCK:
        _INDEX.clear()
        _INDEX.update(loaded)
        _STATUS['indexedChunks'] = len(loaded)
        _STATUS['totalChunks'] = len(chunks)
    return loaded


def sync_index():
    """Embed only new/changed chunks; retain BM25 operation on any failure."""
    chunks = chat_knowledge.knowledge_chunks()
    connection = _connect()
    complete = True
    error_message = None
    try:
        _ensure_table(connection)
        connection.commit()
        existing = {
            row['id']: row
            for row in connection.execute(
                'SELECT id, content_hash, embedding_dim FROM chat_knowledge_chunks'
            ).fetchall()
        }
        now = datetime.now(timezone.utc).isoformat()
        for chunk in chunks:
            row = existing.get(chunk['id'])
            if (
                row
                and row['content_hash'] == chunk['contentHash']
                and row['embedding_dim'] == chat_embeddings.EMBEDDING_DIMENSION
            ):
                continue
            try:
                vector = chat_embeddings.embed_document(chunk['title'], chunk['content'])
            except chat_embeddings.EmbeddingUnavailable as exc:
                complete = False
                error_message = str(exc)
                break
            connection.execute(
                '''
                INSERT INTO chat_knowledge_chunks
                (id, knowledge_version, title, section, brand, language, source_path,
                 content, content_hash, embedding, embedding_dim, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    knowledge_version = excluded.knowledge_version,
                    title = excluded.title,
                    section = excluded.section,
                    brand = excluded.brand,
                    language = excluded.language,
                    source_path = excluded.source_path,
                    content = excluded.content,
                    content_hash = excluded.content_hash,
                    embedding = excluded.embedding,
                    embedding_dim = excluded.embedding_dim,
                    updated_at = excluded.updated_at
                ''',
                (
                    chunk['id'], chat_knowledge.knowledge_version(), chunk['title'],
                    chunk['section'], chunk['brand'], chunk['language'],
                    chunk['sourcePath'], chunk['content'], chunk['contentHash'],
                    _pack_vector(vector), len(vector), now,
                ),
            )
            connection.commit()

        valid_ids = {chunk['id'] for chunk in chunks}
        stale_ids = [chunk_id for chunk_id in existing if chunk_id not in valid_ids]
        if stale_ids:
            connection.executemany(
                'DELETE FROM chat_knowledge_chunks WHERE id = ?',
                ((chunk_id,) for chunk_id in stale_ids),
            )
            connection.commit()

        loaded = _load_current_rows(connection, chunks)
        if len(loaded) != len(chunks):
            complete = False
            error_message = error_message or (
                f'Index contains {len(loaded)} of {len(chunks)} current chunks'
            )
        with _LOCK:
            _STATUS['embedding'] = 'ok' if complete else 'unavailable'
            _STATUS['lastError'] = error_message
            if complete:
                _STATUS['lastSuccessfulRebuild'] = now
        if error_message:
            print(f'[chat_index] {error_message}; BM25 fallback remains active', file=sys.stderr)
        else:
            print(f'[chat_index] local vector index ready ({len(loaded)} chunks)', file=sys.stderr)
        return complete
    finally:
        connection.close()


def _sync_worker():
    global _SYNC_THREAD
    try:
        sync_index()
    except Exception as exc:  # noqa: BLE001
        with _LOCK:
            _STATUS['embedding'] = 'unavailable'
            _STATUS['lastError'] = str(exc)
        print(f'[chat_index] background rebuild failed: {exc}', file=sys.stderr)
    finally:
        with _LOCK:
            _SYNC_THREAD = None


def start_background_sync():
    global _SYNC_THREAD
    with _LOCK:
        if _SYNC_THREAD and _SYNC_THREAD.is_alive():
            return
        _SYNC_THREAD = threading.Thread(
            target=_sync_worker,
            name='chat-embedding-index',
            daemon=True,
        )
        _SYNC_THREAD.start()


def _cosine_for_normalized(left, right):
    # llama.cpp is asked for L2-normalized vectors, so the dot product is cosine.
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right))))


def retrieve(question, k=3, brand_hint=None):
    lexical = chat_knowledge.bm25_results(question, k=30, brand_hint=brand_hint)
    lexical_by_id = {item['id']: item for item in lexical}
    brand = chat_knowledge.detect_brand(question) or brand_hint
    query_vector = None
    try:
        query_vector = chat_embeddings.embed_query(question)
        with _LOCK:
            _STATUS['embedding'] = 'ok'
            _STATUS['lastError'] = None
    except chat_embeddings.EmbeddingUnavailable as exc:
        with _LOCK:
            _STATUS['embedding'] = 'unavailable'
            _STATUS['lastError'] = str(exc)

    with _LOCK:
        vectors = list(_INDEX.values())
    candidates = {}
    for item in vectors:
        if brand and item['brand'] not in ('', brand):
            continue
        candidates[item['id']] = dict(item)
    for item in lexical:
        candidates.setdefault(item['id'], dict(item))

    ranked = []
    for chunk_id, item in candidates.items():
        semantic_score = 0.0
        if query_vector is not None and item.get('vector'):
            semantic_score = _cosine_for_normalized(query_vector, item['vector'])
        bm25_score = lexical_by_id.get(chunk_id, {}).get('bm25Score', 0.0)
        combined = SEMANTIC_WEIGHT * semantic_score + BM25_WEIGHT * bm25_score
        result = {key: value for key, value in item.items() if key != 'vector'}
        result.update({
            'semanticScore': semantic_score,
            'bm25Score': bm25_score,
            'score': combined,
            'embeddingUsed': query_vector is not None and bool(item.get('vector')),
        })
        ranked.append(result)
    ranked.sort(key=lambda item: item['score'], reverse=True)
    return ranked[:k]


def confidence_for(score):
    if score >= HIGH_CONFIDENCE:
        return 'high'
    if score >= MEDIUM_CONFIDENCE:
        return 'medium'
    return 'low'


def status(check_service=False):
    with _LOCK:
        snapshot = dict(_STATUS)
        building = bool(_SYNC_THREAD and _SYNC_THREAD.is_alive())
    if check_service:
        service = chat_embeddings.health()
        snapshot['embedding'] = service['status']
        snapshot['embeddingLatencyMs'] = service['latencyMs']
    snapshot.update({
        'mode': 'local_rag',
        'knowledgeVersion': chat_knowledge.knowledge_version(),
        'building': building,
    })
    return snapshot


def reset_for_tests():
    """Clear process-local state after a test changes the SQLite path."""
    with _LOCK:
        _INDEX.clear()
        _STATUS.update({
            'embedding': 'not_checked',
            'indexedChunks': 0,
            'totalChunks': len(chat_knowledge.knowledge_chunks()),
            'lastSuccessfulRebuild': None,
            'lastError': None,
        })
