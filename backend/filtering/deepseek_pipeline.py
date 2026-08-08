"""
DeepSeek Pre-Process filter pipeline.
Uses DeepSeek V4 Flash (via OpenRouter) as the editorial router:
  - Date gate + cheap URL dedup (free, deterministic)
  - Single DeepSeek request: semantic dedup + brand clustering + ranking
  - Returns same {shortlist, stats, all_tracked} shape as run_pipeline()
"""
import sys
import urllib.parse
from datetime import datetime, timezone

from .config import (
    BRAND_EDITORIAL_DESCS, BRAND_NAME_TO_KEY, BRAND_CONFIGS,
    SOURCE_AUTHORITY, DEFAULT_AUTHORITY, TOP_N_PER_BRAND,
)
from .pipeline import _parse_date   # reuse existing date parser

DEEPSEEK_MODEL    = 'deepseek/deepseek-v4-flash'
BATCH_SIZE        = 60      # max articles per DeepSeek request
MAX_BRANDS_PER_ART = 2      # an article can land in at most this many brands


# ── Helpers (reuse pipeline.py utilities via import) ─────────────────────────

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


def _age_label(pub_date_iso: str) -> str:
    try:
        dt  = _parse_date(pub_date_iso)
        if dt is None:
            return ''
        age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        if age_h < 1:   return f'{int(age_h*60)}m'
        if age_h < 24:  return f'{age_h:.0f}h'
        return f'{age_h/24:.0f}d'
    except Exception:
        return ''


def _build_prompt(article_lines: list[str], selected_media: list[str],
                  topics: str) -> tuple[str, str]:
    """Return (system_msg, user_msg) for DeepSeek."""
    brand_section = ''
    for name in selected_media:
        desc = BRAND_EDITORIAL_DESCS.get(name, '')
        if desc:
            brand_section += f'\n\n[{name}]\n{desc}'

    topic_line = (f'\nTOPIC FOCUS: Prioritise articles about "{topics}" when routing.\n'
                  if topics and topics.strip() else '')

    label_list = '\n'.join(article_lines)

    system = 'You are a senior crypto editorial strategist. Return ONLY valid JSON — no prose, no markdown fences.'

    user = f"""PUBLICATIONS:{brand_section}

{topic_line}ARTICLES (label | source | title | age | description):
{label_list}

TASK — do these three things in order:

1. DEDUPLICATE: Find groups of articles that report the same underlying event (same story, different outlets or angles). For each group keep only the single best article (most authoritative source, most complete headline). List every removed duplicate's label in "duplicates".

2. CLUSTER: Assign each surviving article to the brand(s) it genuinely serves (max {MAX_BRANDS_PER_ART} brands per article). Apply each brand's REJECTS rules strictly. Keep Ranking classified as a platform, never a token. If an article fits no brand, omit it.

3. RANK: Within each brand, order articles best-fit first (how well this article serves THAT brand's specific audience). Keep at most {TOP_N_PER_BRAND} per brand. For each kept article include a fit score 0-100 and a one-line reason.

Return ONLY this JSON (replace … with real data):
{{
  "duplicates": [["a1","a3"], ["a5","a8","a12"]],
  "brands": {{
    "MGC Coin":         [{{"id":"a2","fit":87,"reason":"..."}}],
    "Ranking Platform": [...],
    "Oasis Coin":       [...],
    "Jewelry Coin":     [...],
    "Industrial Token": [...],
    "Real Estate Token": [...]
  }}
}}
Omit any brand not in the PUBLICATIONS list above. If a brand has no suitable articles, set its value to [].
"""
    return system, user


