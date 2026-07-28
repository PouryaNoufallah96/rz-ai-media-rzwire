"""
OpenAI Embedding filter pipeline — 7 stages.
Public entry point: run_pipeline(articles, selected_media, topics, recency_hours) -> dict
"""
import math
import re
import sys
import threading
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import numpy as np

from .config import (
    BRAND_CONFIGS, BRAND_KEYS, BRAND_NAME_TO_KEY,
    DEDUP_COSINE, SOURCE_AUTHORITY, DEFAULT_AUTHORITY,
    TOP_N_PER_BRAND, VIRALITY_POWER_WORDS, VIRALITY_ENTITIES,
)
from .embedder import Embedder

# ── Module-level singletons (initialised once on import) ──────────────────────
_embedder: Optional[Embedder] = None
_anchor_vecs: Optional[dict]  = None   # brand_key → (n_phrases, 1536) array
_embedder_lock    = threading.Lock()
_anchor_vecs_lock = threading.Lock()

# Topic-vector cache: user keyword string → (1, 1536) L2-normalised vector.
# Lets user-entered keywords semantically influence the ranking. Cache is keyed
# by the exact topic string so re-analyzing with the same keywords is instant.
_topic_vecs: dict[str, np.ndarray] = {}
_topic_vecs_lock = threading.Lock()


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                _embedder = Embedder()
    return _embedder


def _get_anchor_vecs() -> dict:
    global _anchor_vecs
    if _anchor_vecs is not None:
        return _anchor_vecs
    with _anchor_vecs_lock:
        if _anchor_vecs is not None:
            return _anchor_vecs
        emb = _get_embedder()
        vecs = {}
        for key, cfg in BRAND_CONFIGS.items():
            phrases = cfg['anchor_phrases']
            mat, _, _ = emb.embed(phrases)
            vecs[key] = mat   # (n_phrases, 1536), already L2-normalised
        _anchor_vecs = vecs
    return _anchor_vecs


