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
from analytics_chart_style import normalize_chart_style, normalize_hex_color
from llm import openrouter_chat


def _variant(summary, skeleton, chart, typography, brand_translation, finish, forbidden):
    """Create one immutable analytics family contract.

    The sample image remains the visual source of truth.  These fields give the
    vision Art Director enough production language to describe it precisely and
    stop the final image model from drifting into a generic dashboard.
    """
    return {
        "summary": summary,
        "skeleton": skeleton,
        "chart": chart,
        "typography": typography,
        "brandTranslation": brand_translation,
        "finish": finish,
        "forbidden": forbidden,
    }


ANALYTICS_TEMPLATE_FAMILIES = {
    "phone": {
        "name": "Phone Market View",
        "variants": {
            "phone-centered": _variant(
                "Centered full-height premium phone with a complete market view inside its screen.",
                "One dominant upright phone occupies roughly 62-72% of canvas height and is centered on a quiet branded stage. A concise headline sits above it; the official footer sits below it. The device, header, and footer form one strong vertical axis.",
                "The approved chart is clipped fully inside the phone display, filling the central screen module without covering the bezel. Above it are compact asset chips and period controls; below it are the exact legend and a short market-stat summary.",
                "Large editorial headline, one restrained supporting line, compact but readable screen UI, and a clearly legible footer. Preserve the sample's type scale and line breaks.",
                "Keep the phone geometry and information architecture fixed. Translate only the stage palette, restrained motifs, logo, domain, chart colors, and coin-specific accents to the theme owner.",
                "Photoreal premium device, crisp glass and metal, controlled reflections, sharp screen, high-end campaign lighting, no hazy or miniature UI.",
                "No chart outside the phone; no floating chart panel; no giant unused lower half; no extra device; no tiny headline; no fake app data; no generic crypto neon.",
            ),
            "phone-split-stat": _variant(
                "Editorial phone with verified result callouts balanced around the device.",
                "A slightly off-center upright phone fills 58-68% of canvas height. One or two result blocks flank it at mid-height while the headline occupies the upper band and the footer anchors the lower band.",
                "The complete approved chart remains inside the phone screen. Exterior callouts repeat only verified start price, end price, and movement for the most important series; they never replace or obscure the chart.",
                "Confident headline above; large numeric callouts outside; disciplined compact UI inside; footer at readable social-post size.",
                "Use the owner palette for the stage and callout containers while every asset retains its assigned chart color. Keep the owner's logo and domain in the sample positions.",
                "Premium product-ad polish, subtle dimensional shadows, accurate device perspective, generous but purposeful breathing room.",
                "No detached chart; no more callouts than the sample can hold; no tilted phone unless visible in the sample; no duplicated numbers; no empty decorative cards.",
            ),
            "phone-editorial": _variant(
                "Tight dramatic editorial phone crop with headline-led storytelling.",
                "The phone is enlarged and may crop slightly at one canvas edge exactly as the sample does. A bold headline and concise comparison statement occupy the complementary negative-space block.",
                "The full approved chart is scaled into the visible phone screen, never under the crop or bezel. The chart, period, legend, and endpoint facts remain readable at publication size.",
                "Oversized headline with compact support copy; screen text uses a clean market-interface hierarchy; footer is visible and deliberate.",
                "Preserve the dramatic crop and replace sample colors, logo, domain, and atmospheric motifs with the selected owner's language.",
                "Editorial fashion-tech finish, precise edge light, rich blacks, crisp device and screen, intentional asymmetry.",
                "No separate chart card; no phone reduced to a small icon; no lost screen content; no excessive copy; no invented UI branding.",
            ),
        },
    },
    "laptop": {
        "name": "Laptop Dashboard",
        "variants": {
            "laptop-cinematic": _variant(
                "Centered frontal premium laptop on a dramatic chart-focused stage.",
                "A hero laptop spans roughly 72-88% of canvas width in the middle band. Headline and period sit above; a short verified outcome line and brand footer sit below. The laptop is the unmistakable focal object.",
                "The complete approved chart fills the laptop's inner display with correct perspective and bezel clipping. Use a restrained market-interface frame only when present in the sample; never shrink the chart into a small widget.",
                "Large two-level headline, readable outcome sentence, chart labels legible inside the screen, and a clear lower footer/domain.",
                "Preserve laptop pose, crop, stage depth, and screen-to-body ratio. Re-skin the environment and accents with the theme-owner palette, motifs, logo, and domain.",
                "Photoreal metal laptop, clean keyboard edge, cinematic yet restrained lighting, luminous accurate screen, premium launch-campaign finish.",
                "No chart floating over the laptop; no tiny laptop; no giant dead lower field; no generic web dashboard; no unrelated sidebars or social feed; no illegible axes.",
            ),
            "laptop-editorial": _variant(
                "Calm editorial laptop composition with exact chart placement.",
                "A frontal or gently angled laptop occupies the upper-middle field. A strong headline block and concise explanation use the remaining space, followed by a deliberate brand footer or compact fact strip.",
                "The full chart is the dominant screen content, inset correctly inside the display and sized for readable axes, dates, lines, legend, and endpoints.",
                "Elegant headline hierarchy with generous line spacing; small copy is kept to one concise sentence; footer never becomes microtext.",
                "Keep the sample's quiet geometry. Translate surface colors, atmospheric arcs or motifs, logo, and footer through the theme owner's Art Director profile.",
                "Refined editorial lighting, soft dimensionality, controlled texture, exact screen alignment, print-quality typography.",
                "No extra statistic slab unless in sample; no decorative database icons; no chart outside display; no excessive empty space; no web-browser chrome invented by the model.",
            ),
            "laptop-wide": _variant(
                "Wide multi-series dashboard laptop with strong horizontal information flow.",
                "A wide laptop or monitor-like laptop fills the principal horizontal band. Headline lives above or to one side; a compact result strip and footer complete the composition without competing with the screen.",
                "The approved multi-series chart expands across the screen aperture. Legend and endpoint summary remain inside or immediately adjacent according to the sample, with every series visible.",
                "Wide concise headline, compact series labels, readable date and value axes, and a firm footer lockup.",
                "Theme-owner colors control the stage and frame accents; chart-series colors remain factual and distinct. Preserve sample proportions and wide-screen rhythm.",
                "Crisp widescreen product visualization, subtle depth, high contrast without glare, professional financial-editorial finish.",
                "No cramped sidebar; no second chart; no miniature lines; no reordering series; no arbitrary tilt; no oversized footer band.",
            ),
        },
    },
    "growth": {
        "name": "Growth Spotlight",
        "variants": {
            "growth-card": _variant(
                "Dramatic coin-owned editorial story with a compact protected performance card and exact result strips.",
                "Reserve the upper 28-34% for one dramatic owner-specific environment plus a compact two-to-three-line editorial headline. The approved chart panel occupies roughly 30-38% of the canvas height in the middle-lower field. Exact result strips and a quiet official footer complete the bottom 20-25%.",
                "Scale the complete approved chart proportionally into one compact panel with exact axes, dates, and its single approved legend. Present start price, end price, and movement in separate protected result strips outside the plotting area. Never recreate the chart title or legend elsewhere.",
                "Compact editorial headline, no more than three lines; medium chart title; clear result-strip values; small but readable axes and deliberate footer. The headline must not overpower the scene or force the chart downward.",
                "Preserve the sample's information order but replace its literal environment with one approved dramatic scene belonging to the selected owner. Use owner colors for atmosphere, card edge, highlights, logo, and footer while series colors remain exact.",
                "Cinematic campaign depth in the background, controlled localized light behind the hero subject, premium molded chart card, crisp typography, and restrained borders without a halo around the full chart.",
                "No flat empty black field; no chart taller than 38% of the canvas; no duplicate chart title or legend; no multiple tilted cards; no chart separated from its card; no invented rank, alert controls, glow box, or generic crypto decoration.",
            ),
            "growth-hero": _variant(
                "Large chart-led performance hero with one unmistakable market outcome.",
                "A bold headline and hero number occupy the top third; the approved chart fills a strong central panel; the logo/footer anchors the bottom. Visual energy follows the real movement direction.",
                "The complete chart is dominant and protected, with endpoint emphasis derived only from the verified data. Supporting data remains secondary.",
                "Very large headline or movement, concise supporting sentence, readable chart labels, restrained footer.",
                "Translate background gradient, motif, highlights, and logo to the owner while retaining factual line colors and green/red semantics.",
                "Campaign-scale polish, controlled luminous accents, strong depth separation, sharp data visualization.",
                "No device mockup; no decorative chart redraw; no extra market claims; no oversized empty lower third; no low-contrast labels.",
            ),
            "growth-milestone": _variant(
                "Spacious editorial milestone composition with an elegant protected chart panel.",
                "A milestone statement and exact value lead the upper half. A refined chart panel occupies the middle-lower band, followed by a quiet official footer.",
                "The approved chart remains intact inside a calm panel; endpoint values and the selected period form the supporting evidence.",
                "Elegant large milestone copy, one accent value, restrained chart labels, spacious but readable footer.",
                "Use brand-owned materials and motifs with ample negative space, but keep enough scale that chart and text remain legible on mobile.",
                "Luxury editorial finish, fine borders, soft controlled light, precise spacing, no visual noise.",
                "No tiny chart; no excessive blank canvas; no celebratory icons unrelated to the brand; no arbitrary percentage badge.",
            ),
        },
    },
    "contrast": {
        "name": "Performance Contrast",
        "variants": {
            "contrast-duel": _variant(
                "Winner-versus-loser duel with exact evidence in balanced opposing panels.",
                "Two principal opposing panels or shapes dominate the central field, with a decisive headline above and official footer below. For more series, retain the two leaders and place the remainder in a compact ranked strip.",
                "Each principal panel contains its verified mini trend; a protected combined chart may appear only if the sample includes it. Exact start/end and movement sit next to their corresponding asset.",
                "Outcome headline is largest; asset symbols and movement are bold; prices and footer remain clearly readable.",
                "The theme owner controls the base world; positive and negative contrast uses semantic green/red without allowing a comparison asset to own the background.",
                "Dramatic but disciplined contrast, crisp glow limited to endpoints, premium dark editorial finish.",
                "No invented winner; no empty ghost cards; no mismatched mini-chart; no more than one headline; no decorative price labels.",
            ),
            "contrast-intersecting": _variant(
                "Single combined comparison chart with exact endpoint callouts and a clear outcome headline.",
                "A large rounded plotting field occupies the center. Headline above; start/end callouts attach to real line endpoints; logo/domain anchor the bottom.",
                "Use the approved combined chart as one protected unit. Callouts may be added only for exact supplied endpoint values and must not cover lines or axes.",
                "Large editorial conclusion, medium endpoint callouts, clear legend and axes, quiet footer.",
                "Translate the container, background atmosphere, and footer to the owner theme; preserve each line's stable asset color.",
                "Sharp chart-first visualization, subtle dimensional frame, restrained cinematic illumination.",
                "No separated cards; no redrawn line shapes; no detached legend; no callout without verified value; no large empty half-canvas.",
            ),
            "contrast-scoreboard": _variant(
                "Ranked cinematic scoreboard backed by compact verified chart evidence.",
                "A ranked result stack occupies one side or upper band; a compact but complete chart occupies the complementary panel. Headline and footer close the hierarchy.",
                "The approved chart remains complete. Ranking order follows verified movement only; all selected assets appear once with exact change and endpoint values.",
                "Bold rank numbers and headline, medium asset rows, compact readable chart labels, official footer.",
                "Owner identity shapes the scoreboard surfaces, border accents, motifs, logo, and domain; comparison colors remain confined to their rows and lines.",
                "Broadcast-grade scoreboard precision, rich material hierarchy, sharp type and data, controlled highlights.",
                "No fabricated ranks or trophies; no omitted series; no tiny chart; no sports styling unless the sample shows it; no duplicate assets.",
            ),
        },
    },
    "separated": {
        "name": "Separated Performance",
        "variants": {
            "separated-grid": _variant(
                "Responsive exact asset-card grid with a shared comparison chart.",
                "One equal-weight card per asset forms a clean one-to-three-column grid in the upper-middle field. A full-width protected combined chart sits beneath the cards, followed by the logo/domain footer.",
                "Every card contains symbol, exact movement, start/end prices, and its verified mini trend. The lower approved chart shows all series intact with dates, axes, and legend.",
                "Centered or left-aligned outcome headline, bold asset labels and movements, readable card facts, clear chart labels and footer.",
                "Owner theme controls canvas, card surfaces, outlines, official logo, and footer. Each asset preserves its assigned line and marker color.",
                "Balanced premium modular system, crisp aligned cards, subtle depth, precise shared baseline, publication-grade sharpness.",
                "No tilted cards; no different card sizes without sample evidence; no giant empty lower field; no missing shared chart; no micro footer; no invented logos.",
            ),
            "separated-stacked": _variant(
                "Offset connected asset cards with exact trends in a calm premium field.",
                "Cards follow the sample's measured vertical or diagonal stack with consistent overlap and a visible reading order. Headline and result statement balance the stack; footer closes the composition.",
                "Each card includes the correct mini trend and exact values. If a combined chart exists in the sample, it remains a separate protected panel and is never covered by the stack.",
                "Strong headline, consistent asset-card typography, concise conclusion, visible brand footer.",
                "Use owner surfaces, motif lines, and lighting to connect the stack. Keep factual line colors distinct.",
                "Refined layered cards, soft dimensional shadow, strict alignment, clean editorial finish.",
                "No random rotation; no unreadable overlap; no omitted asset; no empty decorative card; no separated chart floating without frame.",
            ),
            "separated-orbiting": _variant(
                "Dynamic modular asset cards arranged around a shared market story.",
                "A protected central chart or central owner motif anchors the composition while one factual card per asset occupies fixed orbital positions. The headline leads and the footer remains quiet but legible.",
                "All mini trends and the shared chart derive from the approved chart. Card positions may be dynamic, but they cannot obscure chart axes, dates, legend, or each other.",
                "Editorial headline, compact cards with bold movements, clear central legend, official footer.",
                "Owner motifs may guide the orbital paths; palette and atmosphere belong to the owner, while data marks retain series colors.",
                "High-end modular motion implied in a still image, crisp edges, disciplined depth, no clutter.",
                "No chaotic scatter; no duplicate or empty card; no data outside protected modules; no illegible small type; no excessive rotations.",
            ),
        },
    },
    "combined": {
        "name": "Combined Performance",
        "variants": {
            "combined-rounded": _variant(
                "Large rounded multi-series chart with exact callouts and horizon-like depth.",
                "A single rounded chart panel occupies a controlled 40-48% of the canvas, leaving a substantial owner-specific cinematic environment around it. Outcome headline sits above; exact endpoint callouts live inside the panel; official logo and footer sit below.",
                "Use the approved chart in full as the panel content. Preserve every line, date, axis, legend, and relative shape; endpoint callouts may repeat exact metadata only.",
                "Bold concise headline, medium callouts, highly readable axes and legend, visible footer/domain.",
                "Owner theme shapes the background, rounded frame, horizon light, logo, and footer; chart colors remain asset-specific.",
                "Premium dark or light chart surface appropriate to the owner, fine grid, clean depth, sharp vector-like data.",
                "No device mockup; no second chart; no chart larger than half the canvas; no dead lower half; no invented ticks or values; no duplicate legend.",
            ),
            "combined-minimal": _variant(
                "Quiet chart-first spotlight with restrained information and generous purposeful space.",
                "One clean chart panel sits at visual center with headline and one result line above and a small official footer below. Negative space frames the data rather than dwarfing it.",
                "Approved chart is complete and large enough for social viewing. The legend and axes remain intact; no ornamental data modules are added.",
                "Elegant headline, one concise support sentence, clear chart labels, modest but readable footer.",
                "Owner palette appears in the field, one accent, logo and domain. Motifs are faint and never compete with data.",
                "Museum-clean editorial polish, precise spacing, subtle texture, excellent contrast and sharpness.",
                "No device; no cards; no huge empty lower third; no micro-chart; no glow-heavy crypto clichés; no extra claims.",
            ),
            "combined-editorial": _variant(
                "Typography-led editorial chart with exact result callouts.",
                "A strong headline block occupies the upper or left field while one protected chart fills the complementary majority. Exact result callouts and footer follow the sample's grid.",
                "The complete approved chart stays inside one defined panel. Endpoint annotations use supplied facts and remain secondary to the chart geometry.",
                "Expressive but disciplined headline, medium supporting result, readable chart, deliberate brand footer.",
                "Use owner typography mood, colors, motifs, logo, and domain without changing the sample's grid or allowing comparison assets to color the environment.",
                "Contemporary magazine-finance finish, crisp type, precise panel edges, controlled depth and contrast.",
                "No device unless visible in sample; no multiple chart panels; no improvised labels; no tiny chart; no off-grid footer; no large unused region.",
            ),
        },
    },
}


