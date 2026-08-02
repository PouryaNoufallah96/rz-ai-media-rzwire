"""Template-family Art Director pipeline for verified Market Analytics posts.

The market chart and copy are factual inputs owned by the deterministic analytics
workflow.  This module directs the *presentation* of those facts: it translates
the chosen permanent sample, the selected brand owner, and the template variant
into a small validated creative brief and then a strict image-generation prompt.
"""

from __future__ import annotations

import json
from copy import deepcopy

from config import EDITORIAL_MODELS
from llm import openrouter_chat


ANALYTICS_TEMPLATE_FAMILIES = {
    "phone": {
        "name": "Phone Market View",
        "variants": {
            "phone-centered": "Centered full-height premium phone; the complete verified chart belongs inside the phone screen.",
            "phone-split-stat": "Editorial phone with exact verified result callouts beside the device and the chart inside its screen.",
            "phone-editorial": "Tighter dramatic phone crop with an oversized headline and a complete readable chart inside the screen.",
        },
    },
    "laptop": {
        "name": "Laptop Dashboard",
        "variants": {
            "laptop-cinematic": "Centered frontal premium laptop on a cinematic stage; the approved chart fills the laptop screen.",
            "laptop-editorial": "Angled laptop with calm editorial spacing; the approved chart is the dominant content inside the screen.",
            "laptop-wide": "Wide desk-set laptop for a multi-series story; the complete approved chart fills the screen aperture.",
        },
    },
    "growth": {
        "name": "Growth Spotlight",
        "variants": {
            "growth-card": "Protected performance card with exact movement, start/end values, and the approved chart.",
            "growth-hero": "Large performance-led hero with the approved chart as the dominant factual element.",
            "growth-milestone": "Spacious editorial milestone composition with a refined protected chart panel.",
        },
    },
    "contrast": {
        "name": "Performance Contrast",
        "variants": {
            "contrast-duel": "Winner/loser panels with exact values and protected mini-chart evidence.",
            "contrast-intersecting": "One protected combined chart with exact endpoint callouts and a clear outcome headline.",
            "contrast-scoreboard": "Ranked cinematic scoreboard with exact verified outcomes and a compact protected chart.",
        },
    },
    "separated": {
        "name": "Separated Performance",
        "variants": {
            "separated-grid": "Responsive grid of one exact card per selected asset, each with verified values and a mini chart.",
            "separated-stacked": "Offset connected cards with exact mini charts and a calm premium field.",
            "separated-orbiting": "Dynamic modular asset cards orbiting a shared verified market story.",
        },
    },
    "combined": {
        "name": "Combined Performance",
        "variants": {
            "combined-rounded": "Large rounded multi-series chart with exact callouts and horizon-like depth.",
            "combined-minimal": "Quiet spotlight chart with a clean legend, premium restraint, and generous negative space.",
            "combined-editorial": "Typography-led editorial composition with one protected chart and exact endpoint callouts.",
        },
    },
}


_ALLOWED_DEPTH = {"flat editorial", "soft dimensional", "cinematic dimensional"}
_ALLOWED_LIGHTING = {"quiet studio", "directional editorial", "cinematic atmospheric"}
_ALLOWED_DENSITY = {"minimal", "balanced", "information-rich"}


def resolve_analytics_template(category_id: str, variant_id: str) -> dict:
    category = ANALYTICS_TEMPLATE_FAMILIES.get(str(category_id or "").strip())
    if not category:
        raise ValueError("Unknown analytics publishing category.")
    variant_rule = category["variants"].get(str(variant_id or "").strip())
    if not variant_rule:
        raise ValueError("The selected analytics variant does not belong to its publishing category.")
    return {
        "categoryId": category_id,
        "categoryName": category["name"],
        "variantId": variant_id,
        "variantRule": variant_rule,
    }


def _clean_series(series_metadata) -> list[dict]:
    clean = []
    for item in series_metadata or []:
        if not isinstance(item, dict) or not str(item.get("symbol") or "").strip():
            continue
        clean.append({
            "symbol": str(item.get("symbol") or "").strip().upper(),
            "name": str(item.get("name") or item.get("symbol") or "").strip(),
            "role": str(item.get("role") or "comparison").strip(),
            "startPrice": item.get("startPrice"),
            "endPrice": item.get("endPrice"),
            "changePercent": item.get("changePercent"),
            "coverageStart": item.get("coverageStart"),
            "coverageEnd": item.get("coverageEnd"),
        })
    if not clean:
        raise ValueError("Analytics Art Director requires verified series metadata.")
    if len(clean) > 6:
        raise ValueError("Analytics Art Director supports at most six verified series.")
    return clean


