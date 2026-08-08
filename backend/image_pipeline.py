"""Two-stage image pipeline: Art Director LLM (Stage 1) -> brief validation +
deterministic prompt assembler (Stage 2). Holds the in-memory anti-repetition
brief cache (resets on restart).
"""
import re

from config import (ART_DIRECTOR_TEMPERATURE, ART_DIRECTOR_MAX_TOKENS, _CORE_AXES,
                    _BANNED_SUBJECT_TERMS, _WALLET_ADDRESS_RE, EDITORIAL_MODELS)
from llm import openrouter_chat


# ── Anti-repetition memory for the Art Director (in-memory, resets on restart) ──
_RECENT_BRIEFS = {}

def _remember_brief(media, brief, profile):
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    lst = _RECENT_BRIEFS.setdefault(media, [])
    lst.append({
        'family': brief.get('family'),
        env_axis: brief.get(env_axis),
        cam_axis: brief.get(cam_axis),
        'scene': (brief.get('subject_scene') or '')[:140],
        **{axis: brief.get(axis) for axis in _extra_axes(profile)},
        **{field: brief.get(field) for field in profile.get('passthrough_fields', [])},
    })
    del lst[:-10]
def _extra_axes(profile):
    return [k for k in profile['axes'] if k not in profile.get('core_axes', _CORE_AXES)]


def _active_families(profile):
    families = profile['families']
    if profile.get('meme_enabled', True) or 'meme' not in families:
        return families
    return {k: v for k, v in families.items() if k != 'meme'}


def _build_brief_schema(profile):
    axes = profile['axes']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    family_enum = ' | '.join(_active_families(profile).keys())
    env_enum    = ' | '.join(axes[env_axis].keys())
    camera_enum = ' | '.join(axes[cam_axis].keys())
    energy_enum = ' | '.join(axes[nrg_axis].keys())
    mood_enum   = ' | '.join(axes[mood_axis].keys())
    max_words   = profile.get('headline_max_words', 6)
    case_note   = 'UPPERCASE' if profile.get('headline_uppercase', True) else 'mixed case'

    prefix_lines = ''
    for field, hint in profile.get('brief_prefix_schema', {}).items():
        prefix_lines += f'  "{field}": "{hint}",\n'

    extra_field_lines = ''
    axis_optional = profile.get('axis_optional', {})
    for axis in _extra_axes(profile):
        enum = ' | '.join(axes[axis].keys())
        if axis_optional.get(axis):
            enum += ' | none'
        extra_field_lines += f'  "{axis}": "{enum}",\n'

    for field, description in profile.get('passthrough_field_schema', {}).items():
        extra_field_lines += f'  "{field}": "{description}",\n'

    return f"""
Respond with ONLY a single JSON object, no markdown fences and no commentary, matching this schema exactly:
{{
{prefix_lines}  "family": "{family_enum}",
  "headline": "<= {max_words} words, {case_note}",
  "data_elements": [{{"value": "...", "label": "..."}}],
  "{env_axis}": "{env_enum}",
  "{cam_axis}": "{camera_enum}",
  "{nrg_axis}": "{energy_enum}",
  "{mood_axis}": "{mood_enum}",
{extra_field_lines}  "subject_scene": "1-3 sentences describing the central subject and any in-scene text exactly as it should appear. Never use the words text, label, logo or watermark, and never mention brand names."
}}
""".strip()


