"""Controlled RZWire coin registry for market analytics and publishing themes."""

from __future__ import annotations

from copy import deepcopy


REQUIRED_THEME_KEYS = {
    "background", "backgroundAlt", "surface", "surfaceAlt", "text", "muted",
    "positive", "negative", "accent", "accentAlt", "border",
}
REQUIRED_MARKET_KEYS = {"provider", "network", "contract", "pool", "poolName", "tokenSide"}


ANALYTICS_BRANDS = {
    "mgc": {
        "id": "mgc",
        "name": "MGC Coin",
        "symbol": "MGC",
        "enabled": True,
        "logoUrl": "/brands/mgc-coin-logo.png",
        "footer": "metagamescoin.io",
        "domain": "metagamescoin.io",
        "chartColor": "#d9b91d",
        "theme": {
            "background": "#050606", "backgroundAlt": "#262000", "surface": "#111315",
            "surfaceAlt": "#1c1d1e", "text": "#fffdf5", "muted": "#aaa797",
            "positive": "#1fd083", "negative": "#ef5350", "accent": "#f0c419",
            "accentAlt": "#b88a16", "border": "#64551c",
        },
        "motifs": ["signal-yellow horizon", "restrained gold light", "black editorial field", "precise market grid"],
        "artDirectorProfile": "MGC Coin",
        "imagePrompt": "Premium black-and-signal-yellow MGC market editorial with restrained gold, clean geometry, confident hierarchy, and generous negative space.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0xbb73BB2505AC4643d5C0a99c2A1F34B3DfD09D11",
            "pool": "0x771e1c638a9409bfc93158588f1745f638f4d10b",
            "poolName": "RZ / MGC", "tokenSide": "quote",
        },
    },
    "oasis": {
        "id": "oasis",
        "name": "Oasis Coin",
        "symbol": "OASIS",
        "enabled": True,
        "logoUrl": "/brands/oasis-coin-logo.png",
        "footer": "rzoasis.tech",
        "domain": "rzoasis.tech",
        "chartColor": "#739e90",
        "theme": {
            "background": "#060708", "backgroundAlt": "#20242a", "surface": "#12151a",
            "surfaceAlt": "#1d2229", "text": "#f5f6f7", "muted": "#9ba2aa",
            "positive": "#28c890", "negative": "#df6d69", "accent": "#aeb8c4",
            "accentAlt": "#4d8f7c", "border": "#454c55",
        },
        "motifs": ["lunar silver arc", "graphite city grid", "emerald data pulse", "orbital precision"],
        "artDirectorProfile": "Oasis Coin",
        "imagePrompt": "Cinematic black and graphite Oasis market editorial with lunar silver, restrained emerald data accents, quiet depth, and institutional clarity.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0x1a4D41219C547f3A0EE36cf3d9E68F80699cF283",
            "pool": "0xc60bb735abcaa4be9a271bfe3af2fad19a953397",
            "poolName": "OASIS / MGC", "tokenSide": "base",
        },
    },
    "jewelry": {
        "id": "jewelry",
        "name": "Jewelry Coin",
        "symbol": "JEWELRY",
        "enabled": True,
        "logoUrl": "/brands/jewelry-coin-logo.png",
        "footer": "Jewelry.Game",
        "domain": "Jewelry.Game",
        "chartColor": "#8f82e8",
        "theme": {
            "background": "#f8f5ff", "backgroundAlt": "#d8cbff", "surface": "#ffffff",
            "surfaceAlt": "#eee8ff", "text": "#201348", "muted": "#706a82",
            "positive": "#2ba780", "negative": "#cf5b78", "accent": "#8f72ed",
            "accentAlt": "#d68add", "border": "#c9bdf0",
        },
        "motifs": ["crystal refraction", "platinum ring", "lavender glass", "soft pearl light"],
        "artDirectorProfile": "Jewelry Coin",
        "imagePrompt": "Luminous pearl-white and lavender Jewelry market editorial with violet crystal refraction, platinum details, elegant softness, and luxury-tech clarity.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0xf04FaB6Dda66261eaBfD65e92A6b81dDaF6a950a",
            "pool": "0xd85df7190cdc09a42d7a2567f68812128c71e9a7",
            "poolName": "Jewelry / MGC", "tokenSide": "base",
        },
    },
}


