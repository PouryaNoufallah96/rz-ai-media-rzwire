"""Editorial selection (multi-model parallel) + embedding filter pipelines."""
import sys

from config import EDITORIAL_MODELS, OPENROUTER_KEY
from llm import openrouter_chat, _repair_json, _editorial_call_one

# Optional source-article enrichment (fetch + summarize). ImportError here just
# disables enrichment; the editorial pipeline falls back to the RSS lede.
try:
    from article_enrich import enrich_shortlist as _enrich_shortlist
    _ENRICH_AVAILABLE = True
except Exception as _e:
    print(f'[WARN] article_enrich not available: {_e}', file=sys.stderr)
    _ENRICH_AVAILABLE = False

try:
    from filtering.pipeline import run_pipeline as _run_pipeline
    _FILTERING_AVAILABLE = True
except ImportError as _e:
    print(f'[WARN] filtering package not available: {_e}', file=sys.stderr)
    _FILTERING_AVAILABLE = False

try:
    from filtering.deepseek_pipeline import run_deepseek_pipeline as _run_deepseek_pipeline
    _DEEPSEEK_FILTER_AVAILABLE = True
except ImportError as _e2:
    print(f'[WARN] deepseek_pipeline not available: {_e2}', file=sys.stderr)
    _DEEPSEEK_FILTER_AVAILABLE = False