def _build_art_director_system_prompt(profile, recent, brand_mode=True):
    fs = profile['frozen_style']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    style_block = (
        f"Format: {fs['format']}.\n"
        f"Palette: {fs['palette']}.\n"
        f"Materials: {fs['materials']}.\n"
        f"Rendering: {fs['rendering']}.\n"
        f"Background vocabulary: {fs['background_vocab']}.\n"
        f"Headline zone: {fs['headline_zone']}.\n"
        f"Never: {fs['never']}."
    )

    metaphor_lines = '\n'.join(f"- {k}: {v}" for k, v in profile['metaphors'].items())
    approved_directions = profile.get('approved_directions', {})
    approved_section = ''
    if approved_directions:
        approved_lines = '\n'.join(
            f"- {key}: {description}" for key, description in approved_directions.items()
        )
        approved_section = (
            "\n\nAPPROVED CAMPAIGN DIRECTIONS (creative anchors, not templates to copy):\n"
            + approved_lines
        )

    families_block = '\n'.join(
        f"- {key} ({fam['name']}): {fam['skeleton']} Text policy: {fam['text_policy']} "
        f"Default axes: {env_axis}={fam['default_axes'][env_axis]}, "
        f"{cam_axis}={fam['default_axes'][cam_axis]}, {nrg_axis}={fam['default_axes'][nrg_axis]}. "
        f"Max data_elements: {fam['data_budget']}."
        for key, fam in _active_families(profile).items()
    )

    axes = profile['axes']
    axis_optional = profile.get('axis_optional', {})
    axes_block = (
        f"{env_axis}: " + ', '.join(axes[env_axis].keys()) + "\n"
        f"{cam_axis}: " + ', '.join(axes[cam_axis].keys()) + "\n"
        f"{nrg_axis}: " + ', '.join(axes[nrg_axis].keys()) + "\n"
        f"{mood_axis}: " + ', '.join(axes[mood_axis].keys())
    )
    extra_axes = _extra_axes(profile)
    for axis in extra_axes:
        enum = ', '.join(axes[axis].keys())
        if axis_optional.get(axis):
            enum += ', none'
        axes_block += f"\n{axis}: {enum}"

    passthrough_fields = profile.get('passthrough_fields', [])
    if recent:
        recent_lines = '\n'.join(
            f"- family={r['family']}, {env_axis}={r.get(env_axis)}, {cam_axis}={r.get(cam_axis)}"
            + ''.join(f", {axis}={r.get(axis)}" for axis in extra_axes)
            + ''.join(f", {field}={r.get(field)}" for field in passthrough_fields)
            + f", scene=\"{r['scene']}\""
            for r in recent
        )
        recent_block = (
            "Recently used briefs (most recent last) -- choose a different combination, do not "
            "reuse these scene concepts:\n" + recent_lines + "\n\n"
            + profile['anti_repetition_rules']
        )
    else:
        recent_block = "No recent briefs yet -- any combination is fine."

    wolf_desc = profile.get('wolf_descriptions', {})
    wolf_section = ''
    if wolf_desc and brand_mode:
        lines = '\n'.join(f"- {k}: {v}" for k, v in wolf_desc.items())
        wolf_section = f"\n\nCHARACTER CASTING (add to any family by setting the `wolf` axis):\n{lines}"

    return (
        f"You are the Art Director for {profile['brand_name']}, {profile['brand_tagline']}. Given "
        "a news article and its social copy, you design the VISUAL BRIEF for an editorial poster "
        "image. You never write final prompts or render images -- a deterministic system does "
        "that from your brief. Be creative and varied within the brand's frozen visual contract below.\n\n"
        f"FROZEN BRAND STYLE (do not restate this -- it is applied automatically):\n{style_block}\n\n"
        f"VISUAL METAPHOR LIBRARY:\n{metaphor_lines}{approved_section}\n\n"
        f"LAYOUT FAMILIES:\n{families_block}"
        f"{wolf_section}\n\n"
        f"VARIATION AXES (pick one value per axis from these lists):\n{axes_block}\n\n"
        f"ROUTING GUIDANCE:\n{profile['routing_table']}\n\n"
        f"TEXT RULES:\n{profile['text_rules']}\n\n"
        f"ANTI-REPETITION:\n{recent_block}\n\n"
        f"{_build_brief_schema(profile)}\n\n{profile['brief_examples']}"
    )


def call_art_director(article, copy_text, sentiment, platform, profile, recent, brand_mode=True):
    sys_prompt = _build_art_director_system_prompt(profile, recent, brand_mode=brand_mode)
    user_msg = (
        f"Article title: {article.get('title', '')}\n"
        f"Description: {article.get('desc', '')}\n"
        f"Sentiment: {sentiment}\n"
        f"Platform: {platform}\n"
        f"Chosen social copy: {copy_text}\n\n"
        "Design the visual brief now. Respond with ONLY the JSON object."
    )
    msgs = [{'role': 'system', 'content': sys_prompt},
            {'role': 'user',   'content': user_msg}]
    # Keep GPT-5.5 for the Art Director brief. Tight 30s deadline bounds the
    # retry chain so a stalled reasoning-model call can't hang the whole request
    # long enough for the browser to give up with "Failed to fetch". If GPT-5.5
    # doesn't return a usable brief within budget, the deterministic fallback
    # brief in handlers/image.py takes over — image generation still completes.
    return openrouter_chat(EDITORIAL_MODELS['gpt']['id'], msgs, ART_DIRECTOR_TEMPERATURE,
                           ART_DIRECTOR_MAX_TOKENS, deadline_sec=30)


# ── Stage 2a: brief validation + safe fallback ─────────────────────────────────
_BANNED_SUBJECT_TERMS = [
    'text', 'label', 'logo', 'watermark', 'rzwire', 'mgc coin', 'meta games coin',
    'ranking platform', 'ranking.game', 'oasis coin', 'rzoasis', 'jewelry coin',
    'jewelry token', 'industrial token', 'industrial.game',
]
_WALLET_ADDRESS_RE = re.compile(r'0x[a-fA-F0-9]{6,}')