def _get_topic_vec(topic: str) -> Optional[np.ndarray]:
    """Embed the user's keyword string once and cache it by the exact string.

    Returns a (1, 1536) L2-normalised vector, or None when the topic is empty
    (no keywords entered → ranking falls back to the no-topic weighting).
    Uses the same double-checked-locking pattern as _get_anchor_vecs.
    """
    topic = (topic or '').strip()
    if not topic:
        return None
    if topic in _topic_vecs:
        return _topic_vecs[topic]
    with _topic_vecs_lock:
        if topic in _topic_vecs:
            return _topic_vecs[topic]
        emb = _get_embedder()
        mat, _, _ = emb.embed([topic])   # one phrase → (1, 1536), already L2-normalised
        vec = mat[0:1]                   # keep 2D so vec @ vec.T works downstream
        _topic_vecs[topic] = vec
        return vec


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    # RFC-2822 (standard RSS)
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc)
    except Exception:
        pass
    # ISO variants
    for fmt in ('%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass
    return None


def _normalise_url(url: str) -> str:
    try:
        p = urllib.parse.urlparse(url.lower().strip())
        qs = urllib.parse.parse_qs(p.query, keep_blank_values=False)
        drop = {'utm_source', 'utm_medium', 'utm_campaign', 'utm_content',
                'utm_term', 'fbclid', 'gclid', 'ref', 'source'}
        qs = {k: v for k, v in qs.items() if k not in drop}
        clean_q = urllib.parse.urlencode(qs, doseq=True)
        path = p.path.rstrip('/')
        return urllib.parse.urlunparse((p.scheme, p.netloc, path, '', clean_q, ''))
    except Exception:
        return url.lower().strip()


def _url_slug(url: str) -> str:
    try:
        segs = [s for s in urllib.parse.urlparse(url).path.split('/') if s]
        return segs[-1] if segs else ''
    except Exception:
        return ''


def _score_freshness(pub_dt: datetime) -> float:
    age_h = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
    if age_h < 0:   return 50.0
    if age_h < 1:   return 100.0
    if age_h < 2:   return 95.0
    if age_h < 4:   return 88.0
    if age_h < 6:   return 80.0
    if age_h < 12:  return 68.0
    if age_h < 24:  return 50.0
    if age_h < 36:  return 32.0
    if age_h < 48:  return 20.0
    return 8.0


def _score_virality(title: str, desc: str) -> float:
    title_l = title.lower()
    full_l  = (title + ' ' + desc).lower()
    score   = 0.0
    for w in VIRALITY_POWER_WORDS:
        if w in title_l:      score += 15 * 1.5
        elif w in full_l:     score += 15 * 0.4
    for e in VIRALITY_ENTITIES:
        if e in title_l:      score += 12
    if re.search(r'\d+(\.\d+)?%', title):      score += 12
    if re.search(r'\$[\d,\.]+', title):        score += 10
    if re.search(r'\b(billion|trillion|million)\b', title, re.I): score += 14
    return min(100.0, max(0.0, score))


def _has_value_signal(text: str) -> bool:
    if re.search(r'[\$€£]\d', text):             return True
    if re.search(r'\d+(\.\d+)?%', text):         return True
    if re.search(r'\b\d[\d,\.]*\b', text):       return True
    if re.search(r'\b(price|forecast|predict|target|value|cost|worth|revenue|volume|tvl|market cap)\b',
                 text, re.I):
        return True
    return False


def _score_topic_fit(title: str, desc: str, topics: str) -> float:
    if not topics.strip():
        return 0.0
    kws = [t.strip().lower() for t in re.split(r'[,;]+', topics) if t.strip()]
    if not kws:
        return 0.0
    title_l = title.lower()
    desc_l  = desc.lower()
    hits = 0
    for kw in kws:
        if kw in title_l: hits += 2
        elif kw in desc_l: hits += 1
    return min(100.0, round(hits / (len(kws) * 2) * 100))


# ── Stage 6 final score formula ───────────────────────────────────────────────

def _final_score(media_fit: float, cluster_size: int, virality: float,
                 freshness: float, authority: float, source_bias: bool,
                 topic_relevance: float = 0.0, has_topic: bool = False) -> float:
    """Weighted ranking score. Weights always sum to 1.0 (excluding the bias bonus).

    When the user entered keywords (has_topic=True), 15% of the weight goes to a
    SEMANTIC topic_relevance term and media_fit is reduced 0.40→0.25 — so on-topic
    articles can leapfrog higher-brand-fit ones. When no keywords are entered,
    the 15% is redistributed proportionally across the other factors, keeping
    their *relative* importance identical to the original formula (×1/0.85).
    """
    cb = math.log1p(cluster_size) / math.log1p(12) * 100
    if has_topic:
        # Keywords present: 15% of the weight goes to topic_relevance, media_fit
        # reduced 0.40→0.25 so an on-topic article can leapfrog a higher-fit one.
        # (media_fit 0.25 + cluster 0.20 + vir 0.18 + fresh 0.15 + auth 0.07 + topic 0.15 = 1.0)
        s = (media_fit   * 0.25
             + cb        * 0.20
             + virality  * 0.18
             + freshness * 0.15
             + authority * 0.07
             + topic_relevance * 0.15)
    else:
        # No keywords: use the original weights unchanged. They already sum to
        # 1.0 (0.40+0.20+0.18+0.15+0.07), so empty-topics behavior is identical
        # to today — no dead weight, no rescaling needed.
        s = (media_fit   * 0.40
             + cb        * 0.20
             + virality  * 0.18
             + freshness * 0.15
             + authority * 0.07)
    s += (3 if source_bias else 0)
    return round(s, 2)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(articles: list[dict], selected_media: list[str],
                 topics: str, recency_hours: int) -> dict:
    """
    Run all 7 stages and return:
      { shortlist, stats, all_tracked }
    """
    # Map display names to brand keys; ignore unknown brands
    selected_keys = [BRAND_NAME_TO_KEY[m] for m in selected_media
                     if m in BRAND_NAME_TO_KEY]
    if not selected_keys:
        return {'shortlist': [], 'stats': {}, 'all_tracked': []}

    now       = datetime.now(timezone.utc)
    cutoff_dt = datetime.fromtimestamp(
        now.timestamp() - recency_hours * 3600, tz=timezone.utc)

    # Resolve the user's keyword string to a single semantic vector once.
    # None when no keywords entered — ranking then uses the no-topic weighting.
    topic_vec = _get_topic_vec(topics)

    all_tracked: list[dict] = []
    stats = {
        'fetched':           len(articles),
        'dropped_date':      0,
        'dropped_dup_cheap': 0,
        'dropped_clustered': 0,
        'no_media_fit':      0,
        'cap_exceeded':      0,
        'embedded':          0,
        'api_calls':         0,
        'cached_hits':       0,
    }
    for key in selected_keys:
        stats[f'brand_{key}'] = 0

    # ── Stage 1: Date gate ────────────────────────────────────────────────────
    stage1_pass: list[dict] = []
    for art in articles:
        raw = art.get('pubDate') or art.get('pub_date_raw') or ''
        dt  = _parse_date(raw)
        if dt is None:
            all_tracked.append({**art, '_pipelineStatus': 'no_date',
                                 '_scores': None, '_routing': None})
            stats['dropped_date'] += 1
            continue
        if dt < cutoff_dt:
            all_tracked.append({**art, '_pipelineStatus': 'out_of_window',
                                 '_scores': None, '_routing': None,
                                 'pub_date': dt.isoformat()})
            stats['dropped_date'] += 1
            continue
        art['pub_date'] = dt.isoformat()   # always a string — no datetime objects on art
        stage1_pass.append(art)

    # ── Stage 2: Cheap de-duplication ─────────────────────────────────────────
    seen_urls: set  = set()
    seen_norms: set = set()
    seen_slugs: dict = {}   # (source, slug) → title
    stage2_pass: list[dict] = []

    for art in stage1_pass:
        url  = (art.get('link') or art.get('url') or '').strip()
        norm = _normalise_url(url) if url else ''
        slug = _url_slug(url)
        src  = art.get('source', '')

        dup = False
        if url  and url  in seen_urls:  dup = True
        if norm and norm in seen_norms: dup = True
        if slug and (src, slug) in seen_slugs: dup = True

        if dup:
            all_tracked.append({**art, '_pipelineStatus': 'duplicate',
                                 '_scores': None, '_routing': None})
            stats['dropped_dup_cheap'] += 1
            continue

        if url:  seen_urls.add(url)
        if norm: seen_norms.add(norm)
        if slug: seen_slugs[(src, slug)] = art.get('title', '')
        stage2_pass.append(art)

    if not stage2_pass:
        return {'shortlist': [], 'stats': stats, 'all_tracked': all_tracked}

    # ── Stage 3: Embed ────────────────────────────────────────────────────────
    emb   = _get_embedder()
    texts = [
        (art.get('title') or '') + '. ' + (art.get('desc') or '')[:400]
        for art in stage2_pass
    ]
    vecs, api_calls, cache_hits = emb.embed(texts)
    stats['embedded']    = len(stage2_pass)
    stats['api_calls']   = api_calls
    stats['cached_hits'] = cache_hits

    for i, art in enumerate(stage2_pass):
        art['_vec'] = vecs[i]

    # ── Stage 4: Semantic event clustering ────────────────────────────────────
    anchor_vecs = _get_anchor_vecs()
    clusters: list[dict] = []   # each: { centroid, members, best }

    def _authority(art):
        return SOURCE_AUTHORITY.get(art.get('source', ''), DEFAULT_AUTHORITY)

    def _freshness(art):
        dt = _parse_date(art.get('pub_date', ''))
        return _score_freshness(dt) if dt else 50.0

    for art in stage2_pass:
        vec = art['_vec']
        best_cluster = None
        best_cos     = -1.0
        for cl in clusters:
            cos = float(vec @ cl['centroid'])
            if cos > best_cos:
                best_cos     = cos
                best_cluster = cl
        if best_cluster is not None and best_cos >= DEDUP_COSINE:
            best_cluster['members'].append(art)
            # recompute centroid as re-normalised mean
            stack = np.vstack([m['_vec'] for m in best_cluster['members']])
            mean  = stack.mean(axis=0)
            norm  = np.linalg.norm(mean)
            best_cluster['centroid'] = mean / norm if norm > 0 else mean
        else:
            clusters.append({'centroid': vec, 'members': [art]})

    stage4_pass: list[dict] = []
    for cl in clusters:
        members = cl['members']
        if len(members) == 1:
            members[0]['_cluster_size'] = 1
            stage4_pass.append(members[0])
            continue
        # Keep best by authority×0.4 + freshness×0.35
        best = max(members,
                   key=lambda a: _authority(a) * 0.4 + _freshness(a) * 0.35)
        best['_cluster_size'] = len(members)
        stage4_pass.append(best)
        for loser in members:
            if loser is not best:
                all_tracked.append({**loser,
                                     '_pipelineStatus': 'clustered_out',
                                     '_scores': None, '_routing': None})
                stats['dropped_clustered'] += 1

    # ── Stage 5: Media routing ────────────────────────────────────────────────
    stage5_pass: list[dict] = []
    for art in stage4_pass:
        vec   = art['_vec']
        text  = (art.get('title') or '') + ' ' + (art.get('desc') or '')
        # Semantic topic relevance: max cosine(article_vec, topic_vec) × 100.
        # Same operation as media_fit, against the user-keyword vector instead
        # of brand anchors. Stashed on the article so Stage 6 can read it once.
        if topic_vec is not None:
            art['_topic_rel'] = float(np.max(vec @ topic_vec.T)) * 100
        brand_scores: dict[str, float] = {}

        for key in selected_keys:
            cfg        = BRAND_CONFIGS[key]
            avecs      = anchor_vecs[key]
            media_fit  = float(np.max(vec @ avecs.T)) * 100

            # Optional value gate for profiles that require quantified evidence.
            if cfg['value_gate'] and not _has_value_signal(text):
                brand_scores[key] = 0.0
                continue

            if media_fit >= cfg['threshold'] * 100:
                brand_scores[key] = media_fit

        if not brand_scores:
            all_tracked.append({**art, '_pipelineStatus': 'no_media_fit',
                                 '_scores': None, '_routing': None})
            stats['no_media_fit'] += 1
            continue

        art['_brand_scores'] = brand_scores
        # Primary = highest scoring brand
        sorted_brands = sorted(brand_scores.items(), key=lambda x: x[1], reverse=True)
        art['_primary_brand']   = sorted_brands[0][0]
        art['_secondary_brand'] = sorted_brands[1][0] if len(sorted_brands) > 1 else None
        stage5_pass.append(art)

    # ── Stage 6: Rank within each brand → top TOP_N_PER_BRAND ────────────────
    brand_buckets: dict[str, list] = {key: [] for key in selected_keys}
    for art in stage5_pass:
        for key, fit in art['_brand_scores'].items():
            brand_buckets[key].append((art, fit))

    selected_arts: list[dict] = []
    selected_titles: set      = set()

    for key in selected_keys:
        cfg     = BRAND_CONFIGS[key]
        bucket  = brand_buckets[key]
        scored  = []
        for art, media_fit in bucket:
            auth      = _authority(art)
            fresh     = _freshness(art)
            vir       = _score_virality(art.get('title', ''), art.get('desc', ''))
            bias      = art.get('source', '') in cfg['source_bias']
            cs        = art.get('_cluster_size', 1)
            trel      = art.get('_topic_rel', 0.0)
            fscore    = _final_score(media_fit, cs, vir, fresh, auth, bias,
                                     topic_relevance=trel,
                                     has_topic=(topic_vec is not None))
            scored.append((art, media_fit, fscore, vir, fresh, auth))

        scored.sort(key=lambda x: x[2], reverse=True)
        count = 0
        for art, media_fit, fscore, vir, fresh, auth in scored:
            if count >= TOP_N_PER_BRAND:
                if art.get('title', '') not in selected_titles:
                    all_tracked.append({**art, '_pipelineStatus': 'cap_exceeded',
                                         '_scores': None, '_routing': None})
                    stats['cap_exceeded'] += 1
                continue
            if art.get('title', '') not in selected_titles:
                art.setdefault('_final_scores', {})[key] = {
                    'media_fit':      round(media_fit, 1),
                    'final':          fscore,
                    'virality':       round(vir, 1),
                    'freshness':      round(fresh, 1),
                    'authority':      auth,
                    'topic_relevance': round(art.get('_topic_rel', 0.0), 1),
                    'user_topic':     round(_score_topic_fit(
                        art.get('title', ''), art.get('desc', ''), topics), 1),
                }
                selected_arts.append((art, key, media_fit, fscore, vir, fresh, auth))
                selected_titles.add(art.get('title', ''))
                stats[f'brand_{key}'] += 1
                count += 1

    # ── Stage 7: Build output payload ─────────────────────────────────────────
    # De-duplicate: one entry per unique article, _brands lists all brands it joined
    seen_in_payload: dict[str, dict] = {}   # title → payload entry
    for art, brand_key, media_fit, fscore, vir, fresh, auth in selected_arts:
        title = art.get('title', '')
        if title not in seen_in_payload:
            ut = _score_topic_fit(art.get('title', ''), art.get('desc', ''), topics)
            conf = round((media_fit + ut + fresh + auth) / 4)
            primary_name   = BRAND_CONFIGS[art['_primary_brand']]['name']
            secondary_name = (BRAND_CONFIGS[art['_secondary_brand']]['name']
                              if art.get('_secondary_brand') else '')
            entry = {
                'title':    title,
                'source':   art.get('source', ''),
                'link':     art.get('link') or art.get('url', ''),
                'desc':     (art.get('desc') or '')[:220],
                'pub_date': art.get('pub_date', ''),
                'scores': {
                    'final':          round(fscore),
                    'virality':       round(vir),
                    'freshness':      round(fresh),
                    'authority':      round(auth),
                    'topicRelevance': round(art.get('_topic_rel', 0.0)),
                    'userTopic':      round(ut),
                    'confidence':     conf,
                },
                'routing': {
                    'primary_media':   primary_name,
                    'secondary_media': secondary_name,
                },
                '_brands': [BRAND_CONFIGS[brand_key]['name']],
                '_cluster_size': art.get('_cluster_size', 1),
            }
            seen_in_payload[title] = entry
            all_tracked.append({**art, '_pipelineStatus': 'selected',
                                 '_scores': entry['scores'],
                                 '_routing': entry['routing']})
        else:
            # Article already in payload under another brand — just append brand
            seen_in_payload[title]['_brands'].append(
                BRAND_CONFIGS[brand_key]['name'])

    shortlist = list(seen_in_payload.values())
    for i, item in enumerate(shortlist):
        item['input_index'] = i

    # Strip internal non-JSON-serialisable fields (_vec, _dt, _brand_scores, etc.)
    _INTERNAL = {'_vec', '_brand_scores', '_primary_brand',
                 '_secondary_brand', '_final_scores', '_urlSlug', '_entities',
                 '_topic_rel'}

    def _clean(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in _INTERNAL}

    shortlist    = [_clean(a) for a in shortlist]
    all_tracked  = [_clean(a) for a in all_tracked]

    return {
        'shortlist':   shortlist,
        'stats':       stats,
        'all_tracked': all_tracked,
    }
