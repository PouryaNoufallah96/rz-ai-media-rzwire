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
        "footerLogoUrl": "/brands/mgc-footer-logo.svg",
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
        "backgroundScenes": [
            "A monumental black-metal metaverse skyline seen from a low angle, with a controlled signal-yellow sunrise breaking across the horizon, subtle gaming-arena architecture, fine volumetric haze, and generous dark editorial space.",
            "An obsidian digital arena with layered architectural fins and a restrained gold energy core in the distance, cinematic side light, deep graphite atmosphere, and calm negative space.",
            "A vast black orbital landscape crossed by precise gold signal paths and one luminous amber horizon, premium science-fiction scale, no literal coin, no text, and no chart-like graphics.",
        ],
        "artDirectorProfile": "MGC Coin",
        "imagePrompt": "Premium black-and-signal-yellow MGC market editorial with monumental gaming and metaverse architecture, restrained gold, confident hierarchy, cinematic depth, and generous negative space.",
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
        "footerLogoUrl": "/brands/oasis-footer-logo.svg",
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
        "backgroundScenes": [
            "A colossal silver lunar body rising behind a black graphite ridge, with one emerald crescent accent, hard rim light, deep space atmosphere, and a quiet editorial field for typography.",
            "A futuristic graphite lunar outpost at blue hour, precise monolithic towers fading into haze, a restrained emerald horizon glow, and expansive institutional negative space.",
            "An orbital view over a shadowed moon surface with a distant silver sunrise, subtle emerald navigation light, premium cinematic scale, no literal coin, no text, and no chart-like graphics.",
        ],
        "artDirectorProfile": "Oasis Coin",
        "imagePrompt": "Cinematic black and graphite Oasis market editorial with monumental lunar scenery, silver rim light, restrained emerald accents, atmospheric depth, and institutional clarity.",
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
        "footerLogoUrl": "/brands/jewelry-footer-logo.svg",
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
        "backgroundScenes": [
            "A luminous landscape of monumental faceted lavender crystal catching a soft pearl sunrise, with platinum reflections, elegant depth, and clean luxury-editorial negative space.",
            "A sculptural platinum orbital ring surrounding a deep violet gemstone form, soft diffused gallery light, refined shadows, and a calm pearl-white field for typography.",
            "An abstract luxury pavilion built from translucent lavender glass and polished platinum planes, subtle crystal refraction, airy cinematic scale, no literal coin, no text, and no chart-like graphics.",
        ],
        "artDirectorProfile": "Jewelry Coin",
        "imagePrompt": "Luminous pearl-white and lavender Jewelry market editorial with monumental crystal scenery, violet refraction, platinum details, cinematic elegance, and luxury-tech clarity.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0xf04FaB6Dda66261eaBfD65e92A6b81dDaF6a950a",
            "pool": "0xd85df7190cdc09a42d7a2567f68812128c71e9a7",
            "poolName": "Jewelry / MGC", "tokenSide": "base",
        },
    },
    "industrial": {
        "id": "industrial",
        "name": "Industrial Token",
        "symbol": "INDUSTRIAL",
        "enabled": True,
        "logoUrl": "/brands/industrial-coin-logo.png",
        "footerLogoUrl": "/brands/industrial-footer-logo.png",
        "footer": "industrial.game",
        "domain": "industrial.game",
        "chartColor": "#b56ad9",
        "theme": {
            "background": "#10072d", "backgroundAlt": "#291050", "surface": "#191231",
            "surfaceAlt": "#281a47", "text": "#f8f5ff", "muted": "#b9aed1",
            "positive": "#41c98d", "negative": "#ef6c75", "accent": "#f4c224",
            "accentAlt": "#7816d2", "border": "#6c42a1",
        },
        "motifs": ["precision gold robotics", "industrial violet horizon", "verified light paths", "real-economy infrastructure"],
        "backgroundScenes": [
            "A credible advanced manufacturing floor at deep indigo hour, with one precise gold robotic arm, graphite machinery, restrained violet light paths, cinematic depth, and broad quiet editorial space.",
            "A monumental industrial logistics landscape connecting port cranes, rail, warehouse, and clean energy infrastructure with subtle gold verification paths, violet-blue twilight, realistic scale, and calm negative space.",
            "A premium Industry 4.0 hall where one engineer observes a translucent factory-scale digital twin above real machinery, controlled purple atmosphere, warm metallic-gold accents, and uncluttered editorial hierarchy.",
        ],
        "artDirectorProfile": "Industrial Token",
        "imagePrompt": "Premium Industrial Token market editorial with deep indigo, controlled ultraviolet, metallic gold industrial machinery, realistic infrastructure, cinematic depth, and clear factual hierarchy.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0x9e06e1203bdc3747ee3ab5fa9488619bcf2a2666",
            "pool": "0xd5916c07de3ffbb728a07e118fa89b5452ea9602",
            "poolName": "Industrial / MGC", "tokenSide": "base",
            "coinMarketCapId": "35883",
            "coinMarketCapUrl": "https://coinmarketcap.com/currencies/industrial/",
        },
    },
    "real-estate": {
        "id": "real-estate",
        "name": "Real Estate Token",
        "symbol": "REALESTATE",
        "enabled": True,
        "logoUrl": "/brands/real-estate-coin-logo.png",
        "footerLogoUrl": "/brands/real-estate-footer-logo.png",
        "footer": "real-estate.game",
        "domain": "real-estate.game",
        "chartColor": "#0b8f91",
        "theme": {
            "background": "#052f31", "backgroundAlt": "#0a6668", "surface": "#0b4446",
            "surfaceAlt": "#116f72", "text": "#fffdf7", "muted": "#b9d5d3",
            "positive": "#45d09c", "negative": "#ef716f", "accent": "#dfbd69",
            "accentAlt": "#17aeb2", "border": "#318b8c",
        },
        "motifs": ["verified property title", "architectural digital twin", "champagne-gold ownership path", "sustainable city grid"],
        "backgroundScenes": [
            "A premium contemporary residence at blue hour transitioning into an exact cyan architectural digital twin, with warm interior light, deep property teal atmosphere, and generous editorial negative space.",
            "A realistic sustainable coastal property district at sunrise, with restrained teal verification paths integrated into streets, champagne-gold light, credible architecture, and broad calm sky for editorial hierarchy.",
            "A refined property-title scene where a luminous architectural model rises above layered transparent ownership records, dark teal stone surfaces, subtle gold verification nodes, and institutional cinematic depth.",
        ],
        "artDirectorProfile": "Real Estate Token",
        "imagePrompt": "Premium Real Estate Token market editorial with credible contemporary architecture, deep property teal, champagne gold, pearl white, restrained digital ownership infrastructure, cinematic realism, and clear factual hierarchy.",
        "market": {
            "provider": "geckoterminal", "network": "bsc",
            "contract": "0x32477cf0e324f9a9cb49e8803fa4de9f80f8d0d4",
            "pool": "0x742f3a595c83d6a9aa3417c2c7c3f36fb6ee4ac4",
            "poolName": "RealEstate / USDT", "tokenSide": "base",
            "coinMarketCapId": "35949",
            "coinMarketCapUrl": "https://coinmarketcap.com/currencies/realestate/",
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
            for key in ("name", "logoUrl", "footerLogoUrl", "footer", "domain", "chartColor", "artDirectorProfile", "imagePrompt"):
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
            scenes = item.get("backgroundScenes") or []
            if len(scenes) < 3 or any(len(str(scene).strip()) < 80 for scene in scenes):
                raise ValueError(f"Enabled analytics brand {token_id} needs three detailed background scenes.")
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
    fields = ("id", "name", "symbol", "enabled", "logoUrl", "footerLogoUrl", "footer", "domain", "chartColor", "theme", "motifs")
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