def fallback_analytics_brief(template: dict, theme_owner: dict, series_metadata) -> dict:
    series = _clean_series(series_metadata)
    category = template["categoryId"]
    density = "minimal" if len(series) <= 2 else "balanced" if len(series) <= 4 else "information-rich"
    device = "none"
    if category == "phone":
        device = "premium phone frame"
    elif category == "laptop":
        device = "premium laptop frame"
    return {
        "family": category,
        "variant": template["variantId"],
        "concept": f'{theme_owner["name"]} verified market editorial',
        "sample_fidelity": "binding",
        "device_strategy": device,
        "chart_strategy": "place the complete approved chart inside the sample's reserved chart aperture",
        "layout_hierarchy": "headline, supporting statement, protected chart, exact result summary, brand footer",
        "background_scene": theme_owner["imagePrompt"],
        "lighting": "cinematic atmospheric" if category in {"phone", "laptop", "contrast"} else "directional editorial",
        "depth": "cinematic dimensional" if category in {"phone", "laptop"} else "soft dimensional",
        "density": density,
        "brand_expression": ", ".join(theme_owner.get("motifs") or []),
        "negative_space": "preserve the sample's breathing room around the headline, chart, and footer",
        "factual_protection": "all visible chart geometry and market facts come only from the approved chart and supplied metadata",
    }


def call_analytics_art_director(article, copy_text, theme_owner, profile, template,
                                output_dimensions, series_metadata, creative_direction=""):
    """Stage 1: ask the same editorial model used by Multimedia for a JSON brief."""
    series = _clean_series(series_metadata)
    profile_style = profile.get("frozen_style") or {}
    system_prompt = (
        f'You are the specialist Market Analytics Art Director for {theme_owner["name"]}. '
        'You do not invent market data and you do not write an image prompt. You create a concise JSON visual brief '
        'for a deterministic prompt assembler. The approved sample is a BINDING template family, not a loose moodboard. '
        'The final image must remain recognizably the same publishing design while its palette, logo, footer, copy, and '
        'chart content adapt to the selected coin and verified dataset. The approved factual chart must be complete, sharp, '
        'readable, and placed inside the sample\'s chart/device aperture. Never move a phone or laptop chart outside its screen.\n\n'
        f'BRAND OWNER: {theme_owner["name"]}\n'
        f'PALETTE: {json.dumps(theme_owner["theme"], ensure_ascii=False)}\n'
        f'MOTIFS: {", ".join(theme_owner.get("motifs") or [])}\n'
        f'BRAND DIRECTION: {theme_owner["imagePrompt"]}\n'
        f'FROZEN PROFILE STYLE: {json.dumps(profile_style, ensure_ascii=False)}\n\n'
        f'TEMPLATE FAMILY: {template["categoryName"]}\n'
        f'EXACT VARIANT: {template["variantId"]}\n'
        f'VARIANT CONTRACT: {template["variantRule"]}\n\n'
        'Return ONLY one JSON object with exactly these keys: family, variant, concept, sample_fidelity, '
        'device_strategy, chart_strategy, layout_hierarchy, background_scene, lighting, depth, density, '
        'brand_expression, negative_space, factual_protection. '
        'sample_fidelity must be "binding". lighting must be one of: quiet studio, directional editorial, '
        'cinematic atmospheric. depth must be one of: flat editorial, soft dimensional, cinematic dimensional. '
        'density must be one of: minimal, balanced, information-rich.'
    )
    user_prompt = (
        f'Exact headline: {article.get("title", "")}\n'
        f'Exact supporting text: {copy_text}\n'
        f'Canvas: {output_dimensions.get("width", 1080)}x{output_dimensions.get("height", 1350)}\n'
        f'Verified series: {json.dumps(series, ensure_ascii=False)}\n'
        f'Additional creative direction: {creative_direction or "none"}\n\n'
        'Design the visual brief now. Keep all factual content protected.'
    )
    return openrouter_chat(
        EDITORIAL_MODELS["gpt"]["id"],
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        0.55,
        1400,
        deadline_sec=30,
    )


