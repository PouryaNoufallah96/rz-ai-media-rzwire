"""Image generation routes: promo post ideas + full Art-Director image pipeline."""
import json
import sys

from config import BRAND_VISUAL_TONE, EDITORIAL_MODELS, OPENROUTER_IMAGE_MODELS
from brand_profiles import BRAND_IMAGE_PROFILES
from llm import openrouter_chat, openrouter_image
from image_pipeline import (_RECENT_BRIEFS, _remember_brief, _article_mentions_brand,
                            call_art_director, validate_brief, assemble_prompt, _fallback_brief)
from _branddoc import _brand_doc


_LOGO_MEDIA_KEYS = {'mgccoin', 'rankingplatform', 'oasiscoin', 'jewelrycoin'}
_LOGO_SAFE_ZONE = (
    ' Keep the immediate bottom-left corner uncluttered for an official logo added after generation, '
    'but it must remain a seamless, natural continuation of the surrounding artwork. Do NOT create a '
    'separate logo area, box, panel, tile, mask, dark or light block, changed background color, or '
    'texture behind it. Do not place people, faces, objects, coins, devices, charts, data, text, borders, '
    'frames, divider lines, corners, geometric accents, ornaments, or focal details in that corner. '
    'Do not draw or invent any logo or watermark.'
)


def handle_promo_ideas(body):
    brand     = body.get('brand', '')
    prompt    = body.get('prompt', '').strip()
    model_key = body.get('modelKey', 'gpt')
    language  = body.get('language', 'en')
    if not prompt:
        raise ValueError('prompt is required')

    # The full brand bible — positioning, content pillars, voice, and the compliance
    # "Do Not Say" guardrails that MUST bind the generated ideas.
    bible = _brand_doc(brand)

    sys_msg = (
        f"You are the senior social media strategist for {brand}, a premium crypto/Web3 brand.\n"
        "You live and breathe the brand bible below. Every idea you produce MUST respect its "
        "positioning, voice, content pillars, and especially its compliance guardrails — never "
        "use a phrase the bible marks as 'do not say', never position the product as something "
        "the bible forbids (e.g. exchange, insurance, casino, investment, yield), and never make "
        "profit/risk-free/guaranteed-return claims.\n\n"
        f"===== {brand} BRAND BIBLE (authoritative) =====\n"
        f"{bible}\n"
        "===== END BRAND BIBLE =====\n\n"
        "Your task: the user wants to create promotional social posts. Based on their direction "
        "below, generate exactly 4 DIFFERENT post ideas. Each idea must use a distinct angle or "
        "hook drawn from the brand's content pillars/evergreen angles — variety is the point, so "
        "no two ideas should make the same argument or lean on the same pillar.\n\n"
        "Every idea must be fully on-brand and compliance-safe: mechanism-led, credible, no hype, "
        "no empty promises, no forbidden vocabulary. Lead with the product truth, not a price promise.\n\n"
        "Respond with a JSON array of exactly 4 objects, each with:\n"
        '- "title": a short punchy headline (8-12 words, captures the post idea, on-brand voice)\n'
        '- "description": a 1-2 sentence summary of what the post will communicate and the angle it takes\n'
        '- "angle": a 2-4 word label for the angle (e.g. "Mechanism explainer", "Comparison", "Trust")\n\n'
        "Respond with ONLY the JSON array, no other text."
    )
    user_msg = f"Create promotional posts about: {prompt}"
    if language == 'fa':
        sys_msg += ('\nWrite every title, description, and angle in fluent Persian with Persian digits. '
                    'Keep crypto tickers, project and brand names, and URLs in English.')
    model_cfg = EDITORIAL_MODELS.get(model_key, EDITORIAL_MODELS['gpt'])
    model_id = model_cfg['id']
    msgs = [{'role': 'system', 'content': sys_msg}, {'role': 'user', 'content': user_msg}]
    # NOTE: openrouter_chat() runs _repair_json(), so it may return an ALREADY-PARSED
    # Python object (list/dict), not a string. Handle both shapes defensively.
    try:
        result = openrouter_chat(model_id, msgs, temperature=0.9, max_tokens=1500)
    except Exception as exc:  # noqa: BLE001 — surface a clean error, never a 500
        return {'ideas': [], 'error': f'{model_cfg["display"]} call failed: {exc}'}

    if isinstance(result, (list, dict)):
        ideas = result if isinstance(result, list) else [result]
    elif isinstance(result, str):
        raw = result.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        try:
            ideas = json.loads(raw)
        except json.JSONDecodeError as exc:
            return {'ideas': [], 'error': f'{model_cfg["display"]} returned malformed JSON: {exc}'}
        if not isinstance(ideas, list):
            ideas = [ideas]
    else:
        return {'ideas': [], 'error': f'{model_cfg["display"]} returned unexpected type {type(result).__name__}'}

    # Normalise: keep only well-formed idea objects with at least a title/description
    clean = []
    for it in ideas:
        if isinstance(it, dict) and (it.get('title') or it.get('description')):
            clean.append({'title': it.get('title', ''), 'description': it.get('description', ''),
                          'angle': it.get('angle', '')})
    if not clean:
        return {'ideas': [], 'error': f'{model_cfg["display"]} returned no usable ideas'}
    return {'ideas': clean[:4]}


