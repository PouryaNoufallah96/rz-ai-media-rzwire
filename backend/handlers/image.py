"""Image generation routes: promo post ideas + full Art-Director image pipeline."""
import json
import sys

from config import BRAND_VISUAL_TONE, EDITORIAL_MODELS, OPENROUTER_IMAGE_MODELS
from brand_profiles import BRAND_IMAGE_PROFILES
from analytics_brands import get_analytics_brand
from llm import openrouter_chat, openrouter_image
from image_pipeline import (_RECENT_BRIEFS, _remember_brief, _article_mentions_brand,
                            call_art_director, validate_brief, assemble_prompt, _fallback_brief)
from analytics_image_pipeline import (assemble_analytics_prompt,
                                      call_analytics_art_director,
                                      fallback_analytics_brief,
                                      resolve_analytics_template,
                                      validate_analytics_brief)
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
    template_id = body.get('templateId', '').strip()
    template_category_id = body.get('templateCategoryId', '').strip() or template_id
    template_variant_id = body.get('templateVariantId', '').strip() or template_id
    theme_owner_token_id = body.get('themeOwnerTokenId', '').strip().lower()
    brand_theme = body.get('brandTheme', '').strip()
    output_dimensions = body.get('outputDimensions') or {}
    series_metadata = body.get('seriesMetadata') or []
    language = body.get('language', 'en')
    if model not in OPENROUTER_IMAGE_MODELS:
        raise ValueError('Unsupported image generation model')

    profile = BRAND_IMAGE_PROFILES.get(media)
    brief = None
    append_image_direction = True
    apply_logo_safe_zone = True
    if composition_mode == 'analytics_art_directed':
        if len(ref_images) != 3:
            raise ValueError(
                'Analytics Art Director requires exactly three ordered references: approved publishing sample, '
                'approved locked composition, and approved factual chart.'
            )
        if not template_category_id or not template_variant_id:
            raise ValueError('Analytics Art Director requires templateCategoryId and templateVariantId.')
        if not isinstance(series_metadata, list) or not series_metadata:
            raise ValueError('Analytics Art Director requires verified seriesMetadata.')
        if not theme_owner_token_id:
            raise ValueError('Analytics Art Director requires themeOwnerTokenId.')

        theme_owner = get_analytics_brand(theme_owner_token_id)
        selected_primary_ids = {
            str(item.get('tokenId') or str(item.get('id') or '').removeprefix('rz:')).strip().lower()
            for item in series_metadata if item.get('role') == 'primary'
        }
        if theme_owner_token_id not in selected_primary_ids:
            raise ValueError('The analytics theme owner must be one of the selected RZWire primary tokens.')
        profile = BRAND_IMAGE_PROFILES.get(theme_owner['artDirectorProfile'])
        if not profile:
            raise ValueError('The selected analytics theme owner has no approved Art Director profile.')

        template = resolve_analytics_template(template_category_id, template_variant_id)
        width = int(output_dimensions.get('width') or 1080)
        height = int(output_dimensions.get('height') or 1350)
        if width < 512 or height < 512 or width > 4096 or height > 4096:
            raise ValueError('Analytics output dimensions must be between 512 and 4096 pixels.')
        output_dimensions = {**output_dimensions, 'width': width, 'height': height}
        media = theme_owner['artDirectorProfile']

        try:
            raw_brief = call_analytics_art_director(
                article, copy_text, theme_owner, profile, template,
                output_dimensions, series_metadata, image_direction,
            )
            brief = validate_analytics_brief(raw_brief, template, theme_owner, series_metadata)
        except Exception as exc:  # Keep image generation available if the brief model fails.
            print(f'[image] Analytics Art Director failed, using fallback brief: {exc}', file=sys.stderr)
            brief = fallback_analytics_brief(template, theme_owner, series_metadata)

        prompt = assemble_analytics_prompt(
            brief, template, theme_owner, profile, article, copy_text,
            output_dimensions, series_metadata,
        )
        append_image_direction = False
        apply_logo_safe_zone = False
    elif composition_mode == 'analytics_frame_composite':
        if len(ref_images) not in (2, 3):
            raise ValueError(
                'Analytics frame composition requires either two legacy references or three ordered references: '
                'approved concept, static publishing frame, and approved factual chart.'
            )
        if not template_category_id or not template_variant_id:
            raise ValueError('Analytics frame composition requires templateCategoryId and templateVariantId.')
        if not isinstance(series_metadata, list) or not series_metadata:
            raise ValueError('Analytics frame composition requires verified seriesMetadata.')
        # Older analytics clients identified the owner through ``brandTheme`` and
        # omitted role/tokenId from series metadata. Preserve that request shape
        # while keeping the registry as the sole source of truth. New clients
        # always send themeOwnerTokenId explicitly.
        legacy_theme_owner = not theme_owner_token_id
        if legacy_theme_owner:
            theme_owner_token_id = brand_theme.strip().lower()
        theme_owner = get_analytics_brand(theme_owner_token_id)
        selected_primary_ids = {
            str(item.get('tokenId') or str(item.get('id') or '').removeprefix('rz:')).strip().lower()
            for item in series_metadata if item.get('role') == 'primary'
        }
        if legacy_theme_owner and not selected_primary_ids:
            owner_symbol = str(theme_owner.get('symbol') or '').upper()
            if any(str(item.get('symbol') or '').upper() == owner_symbol for item in series_metadata):
                selected_primary_ids.add(theme_owner_token_id)
        if theme_owner_token_id not in selected_primary_ids:
            raise ValueError('The analytics theme owner must be one of the selected RZWire primary tokens.')
        profile = BRAND_IMAGE_PROFILES.get(theme_owner['artDirectorProfile'])
        if not profile:
            raise ValueError('The selected analytics theme owner has no approved Art Director profile.')
        media = theme_owner['artDirectorProfile']
        width = int(output_dimensions.get('width') or 1080)
        height = int(output_dimensions.get('height') or 1350)
        if width < 512 or height < 512 or width > 4096 or height > 4096:
            raise ValueError('Analytics output dimensions must be between 512 and 4096 pixels.')
        symbols = ', '.join(str(item.get('symbol', '')).upper() for item in series_metadata if item.get('symbol'))
        headline = str(article.get('title') or '').strip()
        if len(ref_images) == 3:
            chart_frame_reference = 'REFERENCE 2'
            reference_instructions = (
                'Create one beautiful, premium, publication-ready financial social-media post from exactly three ordered references. '
                'REFERENCE 1 is the exact APPROVED VISUAL CONCEPT and the primary aesthetic target. Keep its recognizable composition, '
                'proportions, visual rhythm, device or card treatment, hierarchy, spacing, lighting, and premium finish. Adapt its example '
                'coin identity to the selected RZWire theme owner without drifting into a different template. '
                'REFERENCE 2 is the deterministic STATIC PUBLISHING FRAME. Treat its canvas, headline, supporting text, logo placement, '
                'footer/domain placement, and chart aperture as protected layout instructions. '
                'REFERENCE 3 is the AUTHORITATIVE APPROVED FACTUAL CHART. Place this complete chart inside the reserved chart aperture '
            )
        else:
            chart_frame_reference = 'REFERENCE 1'
            reference_instructions = (
                'Create one beautiful, premium, publication-ready financial social-media post from two legacy ordered references. '
                'REFERENCE 1 is the deterministic STATIC PUBLISHING FRAME. Treat its canvas, headline, supporting text, logo placement, '
                'footer/domain placement, device or card silhouette, and chart aperture as protected layout instructions. '
                'REFERENCE 2 is the AUTHORITATIVE APPROVED FACTUAL CHART. Place this complete chart inside the reserved chart aperture '
            )
        prompt = (
            reference_instructions +
            f'of {chart_frame_reference} so it feels naturally integrated into the frame. The chart must remain the dominant, sharp, readable '
            'factual element. Preserve the entire chart image: do not crop, redraw, simplify, recolor, relabel, blur, restyle, or '
            'invent any line, axis, date, legend, ticker, value, percentage, or market fact. Do not turn the frame into a fake '
            'CoinMarketCap screenshot, generic trading dashboard, website page, data table, or collection of extra market cards. '
            'Do not add a second chart. Improve only the visual integration around the protected chart using refined lighting, '
            'realistic depth, subtle reflections, elegant spacing, and premium editorial polish. Preserve the protected header, '
            'supporting text, brand mark, footer, and domain; never replace them with invented wording, logos, or domains. '
            f'Exact headline intent: {headline}. Supporting text intent: {copy_text}. '
            f'Publishing category: {template_category_id}. Exact variant: {template_variant_id}. '
            f'Brand owner: {theme_owner["name"]}. Brand palette: {json.dumps(theme_owner["theme"])}. '
            f'Brand motifs: {", ".join(theme_owner["motifs"])}. Art direction: {theme_owner["imagePrompt"]}. '
            f'Canvas: {width}x{height}. Verified assets: {symbols}. '
            'Return one finished image only, with no mockup annotations, editing handles, placeholder labels, or explanation.'
        )
    elif composition_mode == 'analytics_background':
        if len(ref_images) != 3:
            raise ValueError('Analytics background generation requires exactly three ordered references: design sample, approved composition, and approved chart.')
        if not template_id:
            raise ValueError('Analytics background generation requires templateId.')
        if not isinstance(series_metadata, list) or not series_metadata:
            raise ValueError('Analytics background generation requires verified seriesMetadata.')
        width = int(output_dimensions.get('width') or 1080)
        height = int(output_dimensions.get('height') or 1350)
        if width < 512 or height < 512 or width > 4096 or height > 4096:
            raise ValueError('Analytics output dimensions must be between 512 and 4096 pixels.')
        symbols = ', '.join(str(item.get('symbol', '')).upper() for item in series_metadata if item.get('symbol'))
        prompt = (
            'Create only a refined decorative background layer for a premium financial social post. '
            'REFERENCE 1 is the permanent publishing-design sample. REFERENCE 2 is the approved deterministic final composition. '
            'REFERENCE 3 is the authoritative white factual chart. Use them only to understand spacing, atmosphere, and palette. '
            'The returned image will sit BEHIND the exact deterministic composition, so preserve calm negative space and avoid focal '
            'objects where the composition places its device, chart, header, statistics, logo, and footer. '
            'STRICTLY FORBIDDEN: any letters, words, numbers, tickers, prices, percentages, dates, charts, axes, legends, logos, '
            'watermarks, device screens, interface panels, cards, buttons, graphs, or financial symbols. Do not imitate or redraw '
            'any protected factual or branded layer. Return atmosphere only: subtle light, gradient depth, restrained texture, and '
            f'brand-compatible ambience. Template: {template_id}. Theme: {brand_theme or media}. Canvas: {width}x{height}. '
            f'Assets represented above the background: {symbols}. '
        )
    elif composition_mode == 'analytics_post':
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

    if image_direction and append_image_direction:
        prompt = prompt + ' ' + image_direction
    if language == 'fa':
        prompt += (' Any visible headline, caption, or text in the image MUST be fluent Persian in a clear RTL layout '
                   'with Persian digits. Keep only essential crypto tickers and project or brand names in English.')
    if apply_logo_safe_zone and ''.join(str(media).lower().split()) in _LOGO_MEDIA_KEYS:
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
        'compositionMode': composition_mode,
    }
    if brief is not None:
        result['brief'] = brief
    return result