_ALLOWED_DEPTH = {"flat editorial", "soft dimensional", "cinematic dimensional"}
_ALLOWED_LIGHTING = {"quiet studio", "directional editorial", "cinematic atmospheric"}
_ALLOWED_DENSITY = {"minimal", "balanced", "information-rich"}


_CHART_SCALE_RULES = {
    "phone": "Keep the approved chart inside the device screen; the phone itself may remain prominent, but preserve meaningful owner-scene atmosphere around the device.",
    "laptop": "Keep the approved chart inside the laptop screen; the laptop may remain prominent, but preserve a visible owner-scene environment around the hardware.",
    "growth": "The chart panel must occupy about 30-38% of the canvas height and no more than 42% of the total visual area. Reserve the upper field for the dramatic owner scene and editorial headline, then keep result strips and footer clearly separate below.",
    "contrast": "The protected chart evidence must occupy about 32-42% of the total visual area. Reserve the remaining space for the owner scene, decisive headline, exact result modules, and footer.",
    "separated": "All chart modules together must occupy about 32-42% of the total visual area. Keep each chart readable while reserving substantial space for the owner scene, asset facts, headline, and footer.",
    "combined": "The single approved chart panel must occupy about 38-48% of the total visual area and never exceed half of the canvas. The dramatic owner scene, headline, exact result summary, and footer must remain visibly substantial.",
}