def validate_analytics_brand_registry(registry=None) -> dict:
    # Resolve the approved profile catalog lazily. Enabled coins fail closed if
    # their registry entry points at a profile that cannot direct image work.
    from brand_profiles import BRAND_IMAGE_PROFILES

    source = ANALYTICS_BRANDS if registry is None else registry
    entries = list(source.values()) if isinstance(source, dict) else list(source or [])
    seen_ids: set[str] = set()
    seen_symbols: set[str] = set()
    validated: dict[str, dict] = {}
    for raw in entries:
        item = deepcopy(raw)
        token_id = str(item.get("id") or "").strip().lower()
        symbol = str(item.get("symbol") or "").strip().upper()
        if not token_id or token_id in seen_ids:
            raise ValueError(f"Duplicate or missing analytics brand id: {token_id or 'empty'}")
        if not symbol or symbol in seen_symbols:
            raise ValueError(f"Duplicate or missing analytics brand symbol: {symbol or 'empty'}")
        seen_ids.add(token_id)
        seen_symbols.add(symbol)
        item["id"] = token_id
        item["symbol"] = symbol
        if item.get("enabled"):
            for key in ("name", "logoUrl", "footer", "domain", "chartColor", "artDirectorProfile", "imagePrompt"):
                if not str(item.get(key) or "").strip():
                    raise ValueError(f"Enabled analytics brand {token_id} is missing {key}.")
            theme = item.get("theme") or {}
            missing_theme = sorted(REQUIRED_THEME_KEYS - set(theme))
            if missing_theme:
                raise ValueError(f"Enabled analytics brand {token_id} has an incomplete theme: {', '.join(missing_theme)}")
            market = item.get("market") or {}
            missing_market = sorted(REQUIRED_MARKET_KEYS - set(market))
            if missing_market or market.get("provider") != "geckoterminal" or market.get("tokenSide") not in {"base", "quote"}:
                raise ValueError(f"Enabled analytics brand {token_id} has an invalid market mapping.")
            if not item.get("motifs"):
                raise ValueError(f"Enabled analytics brand {token_id} is missing motifs.")
            if item["artDirectorProfile"] not in BRAND_IMAGE_PROFILES:
                raise ValueError(
                    f"Enabled analytics brand {token_id} references an unknown Art Director profile."
                )
        validated[token_id] = item
    return validated


def get_analytics_brand(token_id: str, *, require_enabled: bool = True) -> dict:
    item = ANALYTICS_BRANDS.get(str(token_id or "").strip().lower())
    if not item or (require_enabled and not item.get("enabled")):
        raise ValueError("Unknown or disabled RZWire primary token.")
    # Validate at resolution time so an incomplete future entry fails closed.
    return validate_analytics_brand_registry([item])[item["id"]]


def enabled_analytics_brands() -> list[dict]:
    validated = validate_analytics_brand_registry()
    return [item for item in validated.values() if item.get("enabled")]


def public_analytics_brands() -> list[dict]:
    fields = ("id", "name", "symbol", "enabled", "logoUrl", "footer", "domain", "chartColor", "theme", "motifs")
    result = []
    for item in enabled_analytics_brands():
        public = {key: deepcopy(item[key]) for key in fields}
        public["market"] = {
            key: item["market"][key]
            for key in ("provider", "network", "contract", "poolName", "tokenSide")
        }
        result.append(public)
    return result


def market_token_config() -> dict[str, dict]:
    return {
        item["id"]: {"name": item["name"], "symbol": item["symbol"], **deepcopy(item["market"])}
        for item in enabled_analytics_brands()
    }


# Fail during startup instead of exposing a partly configured brand.
validate_analytics_brand_registry()