def _article_mentions_brand(article, profile):
    keywords = profile.get('brand_keywords', [])
    if not keywords:
        return True  # no keywords defined means the profile always uses brand mode
    text = (article.get('title', '') + ' ' + article.get('desc', '')).lower()
    return any(kw.lower() in text for kw in keywords)


def _fallback_brief(article, profile):
    title = (article.get('title') or '').strip()
    max_words = profile.get('headline_max_words', 6)
    headline = ' '.join(title.split()[:max_words])
    if profile.get('headline_uppercase', True):
        headline = headline.upper()
    brief = dict(profile['fallback_brief'])
    if headline:
        brief['headline'] = headline
    return brief


def validate_brief(brief, article, profile, recent=()):
    if not isinstance(brief, dict):
        return _fallback_brief(article, profile)

    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    families = _active_families(profile)
    axes = profile['axes']
    max_words = profile.get('headline_max_words', 6)

    family = brief.get('family')
    if family not in families:
        return _fallback_brief(article, profile)
    fam = families[family]
    uppercase = fam.get('headline_uppercase', profile.get('headline_uppercase', True))

    headline = (brief.get('headline') or '').strip()
    if not headline:
        return _fallback_brief(article, profile)
    words = headline.split()
    if len(words) > max_words:
        headline = ' '.join(words[:max_words])
    if uppercase:
        headline = headline.upper()

    subject_scene = (brief.get('subject_scene') or '').strip()
    lowered = subject_scene.lower()
    banned_terms = _BANNED_SUBJECT_TERMS + profile.get('extra_banned_subject_terms', [])
    if (not subject_scene or any(term in lowered for term in banned_terms)
            or _WALLET_ADDRESS_RE.search(subject_scene)):
        return _fallback_brief(article, profile)

    no_text_mode = profile.get('no_text_mode')
    if family == no_text_mode:
        art_style = (brief.get('art_style') or '').strip()
        recent_styles = {(r.get('art_style') or '').strip().lower() for r in recent[-5:]}
        if not art_style or art_style.lower() in recent_styles:
            return _fallback_brief(article, profile)

    data_elements = brief.get('data_elements') or []
    if not isinstance(data_elements, list):
        data_elements = []
    clean_elements = []
    max_len = fam.get('data_value_max_len')
    source_numbers = set()
    if profile.get('data_numbers_must_appear_in_article'):
        source_text = f"{article.get('title', '')} {article.get('desc', '')}".replace(',', '')
        source_numbers = set(re.findall(r'\d+(?:\.\d+)?', source_text))
        headline_numbers = set(re.findall(r'\d+(?:\.\d+)?', headline.replace(',', '')))
        if headline_numbers and not headline_numbers.issubset(source_numbers):
            return _fallback_brief(article, profile)
    for el in data_elements:
        if isinstance(el, dict) and el.get('value'):
            value = str(el['value'])[:max_len] if max_len else str(el['value'])
            label = str(el.get('label') or '')
            element_numbers = set(re.findall(
                r'\d+(?:\.\d+)?', f'{value} {label}'.replace(',', '')
            ))
            if element_numbers and not element_numbers.issubset(source_numbers):
                continue
            clean_elements.append({'value': value, 'label': label})
    data_elements = clean_elements[:fam['data_budget']]
    if family == no_text_mode:
        data_elements = []
    if family in profile.get('families_requiring_data', []) and not data_elements:
        return _fallback_brief(article, profile)

    camera = brief.get(cam_axis)
    if camera not in axes[cam_axis]:
        camera = fam['default_axes'][cam_axis]

    energy = brief.get(nrg_axis)
    if energy not in axes[nrg_axis]:
        energy = fam['default_axes'][nrg_axis]

    env_restricted = profile.get('environment_restricted', {})
    environment = brief.get(env_axis)
    if environment not in axes[env_axis]:
        environment = fam['default_axes'][env_axis]
    elif environment in env_restricted:
        cond = env_restricted[environment]
        if energy not in cond.get('energies', []) and family not in cond.get('families', []):
            environment = fam['default_axes'][env_axis]

    mood_default = profile.get('mood_accent_default', next(iter(axes[mood_axis])))
    mood_restricted = profile.get('mood_accent_restricted', {})
    mood_accent = brief.get(mood_axis)
    if mood_accent not in axes[mood_axis]:
        mood_accent = mood_default
    elif mood_accent in mood_restricted:
        cond = mood_restricted[mood_accent]
        if isinstance(cond, str):
            cond = {'families': [cond]}
        if family not in cond.get('families', []) and environment not in cond.get('environments', []):
            mood_accent = mood_default

    companion = profile.get('axis_companion_field', {})
    if mood_accent in companion and not (brief.get(companion[mood_accent]) or '').strip():
        mood_accent = mood_default

    result = {
        'family': family,
        'headline': headline,
        'layout': 'art_with_data' if data_elements else 'art_only',
        'data_elements': data_elements,
        env_axis: environment,
        cam_axis: camera,
        nrg_axis: energy,
        mood_axis: mood_accent,
        'subject_scene': subject_scene,
    }

    axis_optional = profile.get('axis_optional', {})
    for axis in _extra_axes(profile):
        val = brief.get(axis)
        if axis_optional.get(axis):
            if val not in axes[axis] and val != 'none':
                val = 'none'
        else:
            if val not in axes[axis]:
                val = fam['default_axes'].get(axis, next(iter(axes[axis])))
        result[axis] = val

    # Cross-axis constraint: certain axis values are only valid in a specific family.
    for ax, constraints in profile.get('axis_family_required', {}).items():
        for restricted_val, required_family in constraints.items():
            if result.get(ax) == restricted_val and family != required_family:
                result[ax] = 'none' if axis_optional.get(ax) else fam['default_axes'].get(ax, next(iter(axes[ax])))

    for field in profile.get('passthrough_fields', []):
        result[field] = (brief.get(field) or '').strip()

    return result