def _chart_scale_rule(template: dict) -> str:
    return _CHART_SCALE_RULES.get(
        template.get("categoryId"),
        "Keep the approved chart compact but fully readable, using no more than half of the total visual area.",
    )


def _approved_background_scenes(theme_owner: dict) -> list[str]:
    scenes = [
        str(scene).strip()
        for scene in (theme_owner.get("backgroundScenes") or [])
        if str(scene).strip()
    ]
    if scenes:
        return scenes[:6]
    fallback = str(theme_owner.get("imagePrompt") or "premium coin-owned cinematic environment").strip()
    return [fallback]


def _fallback_background_scene(theme_owner: dict, series: list[dict]) -> str:
    """Pick a safe owner scene when the Art Director is unavailable.

    Registry scene order is aspirational/positive, resilient/negative, then
    neutral/mixed. The choice affects atmosphere only, never market facts.
    """
    scenes = _approved_background_scenes(theme_owner)
    owner_id = str(theme_owner.get("id") or "").strip().lower()
    owner_symbol = str(theme_owner.get("symbol") or "").strip().upper()
    owner = next((
        item for item in series
        if str(item.get("tokenId") or "").strip().lower() == owner_id
        or str(item.get("symbol") or "").strip().upper() == owner_symbol
    ), series[0] if series else {})
    try:
        movement = float(owner.get("changePercent") or 0)
    except (TypeError, ValueError):
        movement = 0
    index = 0 if movement > 0.05 else 1 if movement < -0.05 else 2
    return scenes[min(index, len(scenes) - 1)]