def handle_generate_image(body):
    article   = body.get('article', {})
    platform  = body.get('platform', 'X')
    media     = body.get('mediaBrand', 'MGC Coin')
    sentiment = body.get('sentiment', 'Neutral')
    model     = body.get('model', 'openai/gpt-5.4-image-2')
    copy_text = body.get('copy', '')
    image_direction = body.get('imageDirection', '').strip()
    ref_images = body.get('referenceImages', []) or []
    composition_mode = body.get('compositionMode', '').strip()
    language = body.get('language', 'en')
    if model not in OPENROUTER_IMAGE_MODELS:
        raise ValueError('Unsupported image generation model')

    profile = BRAND_IMAGE_PROFILES.get(media)
    brief = None
    if composition_mode == 'analytics_post':
        if len(ref_images) < 2:
            raise ValueError('Analytics post composition requires a design reference and an approved chart reference.')
        prompt = (
            'Create a single finished premium financial social-media post using the two supplied images. '
            'The FIRST image is the visual-layout reference. The SECOND image is the authoritative approved market chart. '
            'Follow the first image for composition, lighting, device framing, spacing, and atmosphere. '
            'Place the second image fully inside the device screen, preserving its complete axes, dates, lines, labels, '
            'values, proportions, and geometry. Do not crop the approved chart or fabricate market information. '
            f'Brand identity: {media}. Platform: {platform}. Story copy: {copy_text}. '
            'Return one polished publication-ready post, not a background, mockup description, or editable wireframe. '
        )
    elif profile:
        recent     = _RECENT_BRIEFS.get(media, [])
        brand_mode = _article_mentions_brand(article, profile)
        # Art-Director LLM call (Stage 1). If it fails for ANY reason — empty
        # content due to finish_reason=length, network blip, JSON repair failure,
        # OpenRouter outage — fall back to the deterministic safe brief instead
        # of surfacing an error. Image generation must never hard-fail here.
        try:
            raw_brief = call_art_director(article, copy_text, sentiment, platform, profile, recent, brand_mode=brand_mode)
            brief = validate_brief(raw_brief, article, profile, recent)
            if not brand_mode and 'wolf' in brief:
                brief['wolf'] = 'none'
        except Exception as exc:  # noqa: BLE001 — the show must go on
            print(f'[image] Art Director failed, using fallback brief: {exc}', file=sys.stderr)
            brief = _fallback_brief(article, profile)
            if not brand_mode and 'wolf' in brief:
                brief['wolf'] = 'none'
        prompt = assemble_prompt(brief, profile, brand_mode=brand_mode)
        _remember_brief(media, brief, profile)
    else:
        # interim fallback for brands not yet migrated to the Art-Director pipeline
        tone = BRAND_VISUAL_TONE.get(media, 'premium crypto news, dark cinematic aesthetic')
        sent_tone = ('optimistic upward energy, green tones' if sentiment == 'Bullish'
                     else 'tense cautionary mood, red accents' if sentiment == 'Bearish'
                     else 'balanced neutral editorial')
        prompt = (
            f'Hyper-realistic editorial illustration for a premium crypto news brand. '
            f'Story: {article.get("title", "")}. Brand visual tone: {tone}. Mood: {sent_tone}. '
            f'Platform: {platform} post — {"square-friendly, bold visual" if platform == "Instagram" else "wide cinematic banner"}. '
            f'No text overlays. No logos.'
        )

    if image_direction:
        prompt = prompt + ' ' + image_direction
    if language == 'fa':
        prompt += (' Any visible headline, caption, or text in the image MUST be fluent Persian in a clear RTL layout '
                   'with Persian digits. Keep only essential crypto tickers and project or brand names in English.')
    if ''.join(str(media).lower().split()) in _LOGO_MEDIA_KEYS:
        prompt += _LOGO_SAFE_ZONE

    print(f'[image] brief: {brief}', file=sys.stderr)
    print(f'[image] prompt: {prompt}', file=sys.stderr)
    image_b64, model_used = openrouter_image(prompt, model, ref_images=ref_images or None)
    result = {
        'imageB64': image_b64,
        'prompt': prompt,
        'model': model_used,
        'requestedModel': model,
        'usedFallback': model_used != model,
    }
    if brief is not None:
        result['brief'] = brief
    return result