def _fallback(survivors: list[dict], selected_media: list[str]) -> list[dict]:
    """Emergency fallback: route most-recent articles to Oasis or the first brand."""
    catchall = 'Oasis Coin' if 'Oasis Coin' in selected_media else selected_media[0]
    sorted_arts = sorted(survivors,
                         key=lambda a: a.get('pub_date', ''), reverse=True)
    shortlist = []
    for i, art in enumerate(sorted_arts[:TOP_N_PER_BRAND]):
        auth = SOURCE_AUTHORITY.get(art.get('source', ''), DEFAULT_AUTHORITY)
        shortlist.append({
            'input_index': i,
            'title':   art.get('title', ''),
            'source':  art.get('source', ''),
            'link':    art.get('link') or art.get('url', ''),
            'desc':    (art.get('desc') or '')[:220],
            'pub_date': art.get('pub_date', ''),
            'scores': {'final': 50, 'virality': 0, 'freshness': 0,
                       'authority': auth, 'userTopic': 0, 'confidence': 50},
            'routing': {'primary_media': catchall, 'secondary_media': ''},
            '_brands': [catchall],
        })
    return shortlist


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_deepseek_pipeline(articles: list[dict], selected_media: list[str],
                          topics: str, recency_hours: int,
                          _openrouter_chat=None, _repair_json=None) -> dict:
    """
    Run the DeepSeek Pre-Process filter pipeline.
    _openrouter_chat and _repair_json are injected by server.py to avoid
    circular imports (they live in server.py, not filtering/).
    """
    now      = datetime.now(timezone.utc)
    cutoff   = datetime.fromtimestamp(now.timestamp() - recency_hours * 3600, tz=timezone.utc)

    all_tracked: list[dict] = []
    stats = {
        'fetched':            len(articles),
        'dropped_date':       0,
        'dropped_dup_cheap':  0,
        'sent_to_deepseek':   0,
        'duplicate_groups_found': 0,
        'api_calls':          0,
        'degraded':           False,
    }
    for name in selected_media:
        key = BRAND_NAME_TO_KEY.get(name)
        if key:
            stats[f'brand_{key}'] = 0

    # ── Stage 1: Date gate ────────────────────────────────────────────────────
    stage1: list[dict] = []
    for art in articles:
        raw = art.get('pubDate') or art.get('pub_date_raw') or ''
        dt  = _parse_date(raw)
        if dt is None:
            all_tracked.append({**art, '_pipelineStatus': 'no_date',
                                 '_scores': None, '_routing': None})
            stats['dropped_date'] += 1
            continue
        if dt < cutoff:
            all_tracked.append({**art, '_pipelineStatus': 'out_of_window',
                                 '_scores': None, '_routing': None,
                                 'pub_date': dt.isoformat()})
            stats['dropped_date'] += 1
            continue
        art['pub_date'] = dt.isoformat()
        stage1.append(art)

    # ── Stage 2: Cheap URL dedup ──────────────────────────────────────────────
    seen_urls:  set  = set()
    seen_norms: set  = set()
    seen_slugs: dict = {}
    survivors:  list[dict] = []

    for art in stage1:
        url  = (art.get('link') or art.get('url') or '').strip()
        norm = _normalise_url(url) if url else ''
        slug = _url_slug(url)
        src  = art.get('source', '')

        dup = (url  and url  in seen_urls) or \
              (norm and norm in seen_norms) or \
              (slug and (src, slug) in seen_slugs)

        if dup:
            all_tracked.append({**art, '_pipelineStatus': 'duplicate',
                                 '_scores': None, '_routing': None})
            stats['dropped_dup_cheap'] += 1
            continue

        if url:  seen_urls.add(url)
        if norm: seen_norms.add(norm)
        if slug: seen_slugs[(src, slug)] = art.get('title', '')
        survivors.append(art)

    if not survivors:
        return {'shortlist': [], 'stats': stats, 'all_tracked': all_tracked}

    stats['sent_to_deepseek'] = len(survivors)

    if _openrouter_chat is None or _repair_json is None:
        # Dependency injection not provided — return fallback
        shortlist = _fallback(survivors, selected_media)
        stats['degraded'] = True
        return {'shortlist': shortlist, 'stats': stats, 'all_tracked': all_tracked}

    # ── Stage 3: Label articles ───────────────────────────────────────────────
    label_map: dict[str, dict] = {}   # "a0" → article dict
    for i, art in enumerate(survivors):
        label_map[f'a{i}'] = art

    def _make_lines(arts_subset: list[dict], start: int) -> list[str]:
        lines = []
        for j, art in enumerate(arts_subset):
            lbl  = f'a{start + j}'
            age  = _age_label(art.get('pub_date', ''))
            desc = (art.get('desc') or '')[:200].replace('\n', ' ')
            lines.append(f'{lbl} | {art.get("source","")} | {art.get("title","")} | {age} | {desc}')
        return lines

    # ── Stage 4: DeepSeek request (with batching) ─────────────────────────────
    # Collect per-brand results across batches
    brand_results: dict[str, list[dict]] = {name: [] for name in selected_media}
    dup_survivors: set[str] = set()   # labels of articles kept after dedup

    def _call_deepseek(art_lines: list[str]) -> dict:
        system, user = _build_prompt(art_lines, selected_media, topics)
        raw = _openrouter_chat(
            DEEPSEEK_MODEL,
            [{'role': 'system', 'content': system},
             {'role': 'user',   'content': user}],
            temperature=0.20,
            max_tokens=4000,
        )
        stats['api_calls'] += 1
        return raw if isinstance(raw, dict) else {}

    def _process_response(resp: dict, offset: int, art_subset: list[dict]) -> None:
        valid_labels = {f'a{offset + i}' for i in range(len(art_subset))}

        # Handle duplicates
        for group in resp.get('duplicates', []):
            group = [g for g in group if g in valid_labels]
            if len(group) < 2:
                continue
            stats['duplicate_groups_found'] += 1
            # Keep the one with highest source authority
            best = max(group, key=lambda lbl: SOURCE_AUTHORITY.get(
                label_map[lbl].get('source', ''), DEFAULT_AUTHORITY))
            for lbl in group:
                if lbl != best:
                    art = label_map[lbl]
                    all_tracked.append({**art, '_pipelineStatus': 'clustered_out',
                                        '_scores': None, '_routing': None})
                    dup_survivors.add(lbl)   # mark as removed

        # Collect brand assignments
        brands_raw = resp.get('brands', {})
        for brand_name in selected_media:
            items = brands_raw.get(brand_name, [])
            for item in items:
                lbl = item.get('id', '')
                if lbl not in valid_labels or lbl in dup_survivors:
                    continue   # hallucinated or duplicate
                brand_results[brand_name].append({
                    'label': lbl,
                    'fit':   int(item.get('fit', 50)),
                    'reason': str(item.get('reason', '')),
                })

    if len(survivors) <= BATCH_SIZE:
        lines = _make_lines(survivors, 0)
        try:
            resp = _call_deepseek(lines)
            _process_response(resp, 0, survivors)
        except Exception as exc:
            print(f'[DeepSeek filter] first attempt failed: {exc}', file=sys.stderr)
            try:
                resp = _call_deepseek(lines)   # one retry
                _process_response(resp, 0, survivors)
            except Exception as exc2:
                print(f'[DeepSeek filter] retry failed: {exc2}', file=sys.stderr)
                stats['degraded'] = True
                shortlist = _fallback(survivors, selected_media)
                return {'shortlist': shortlist, 'stats': stats, 'all_tracked': all_tracked}
    else:
        # Batched path
        for batch_start in range(0, len(survivors), BATCH_SIZE):
            batch = survivors[batch_start:batch_start + BATCH_SIZE]
            lines = _make_lines(batch, batch_start)
            try:
                resp = _call_deepseek(lines)
                _process_response(resp, batch_start, batch)
            except Exception as exc:
                print(f'[DeepSeek filter] batch {batch_start} failed: {exc}', file=sys.stderr)
                # Skip this batch — articles still go to fallback below if nothing selected
        # Merge pass: re-dedup across batches within each brand
        for brand_name in selected_media:
            items = brand_results[brand_name]
            if len(items) <= TOP_N_PER_BRAND:
                continue
            # Re-sort and keep best TOP_N_PER_BRAND
            items.sort(key=lambda x: x['fit'], reverse=True)
            brand_results[brand_name] = items[:TOP_N_PER_BRAND]

    # ── Stage 5: Build output payload ─────────────────────────────────────────
    seen_in_payload: dict[str, dict] = {}   # title → payload entry
    all_brand_labels: dict[str, list] = {}  # label → [brands assigned]

    for brand_name in selected_media:
        items = brand_results[brand_name]
        items.sort(key=lambda x: x['fit'], reverse=True)
        items = items[:TOP_N_PER_BRAND]
        brand_key = BRAND_NAME_TO_KEY.get(brand_name)

        for item in items:
            lbl  = item['label']
            art  = label_map.get(lbl)
            if art is None:
                continue
            title = art.get('title', '')
            auth  = SOURCE_AUTHORITY.get(art.get('source', ''), DEFAULT_AUTHORITY)

            if title not in seen_in_payload:
                entry = {
                    'title':    title,
                    'source':   art.get('source', ''),
                    'link':     art.get('link') or art.get('url', ''),
                    'desc':     (art.get('desc') or '')[:220],
                    'pub_date': art.get('pub_date', ''),
                    'scores': {
                        'final':      item['fit'],
                        'virality':   0,
                        'freshness':  0,
                        'authority':  auth,
                        'userTopic':  0,
                        'confidence': item['fit'],
                    },
                    'routing': {
                        'primary_media':   brand_name,
                        'secondary_media': '',
                    },
                    '_brands':       [brand_name],
                    '_deepseek_reason': item['reason'],
                }
                seen_in_payload[title] = entry
                all_brand_labels[lbl]  = [brand_name]
                all_tracked.append({**art, '_pipelineStatus': 'selected',
                                    '_scores': entry['scores'],
                                    '_routing': entry['routing']})
                if brand_key:
                    stats[f'brand_{brand_key}'] = stats.get(f'brand_{brand_key}', 0) + 1
            else:
                # Article already in payload — add this brand
                existing = seen_in_payload[title]
                if brand_name not in existing['_brands']:
                    if len(existing['_brands']) < MAX_BRANDS_PER_ART:
                        existing['_brands'].append(brand_name)
                        if not existing['routing']['secondary_media']:
                            existing['routing']['secondary_media'] = brand_name

    shortlist = list(seen_in_payload.values())

    # Mark articles not selected by DeepSeek as no_media_fit
    selected_titles = {e['title'] for e in shortlist}
    for art in survivors:
        if art.get('title', '') not in selected_titles and art.get('title', '') not in {
            a.get('title') for a in all_tracked
        }:
            all_tracked.append({**art, '_pipelineStatus': 'no_media_fit',
                                 '_scores': None, '_routing': None})

    # Assign input_index
    for i, item in enumerate(shortlist):
        item['input_index'] = i

    return {
        'shortlist':   shortlist,
        'stats':       stats,
        'all_tracked': all_tracked,
    }