def resolve_analytics_template(category_id: str, variant_id: str) -> dict:
    category = ANALYTICS_TEMPLATE_FAMILIES.get(str(category_id or "").strip())
    if not category:
        raise ValueError("Unknown analytics publishing category.")
    variant_contract = category["variants"].get(str(variant_id or "").strip())
    if not variant_contract:
        raise ValueError("The selected analytics variant does not belong to its publishing category.")
    return {
        "categoryId": category_id,
        "categoryName": category["name"],
        "variantId": variant_id,
        "variantRule": variant_contract["summary"],
        "contract": deepcopy(variant_contract),
    }


def _clean_series(series_metadata) -> list[dict]:
    clean = []
    for item in series_metadata or []:
        if not isinstance(item, dict) or not str(item.get("symbol") or "").strip():
            continue
        clean_item = {
            "symbol": str(item.get("symbol") or "").strip().upper(),
            "name": str(item.get("name") or item.get("symbol") or "").strip(),
            "role": str(item.get("role") or "comparison").strip(),
            "startPrice": item.get("startPrice"),
            "endPrice": item.get("endPrice"),
            "changePercent": item.get("changePercent"),
            "coverageStart": item.get("coverageStart"),
            "coverageEnd": item.get("coverageEnd"),
        }
        if item.get("color"):
            clean_item["color"] = normalize_hex_color(item.get("color"), "series color")
        clean.append(clean_item)
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
    contract = template.get("contract") or {}
    return {
        "family": category,
        "variant": template["variantId"],
        "concept": f'{theme_owner["name"]} verified market editorial',
        "sample_fidelity": "binding",
        "device_strategy": device,
        "reference_analysis": contract.get("summary") or template["variantRule"],
        "composition_map": contract.get("skeleton") or "headline, supporting statement, protected chart, exact result summary, brand footer",
        "chart_integration": contract.get("chart") or "place the complete approved chart inside the sample's reserved chart aperture",
        "typography_system": contract.get("typography") or "large readable headline, concise support copy, legible chart labels, clear footer",
        "data_hierarchy": "show the supplied headline first, then verified comparison context, then the complete chart, exact legends and result summary",
        "brand_translation": contract.get("brandTranslation") or "preserve template geometry while translating palette, logo, domain and motifs to the theme owner",
        "materials_and_finish": contract.get("finish") or "premium publication-ready finish with crisp text and chart detail",
        "logo_footer_system": f'use only the official {theme_owner["name"]} logo and exact footer {theme_owner["footer"]} in the sample-defined positions',
        "quality_control": "all content must remain large, sharp and readable at social-feed size; use the sample's canvas coverage and avoid accidental dead space",
        "forbidden_changes": contract.get("forbidden") or "no invented data, extra panels, layout drift, detached charts or generic crypto decoration",
        "chart_strategy": contract.get("chart") or "place the complete approved chart inside the sample's reserved chart aperture",
        "layout_hierarchy": contract.get("skeleton") or "headline, supporting statement, protected chart, exact result summary, brand footer",
        "background_scene": _fallback_background_scene(theme_owner, series),
        "chart_scale": _chart_scale_rule(template),
        "lighting": "cinematic atmospheric" if category in {"phone", "laptop", "contrast"} else "directional editorial",
        "depth": "cinematic dimensional" if category in {"phone", "laptop"} else "soft dimensional",
        "density": density,
        "brand_expression": ", ".join(theme_owner.get("motifs") or []),
        "negative_space": "preserve the sample's breathing room around the headline, chart, and footer; give the selected dramatic owner scene enough visible area to create depth and influence without reducing readability",
        "factual_protection": "all visible chart geometry and market facts come only from the approved chart and supplied metadata",
    }