# ── Stage 2b: deterministic prompt assembler ───────────────────────────────────
def _render_data_element(el, profile):
    label_part = ''
    if el.get('label'):
        label_tpl = profile.get('data_element_label_template', ' with the short label "{label}"')
        label_part = label_tpl.format(label=el['label'])
    return profile['data_element_template'].format(value=el['value'], label_part=label_part)


def assemble_prompt(brief, profile, brand_mode=True):
    fs = profile['frozen_style']
    env_axis, cam_axis, nrg_axis, mood_axis = profile.get('core_axes', _CORE_AXES)
    fam = profile['families'][brief['family']]
    axes = profile['axes']

    parts = []

    # 1. Frozen style
    parts.append(
        f"{fs['format']}. {fs['palette']}. {fs['materials']}. {fs['rendering']}. "
        f"{fs['background_vocab']}. {fs['headline_zone']}."
    )

    # 2. Finish, if this profile has a finish axis
    if 'finish' in axes:
        parts.append(axes['finish'][brief['finish']])

    # 3. Environment
    parts.append(axes[env_axis][brief[env_axis]])

    # 4. Hall-theme injection, if set
    hall_theme = brief.get('hall_theme')
    if 'hall_theme' in axes and hall_theme not in (None, 'none'):
        parts.append(axes['hall_theme'][hall_theme])

    # 5. Subject
    subject_line = f"Subject: {brief['subject_scene']}"
    if brief.get('art_style'):
        subject_line += f" Art style: {brief['art_style']}."
    parts.append(subject_line)

    # 6. Family skeleton
    parts.append(fam['skeleton'])

    # 7. Data elements, if any
    if brief['data_elements']:
        tiles = '; '.join(_render_data_element(el, profile) for el in brief['data_elements'])
        parts.append(f"The scene also includes {tiles}.")

    # 7.5. Extra axes injected after data elements when a brand profile needs them.
    for ax in profile.get('axis_inject_after_data', []):
        val = brief.get(ax)
        if val and val != 'none':
            sentence = axes.get(ax, {}).get(val, '')
            if sentence:
                parts.append(sentence)

    # 8. Camera/composition + energy
    parts.append(axes[cam_axis][brief[cam_axis]] + ' ' + axes[nrg_axis][brief[nrg_axis]])

    # 9. Mood/accent
    parts.append(axes[mood_axis][brief[mood_axis]])

    # 10/11. Headline rule + legibility, or the no-text override
    if brief['family'] == profile.get('no_text_mode'):
        parts.append(f"{profile['no_text_line']} {fs['never']}.")
    else:
        headline_zone = (
            axes['headline_layout'][brief['headline_layout']] if 'headline_layout' in axes
            else fam.get('headline_treatment', fs['headline_zone'])
        )
        parts.append(f'Headline text: "{brief["headline"]}" -- {headline_zone}.')
        if brand_mode and profile.get('logo_line'):
            parts.append(profile['logo_line'])
        parts.append(f"{profile['legibility_line']} No other text anywhere in the image. {fs['never']}.")

    return ' '.join(parts)