def validate_analytics_brief(raw_brief, template, theme_owner, series_metadata) -> dict:
    fallback = fallback_analytics_brief(template, theme_owner, series_metadata)
    if not isinstance(raw_brief, dict):
        return fallback
    if raw_brief.get("family") != template["categoryId"] or raw_brief.get("variant") != template["variantId"]:
        return fallback
    brief = deepcopy(fallback)
    for key in (
        "concept", "device_strategy", "chart_strategy", "layout_hierarchy", "background_scene",
        "brand_expression", "negative_space", "factual_protection",
    ):
        value = str(raw_brief.get(key) or "").strip()
        if value:
            brief[key] = value[:700]
    brief["sample_fidelity"] = "binding"
    brief["lighting"] = raw_brief.get("lighting") if raw_brief.get("lighting") in _ALLOWED_LIGHTING else fallback["lighting"]
    brief["depth"] = raw_brief.get("depth") if raw_brief.get("depth") in _ALLOWED_DEPTH else fallback["depth"]
    brief["density"] = raw_brief.get("density") if raw_brief.get("density") in _ALLOWED_DENSITY else fallback["density"]
    # These two clauses are non-negotiable even if the model omitted them.
    brief["chart_strategy"] += "; preserve the full approved chart without redrawing or moving it outside the aperture"
    brief["factual_protection"] = fallback["factual_protection"]
    return brief


def assemble_analytics_prompt(brief, template, theme_owner, profile, article, copy_text,
                              output_dimensions, series_metadata) -> str:
    """Stage 2: deterministically assemble the final three-reference prompt."""
    series = _clean_series(series_metadata)
    width = int(output_dimensions.get("width") or 1080)
    height = int(output_dimensions.get("height") or 1350)
    facts = json.dumps(series, ensure_ascii=False, separators=(",", ":"))
    theme = json.dumps(theme_owner["theme"], ensure_ascii=False, separators=(",", ":"))
    footer = theme_owner["footer"]
    headline = str(article.get("title") or "").strip()
    return (
        f'Create one finished {width}x{height} premium financial social post from exactly THREE ordered references. '
        'REFERENCE 1 is the permanent APPROVED PUBLISHING SAMPLE and is the binding composition contract. Match its '
        'camera, crop, device/card silhouette, chart aperture, information hierarchy, spacing, visual rhythm, lighting '
        'quality, and premium finish. Do not reinterpret it as a different layout. Replace only the example coin identity, '
        'palette, copy, footer, and market content. '
        'REFERENCE 2 is the APPROVED LOCKED COMPOSITION. Preserve its exact headline, supporting-copy hierarchy, logo '
        'position, footer position, output ratio, and reserved chart aperture. '
        'REFERENCE 3 is the AUTHORITATIVE APPROVED FACTUAL CHART. Insert this complete chart into the reserved aperture '
        'defined by References 1 and 2. For phone and laptop families the entire chart MUST be physically inside the device '
        'screen, clipped by the inner screen boundary with realistic screen perspective and reflections. Never float it in '
        'front of, behind, beside, or outside the device. For non-device families keep it inside the sample\'s protected chart '
        'panel. Preserve all chart lines, axes, dates, legends, labels, relative geometry, and proportions. Do not redraw, '
        'simplify, recolor, crop, blur, or fabricate the chart. '
        f'TEMPLATE FAMILY: {template["categoryName"]}. EXACT VARIANT: {template["variantId"]}. '
        f'VARIANT CONTRACT: {template["variantRule"]}. '
        f'ART DIRECTOR BRIEF: {json.dumps(brief, ensure_ascii=False)}. '
        f'BRAND OWNER: {theme_owner["name"]}. BRAND PALETTE: {theme}. '
        f'BRAND MOTIFS: {", ".join(theme_owner.get("motifs") or [])}. '
        f'BRAND ART DIRECTION: {theme_owner["imagePrompt"]}. '
        f'EXACT HEADLINE: "{headline}". EXACT SUPPORTING TEXT: "{copy_text}". '
        f'EXACT FOOTER/DOMAIN: "{footer}". VERIFIED SERIES METADATA: {facts}. '
        'Comparison assets may keep their own line/marker colors but may never control the background theme. '
        'Do not invent or substitute any price, percentage, ticker, date, logo, domain, legend, axis, or claim. Do not add '
        'CoinMarketCap branding, a generic website dashboard, extra cards, a second chart, placeholder copy, watermarks, '
        'editing handles, or mockup annotations. The only visible text may be the supplied headline, supporting text, footer, '
        'and factual labels already present in the approved chart/metadata. Return one publication-ready image only.'
    )