def call_analytics_art_director(article, copy_text, theme_owner, profile, template,
                                output_dimensions, series_metadata, creative_direction="",
                                sample_reference="", chart_style=None):
    """Stage 1: ask the same editorial model used by Multimedia for a JSON brief."""
    series = _clean_series(series_metadata)
    chart_style = normalize_chart_style(chart_style)
    profile_style = profile.get("frozen_style") or {}
    background_scenes = _approved_background_scenes(theme_owner)
    chart_scale = _chart_scale_rule(template)
    system_prompt = (
        f'You are the specialist Market Analytics Art Director for {theme_owner["name"]}. '
        'You do not invent market data and you do not write a short generic image prompt. You create a complete production '
        'brief for a deterministic prompt assembler, exactly as a senior campaign Art Director briefs an image-production team. '
        'You are given the chosen permanent sample as a visual reference. Inspect it carefully. The sample is a BINDING '
        'template family, not a loose moodboard. Describe its real information architecture, module sizes, alignment, chart '
        'treatment, headline treatment, legend placement, device/card geometry, footer, materials, and finish. '
        'The final image must remain recognizably the same publishing design while its palette, logo, footer, copy, and '
        'chart content adapt to the selected coin and verified dataset. The approved factual chart must be complete, sharp, '
        'readable, and placed inside the sample\'s chart/device aperture. Never move a phone or laptop chart outside its screen. '
        'There is NO captured composition reference. Your written production brief is therefore the complete construction '
        'specification for the final card. Do not rely on unstated visual assumptions. Describe the card from the canvas inward: '
        'major zones and approximate coverage, alignment grid, device or card silhouette, chart aperture, headline and supporting-copy '
        'placement, typography hierarchy, legends and verified facts, logo and footer placement, negative space, materials, depth, '
        'lighting, brand translation, and every prohibited change.\n\n'
        f'BRAND OWNER: {theme_owner["name"]}\n'
        f'PALETTE: {json.dumps(theme_owner["theme"], ensure_ascii=False)}\n'
        f'MOTIFS: {", ".join(theme_owner.get("motifs") or [])}\n'
        f'BRAND DIRECTION: {theme_owner["imagePrompt"]}\n'
        f'APPROVED OWNER BACKGROUND SCENES: {json.dumps(background_scenes, ensure_ascii=False)}\n'
        'BACKGROUND SELECTION RULE: choose exactly one approved owner background scene and return that complete scene text '
        'verbatim in background_scene. Select the scene whose emotional direction best fits the verified owner movement and '
        'headline. Preserve the sample background\'s spatial role, crop, depth, and negative-space behavior, but do not copy the '
        'example coin\'s literal world. The selected owner scene must be visibly present and dramatic, never reduced to a flat '
        'black field, plain gradient, uncontrolled glow, generic dashboard, or decorative crypto wallpaper. Keep a quiet local '
        'area behind typography and the protected chart.\n'
        f'IMMUTABLE CHART SCALE RULE: {chart_scale}\n'
        'This revised chart scale is a deliberate family constraint and overrides any looser interpretation that would let the '
        'chart dominate the poster. The chart remains fully readable and factual, but the owner scene and editorial story must '
        'have meaningful visual presence.\n'
        f'FROZEN PROFILE STYLE: {json.dumps(profile_style, ensure_ascii=False)}\n\n'
        f'TEMPLATE FAMILY: {template["categoryName"]}\n'
        f'EXACT VARIANT: {template["variantId"]}\n'
        f'VARIANT CONTRACT: {json.dumps(template.get("contract") or {}, ensure_ascii=False)}\n\n'
        'REFERENCE INTERPRETATION RULES: Reference geometry and hierarchy stay fixed. The selected brand owner changes only '
        'the palette, official logo/domain, approved motifs, materials and atmosphere. Market data changes only headline, '
        'supporting text, chart, legends, endpoint values and verified statistics. If the sample contains separate performance '
        'cards, keep series separate. If it contains one combined chart, keep them combined. If it contains a phone or laptop, '
        'the complete chart and legends belong inside the screen. Do not turn a family into another family. The approved chart '
        'already contains its title and selected legend; do not recreate either outside it or add a second legend inside it.\n\n'
        'BRIEF DETAIL RULES: reference_analysis must explain the sample\'s visible construction. composition_map and layout_hierarchy '
        'must describe the canvas in reading order with relative proportions and alignment. device_strategy must specify silhouette, '
        'pose, crop, bezel or card boundaries, and screen/aperture behavior. typography_system must specify headline scale, line count, '
        'alignment, supporting-copy relationship, factual-label scale, and footer hierarchy. chart_integration and chart_strategy must '
        'state exactly where the complete chart sits and how it is clipped without being redrawn. data_hierarchy must list which supplied '
        'facts appear and their order. brand_translation, materials_and_finish, lighting, depth, negative_space, logo_footer_system, and '
        'quality_control must together make the brief executable without another layout image. forbidden_changes must be exhaustive.\n\n'
        'Return ONLY one JSON object with exactly these keys: family, variant, concept, sample_fidelity, '
        'reference_analysis, composition_map, device_strategy, chart_integration, chart_strategy, typography_system, '
        'data_hierarchy, layout_hierarchy, background_scene, chart_scale, lighting, depth, density, brand_translation, '
        'brand_expression, materials_and_finish, logo_footer_system, negative_space, quality_control, '
        'forbidden_changes, factual_protection. '
        'sample_fidelity must be "binding". lighting must be one of: quiet studio, directional editorial, '
        'cinematic atmospheric. depth must be one of: flat editorial, soft dimensional, cinematic dimensional. '
        'density must be one of: minimal, balanced, information-rich. chart_scale must repeat the immutable chart scale rule exactly.'
    )
    user_prompt = (
        f'Exact headline: {article.get("title", "")}\n'
        f'Exact supporting text: {copy_text}\n'
        f'Canvas: {output_dimensions.get("width", 1080)}x{output_dimensions.get("height", 1350)}\n'
        f'Verified series: {json.dumps(series, ensure_ascii=False)}\n'
        f'Approved chart presentation: {json.dumps(chart_style, ensure_ascii=False)}\n'
        f'Additional creative direction: {creative_direction or "none"}\n\n'
        'Design the complete visual production brief now. State exactly which elements are replaced with the new headline, '
        'support copy, verified chart, legends, prices, movements, logo and footer, and which sample geometry must never move. '
        'Keep all factual content protected.'
    )
    user_content = user_prompt
    if sample_reference:
        user_content = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": sample_reference}},
        ]
    return openrouter_chat(
        EDITORIAL_MODELS["gpt"]["id"],
        [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
        0.55,
        2600,
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
        "concept", "reference_analysis", "composition_map", "device_strategy", "chart_integration",
        "chart_strategy", "typography_system", "data_hierarchy", "layout_hierarchy",
        "brand_translation", "brand_expression", "materials_and_finish", "logo_footer_system",
        "negative_space", "quality_control", "forbidden_changes", "factual_protection",
    ):
        value = str(raw_brief.get(key) or "").strip()
        if value:
            brief[key] = value[:1600]
    # Background subjects are controlled by the selected coin registry. The Art
    # Director may choose among them but cannot replace them with a generic scene.
    requested_scene = str(raw_brief.get("background_scene") or "").strip().casefold()
    for approved_scene in _approved_background_scenes(theme_owner):
        if requested_scene == approved_scene.casefold():
            brief["background_scene"] = approved_scene
            break
    brief["chart_scale"] = _chart_scale_rule(template)
    brief["sample_fidelity"] = "binding"
    brief["lighting"] = raw_brief.get("lighting") if raw_brief.get("lighting") in _ALLOWED_LIGHTING else fallback["lighting"]
    brief["depth"] = raw_brief.get("depth") if raw_brief.get("depth") in _ALLOWED_DEPTH else fallback["depth"]
    brief["density"] = raw_brief.get("density") if raw_brief.get("density") in _ALLOWED_DENSITY else fallback["density"]
    # These two clauses are non-negotiable even if the model omitted them.
    brief["chart_strategy"] += "; preserve the full approved chart without redrawing or moving it outside the aperture"
    brief["chart_integration"] += "; use only the supplied approved chart and preserve its complete factual content"
    brief["chart_integration"] += "; use exactly one chart title and exactly the approved legend already inside the chart"
    brief["forbidden_changes"] = fallback["forbidden_changes"]
    brief["factual_protection"] = fallback["factual_protection"]
    return brief


def assemble_analytics_prompt(brief, template, theme_owner, profile, article, copy_text,
                              output_dimensions, series_metadata, chart_style=None) -> str:
    """Stage 2: deterministically assemble the final two-reference prompt."""
    series = _clean_series(series_metadata)
    chart_style = normalize_chart_style(chart_style)
    width = int(output_dimensions.get("width") or 1080)
    height = int(output_dimensions.get("height") or 1350)
    facts = json.dumps(series, ensure_ascii=False, separators=(",", ":"))
    theme = json.dumps(theme_owner["theme"], ensure_ascii=False, separators=(",", ":"))
    footer = theme_owner["footer"]
    headline = str(article.get("title") or "").strip()
    contract = json.dumps(template.get("contract") or {}, ensure_ascii=False)
    return (
        f'Create one finished {width}x{height} premium financial social post from exactly TWO ordered references. '
        'REFERENCE 1 is the permanent APPROVED PUBLISHING SAMPLE and is the binding composition contract. Match its '
        'camera, crop, device/card silhouette, chart aperture, information hierarchy, spacing, visual rhythm, lighting '
        'quality, and premium finish. Do not reinterpret it as a different layout. Replace only the example coin identity, '
        'palette, copy, footer, and market content. '
        'REFERENCE 2 is the AUTHORITATIVE APPROVED FACTUAL CHART. Insert this complete chart into the reserved aperture '
        'defined by Reference 1 and the written production brief. For phone and laptop families the entire chart MUST be physically inside the device '
        'screen, clipped by the inner screen boundary with realistic screen perspective and reflections. Never float it in '
        'front of, behind, beside, or outside the device. For non-device families keep it inside the sample\'s protected chart '
        'panel. Preserve all chart lines, axes, dates, legends, labels, relative geometry, and proportions. Do not redraw, '
        'simplify, recolor, crop, blur, or fabricate the chart. '
        f'TEMPLATE FAMILY: {template["categoryName"]}. EXACT VARIANT: {template["variantId"]}. '
        f'FULL IMMUTABLE FAMILY CONTRACT: {contract}. '
        f'FULL ART DIRECTOR PRODUCTION BRIEF: {json.dumps(brief, ensure_ascii=False)}. '
        f'CANVAS AND MODULE MAP: {brief["composition_map"]}. '
        f'LAYOUT AND READING ORDER: {brief["layout_hierarchy"]}. '
        f'DEVICE OR CARD CONSTRUCTION: {brief["device_strategy"]}. '
        f'TYPOGRAPHY SYSTEM: {brief["typography_system"]}. '
        f'INFORMATION HIERARCHY: {brief["data_hierarchy"]}. '
        f'CHART APERTURE AND INTEGRATION: {brief["chart_integration"]}. '
        f'CHART PROTECTION STRATEGY: {brief["chart_strategy"]}. '
        f'CHART SCALE LIMIT: {brief["chart_scale"]}. This scale limit is mandatory even if Reference 1 could be interpreted '
        'more loosely; the chart must remain fully legible but must not dominate the full poster. '
        f'SELECTED DRAMATIC OWNER BACKGROUND: {brief["background_scene"]}. Build this actual scene as the poster environment, '
        'preserving the reference\'s scene placement and negative-space behavior while translating the literal subject to the '
        'selected coin. The scene must be clearly visible around the smaller chart, not replaced by flat black, a plain gradient, '
        'a full-card halo, generic crypto wallpaper, or empty space. '
        f'BRAND TRANSLATION: {brief["brand_translation"]}. '
        f'BRAND EXPRESSION: {brief["brand_expression"]}. '
        f'MATERIALS, LIGHTING, AND DEPTH: {brief["materials_and_finish"]}; {brief["lighting"]}; {brief["depth"]}. '
        f'LOGO AND FOOTER SYSTEM: {brief["logo_footer_system"]}. '
        f'NEGATIVE SPACE: {brief["negative_space"]}. '
        f'QUALITY CONTROL: {brief["quality_control"]}. '
        f'FORBIDDEN CHANGES: {brief["forbidden_changes"]}. '
        f'FACTUAL PROTECTION: {brief["factual_protection"]}. '
        f'BRAND OWNER: {theme_owner["name"]}. BRAND PALETTE: {theme}. '
        f'BRAND MOTIFS: {", ".join(theme_owner.get("motifs") or [])}. '
        f'BRAND ART DIRECTION: {theme_owner["imagePrompt"]}. '
        f'EXACT HEADLINE: "{headline}". EXACT SUPPORTING TEXT: "{copy_text}". '
        f'EXACT FOOTER/DOMAIN: "{footer}". VERIFIED SERIES METADATA: {facts}. '
        f'APPROVED CHART PRESENTATION: {json.dumps(chart_style, ensure_ascii=False, separators=(",", ":"))}. '
        'Preserve the approved background, series colors, line weight, markers, grid strength, legend position, and legend format '
        'when integrating the chart into the publishing design. '
        'EXECUTION ORDER: first reproduce Reference 1 composition and major module proportions; second apply the brand-owner '
        'theme; third replace the sample headline/supporting text with the supplied exact copy; fourth place Reference 2 into '
        'the defined chart area; fifth rebuild exact legends and verified result labels from the supplied metadata; sixth add '
        'the official logo/footer in the sample-defined position; finally apply premium lighting and finish. Major modules '
        'must cover the canvas with the same confidence as Reference 1. Do not create a large unintended empty region. The '
        'approved chart already contains its chart title and selected legend: show each exactly once and never add a duplicate '
        'title, detached legend, tooltip, or second legend. '
        'For separate-card variants, keep separate mini charts plus the sample-defined combined factual view when specified. '
        'For combined-chart variants, use one combined chart only. Comparison assets may keep their own line/marker colors '
        'but may never control the background theme. '
        'Do not invent or substitute any price, percentage, ticker, date, logo, domain, legend, axis, or claim. Do not add '
        'CoinMarketCap branding, a generic website dashboard, extra cards, a second chart, placeholder copy, watermarks, '
        'editing handles, or mockup annotations. The only visible text may be the supplied headline, supporting text, footer, '
        'and factual labels already present in the approved chart/metadata. Return one publication-ready image only.'
    )
