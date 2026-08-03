"""Validation and normalization for user-controlled Analytics chart styling."""

from __future__ import annotations

import re
from copy import deepcopy


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
SERIES_KEY_RE = re.compile(r"^[A-Za-z0-9:._-]{1,160}$")

PRESET_IDS = {"clean-light", "brand-dark", "high-contrast", "colorblind-safe", "custom"}
LEGEND_POSITIONS = {"top", "bottom", "left", "right", "overlay-top-right", "overlay-bottom-right"}
LEGEND_FORMATS = {"symbol", "symbol-change"}
LINE_WIDTHS = {2, 4, 6}
MARKER_MODES = {"none", "endpoints", "all"}
GRID_STRENGTHS = {"none", "subtle", "standard"}

DEFAULT_CHART_STYLE = {
    "version": 1,
    "presetId": "clean-light",
    "backgroundColor": "#FBFAF7",
    "seriesColors": {},
    "legend": {"position": "bottom", "format": "symbol-change"},
    "lineWidth": 4,
    "markers": "endpoints",
    "gridStrength": "subtle",
}


def normalize_hex_color(value, field_name="color") -> str:
    color = str(value or "").strip()
    if not HEX_COLOR_RE.fullmatch(color):
        raise ValueError(f"{field_name} must be a six-digit hex color")
    return color.upper()


def normalize_chart_style(raw_style=None) -> dict:
    """Return the stable public chart-style shape or raise a clean ValueError."""
    if raw_style is None:
        return deepcopy(DEFAULT_CHART_STYLE)
    if not isinstance(raw_style, dict):
        raise ValueError("chartStyle must be an object")

    try:
        version = int(raw_style.get("version", 1))
    except (TypeError, ValueError) as exc:
        raise ValueError("Unsupported Analytics chart style version") from exc
    if version != 1:
        raise ValueError("Unsupported Analytics chart style version")

    preset_id = str(raw_style.get("presetId") or DEFAULT_CHART_STYLE["presetId"]).strip()
    if preset_id not in PRESET_IDS:
        raise ValueError("Unsupported Analytics chart preset")

    background = normalize_hex_color(
        raw_style.get("backgroundColor") or DEFAULT_CHART_STYLE["backgroundColor"],
        "backgroundColor",
    )

    raw_colors = raw_style.get("seriesColors") or {}
    if not isinstance(raw_colors, dict):
        raise ValueError("seriesColors must be an object")
    if len(raw_colors) > 100:
        raise ValueError("seriesColors supports at most 100 saved asset colors")
    series_colors = {}
    for raw_key, raw_color in raw_colors.items():
        key = str(raw_key or "").strip()
        if not SERIES_KEY_RE.fullmatch(key):
            raise ValueError("seriesColors contains an invalid asset id")
        series_colors[key] = normalize_hex_color(raw_color, f"seriesColors.{key}")

    raw_legend = raw_style.get("legend") or {}
    if not isinstance(raw_legend, dict):
        raise ValueError("legend must be an object")
    legend_position = str(raw_legend.get("position") or DEFAULT_CHART_STYLE["legend"]["position"]).strip()
    legend_format = str(raw_legend.get("format") or DEFAULT_CHART_STYLE["legend"]["format"]).strip()
    if legend_position not in LEGEND_POSITIONS:
        raise ValueError("Unsupported Analytics legend position")
    if legend_format not in LEGEND_FORMATS:
        raise ValueError("Unsupported Analytics legend format")

    try:
        line_width = int(raw_style.get("lineWidth", DEFAULT_CHART_STYLE["lineWidth"]))
    except (TypeError, ValueError) as exc:
        raise ValueError("lineWidth must be 2, 4, or 6") from exc
    if line_width not in LINE_WIDTHS:
        raise ValueError("lineWidth must be 2, 4, or 6")

    markers = str(raw_style.get("markers") or DEFAULT_CHART_STYLE["markers"]).strip()
    if markers not in MARKER_MODES:
        raise ValueError("Unsupported Analytics marker mode")
    grid_strength = str(raw_style.get("gridStrength") or DEFAULT_CHART_STYLE["gridStrength"]).strip()
    if grid_strength not in GRID_STRENGTHS:
        raise ValueError("Unsupported Analytics grid strength")

    return {
        "version": 1,
        "presetId": preset_id,
        "backgroundColor": background,
        "seriesColors": dict(sorted(series_colors.items())),
        "legend": {"position": legend_position, "format": legend_format},
        "lineWidth": line_width,
        "markers": markers,
        "gridStrength": grid_strength,
    }