def handle_editorial_select(body):
    """Generator — yields (model_key, result_dict) as each model finishes.

    Validation (ValueError) happens before the first yield, so callers can
    pull `next(gen)` to surface a clean 400 before committing to a streamed
    response (HTTP headers can't be unsent once writing begins).
    """
    shortlist      = body.get('shortlist', [])
    sel_media      = body.get('selectedMedia', [])
    sel_plats      = body.get('selectedPlatforms', ['X', 'Telegram', 'Instagram'])
    topics         = body.get('topics', '').strip()
    test_mode      = body.get('testMode', False)
    enrich         = body.get('enrichArticles', True) and _ENRICH_AVAILABLE
    language       = body.get('language', 'en')

    if not shortlist:
        raise ValueError('shortlist is empty')
    if not OPENROUTER_KEY:
        raise ValueError('OPENROUTER_API_KEY not set in .env')

    if test_mode:
        brand_list = ', '.join(f'"{m}"' for m in sel_media)
        lines = '\n'.join(
            f'[{a["input_index"]}] {a.get("title","")} — {a.get("source","")}'
            for a in shortlist
        )
        system_prompt = (
            'You are a test assistant. Rewrite each article in very short format and return ONLY valid JSON.\n'
            f'Brands: [{brand_list}]. For each brand pick 1 article and rewrite it very briefly.\n'
            'Schema: {"brands":{"<brand>":[{"input_index":<N>,"platform":"X","title":"<short title>",'
            '"source":"<src>","source_url":"#","selection_reason":"test","copy":"<one sentence>",'
            '"hashtags":["#Test"],"suitability_score":80,"impact_score":80,"virality_score":80,"confidence_score":80}]}}'
        )
        user_prompt = f'Articles:\n{lines}'
        sel_models  = body.get('selectedModels', list(EDITORIAL_MODELS.keys()))
        active_models = {k: v for k, v in EDITORIAL_MODELS.items() if k in sel_models}
        from concurrent.futures import ThreadPoolExecutor, as_completed
        # Thinking models (Gemini 2.5 Pro, etc.) consume tokens on internal reasoning
        # before generating output, so they need a higher cap even in test mode.
        THINKING_MODELS = {'gemini'}
        with ThreadPoolExecutor(max_workers=len(active_models)) as pool:
            futures = {
                pool.submit(_editorial_call_one, k, {**v, 'max_tokens': 4000 if k in THINKING_MODELS else 800}, system_prompt, user_prompt): k
                for k, v in active_models.items()
            }
            for fut in as_completed(futures):
                yield fut.result()
        return

    # Optional: fetch + summarize each source article so the model sees more
    # than the RSS lede. Mutates items in place, adding '_enriched'. Falls back
    # to the raised-cap lede when scraping fails — never worse than today.
    if enrich and shortlist:
        _enrich_shortlist(shortlist)

    # Build compact article list for the prompt
    lines = []
    for a in shortlist:
        s   = a.get('scores', {})
        r   = a.get('routing', {})
        idx = a.get('input_index', 0)
        # Raised cap 220 → 450: the model now sees the full RSS lede even when
        # enrichment is off, and the fallback (when scraping fails) is richer.
        desc = (a.get('desc') or '')[:450].replace('\n', ' ')
        summary = (a.get('_enriched') or '').replace('\n', ' ')
        eligible_brands = a.get('_brands') or []
        brand_scores = a.get('brandScores') or {}
        eligibility = ', '.join(
            f"{brand} ({brand_scores.get(brand, {}).get('embeddingFit', 0):g})"
            for brand in eligible_brands
        ) or r.get('primary_media', '')
        # Only include the Summary line when enrichment actually produced text
        # beyond the lede — otherwise omit it to keep the prompt tight.
        summary_line = f'\n    Summary: {summary}' if summary else ''
        lines.append(
            f"[{idx}] {a.get('source','')} | "
            f"Score:{s.get('final',0)} Vir:{s.get('virality',0)} "
            f"Fresh:{s.get('freshness',0)} Auth:{s.get('authority',0)} "
            f"Eligible→{eligibility}\n"
            f"    \"{a.get('title','')}\"\n"
            f"    {a.get('link','')}\n"
            f"    {desc}"
            f"{summary_line}"
        )
    article_text = '\n\n'.join(lines)

    brand_list = ', '.join(sel_media) if sel_media else 'any'
    plat_list  = ', '.join(sel_plats)
    topic_line = f'Topic focus: {topics}' if topics else 'No specific topic filter — use your editorial judgment.'

    brand_descs = {
        'MGC Coin':         'Gaming Utility · Rewards · BNB Smart Chain · RZ Ecosystem',
        'Ranking Platform': 'Competition · Profiles · Teams · Tournaments · Community',
        'Oasis Coin':       'Metaverse · Gaming · Digital Worlds · Future Utility',
        'Jewelry Coin':     'Digital Jewelry · NFTs · Marketplace · Physical Craft',
        'Industrial Token': 'Industry 4.0 · Smart Factories · Supply Chains · Industrial Education',
        'Real Estate Token': 'Property Tokenization · Ownership · Digital Real Estate · Community',
    }
    brand_descs_text = '\n'.join(
        f'  - {m}: {brand_descs.get(m, "Crypto media brand")}' for m in sel_media
    )
    article_schema = (
        '{"input_index":<N>,"platform":"<platform>",'
        '"title":"<exact title>","source":"<source>","source_url":"<url>",'
        '"selection_reason":"<why>","copy":"<post copy>",'
        '"hashtags":["#Tag"],'
        '"suitability_score":<0-100>,"impact_score":<0-100>,'
        '"virality_score":<0-100>,"confidence_score":<0-100>}'
    )
    system_prompt = (
        'You are a senior crypto news editor making independent editorial decisions for social media publishing.\n'
        f'Available platforms: {plat_list}\n\n'
        f'Media brands you must cover:\n{brand_descs_text}\n\n'
        'Your task: For EACH media brand listed above, independently select the BEST 5 articles '
        'from that brand\'s 10 embedding-ranked eligible candidates. '
        'For a brand, select only articles whose Eligible list includes that brand. '
        'An article may appear in multiple brands if genuinely relevant to both.\n'
        'Base your judgment on: news value, real-world impact, brand fit, virality potential, freshness, and topic relevance.\n'
        'Each model is making this selection independently — bring your own editorial perspective.\n\n'
        'For each selected article:\n'
        '- Use the EXACT input_index from the [N] marker in the list\n'
        '- Assign the best matching platform\n'
        '- Write a selection_reason (1-2 sentences, your editorial reasoning for THIS brand)\n'
        '- Write platform-appropriate copy (tweet ≤280 chars for X, longer post for Telegram/Instagram)\n'
        '- Provide 3-5 relevant hashtags\n'
        '- Score suitability/impact/virality/confidence 0-100\n\n'
        'Respond ONLY with valid JSON — one key per brand, each value an array of exactly 5 article objects:\n'
        '{"brands":{'
        f'"<brand_name>":[{article_schema},...5 items],'
        '"<next_brand>":[...5 items]'
        '}}'
    )
    if language == 'fa':
        system_prompt += ('\nWrite all reader-facing fields in fluent Persian: title, selection_reason, copy, and hashtags. '
                          'Use Persian digits. Keep only crypto tickers, project and brand names, source names, and URLs in English. '
                          'The input_index and source_url values must remain exact.')
    user_prompt = f'{topic_line}\n\nShortlisted articles ({len(shortlist)} total):\n\n{article_text}'

    sel_models   = body.get('selectedModels', list(EDITORIAL_MODELS.keys()))
    active_models = {k: v for k, v in EDITORIAL_MODELS.items() if k in sel_models}
    if not active_models:
        active_models = EDITORIAL_MODELS  # fallback: use all

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=len(active_models)) as pool:
        futures = {
            pool.submit(_editorial_call_one, k, v, system_prompt, user_prompt): k
            for k, v in active_models.items()
        }
        for fut in as_completed(futures):
            yield fut.result()


# ── Embedding filter pipeline handler ──────────────────────────────────────────
def handle_filter_pipeline(body):
    if not _FILTERING_AVAILABLE:
        raise ValueError('filtering package not installed (pip install numpy)')
    articles       = body.get('articles', [])
    selected_media = body.get('selectedMedia', [])
    topics         = body.get('topics', '')
    recency_hours  = int(body.get('recencyHours', 24))
    if not articles:
        raise ValueError('articles array is empty')
    if not selected_media:
        raise ValueError('selectedMedia is empty')
    return _run_pipeline(articles, selected_media, topics, recency_hours)


def handle_deepseek_filter(body):
    if not _DEEPSEEK_FILTER_AVAILABLE:
        raise ValueError('deepseek_pipeline not available')
    articles       = body.get('articles', [])
    selected_media = body.get('selectedMedia', [])
    topics         = body.get('topics', '')
    recency_hours  = int(body.get('recencyHours', 24))
    if not articles:
        raise ValueError('articles array is empty')
    if not selected_media:
        raise ValueError('selectedMedia is empty')
    return _run_deepseek_pipeline(
        articles, selected_media, topics, recency_hours,
        _openrouter_chat=openrouter_chat,
        _repair_json=_repair_json,
    )
