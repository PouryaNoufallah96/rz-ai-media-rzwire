"""Verified public-market history for RZWire analytics posts."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import re
from threading import Lock
from time import monotonic, sleep

import requests

from analytics_brands import get_analytics_brand, market_token_config, public_analytics_brands


GECKO_BASE = "https://api.geckoterminal.com/api/v2"
BINANCE_BASE = "https://api.binance.com/api/v3"
GECKO_HEADERS = {
    "Accept": "application/json;version=20230203",
    "User-Agent": "RZWire/1.0 market-analytics",
}

TOKEN_CONFIG = market_token_config()


def handle_market_brands() -> dict:
    return {"ok": True, "brands": public_analytics_brands()}

PERIOD_CONFIG = {
    "24h": {"gecko": ("hour", 1, 25), "binance": ("1h", 25)},
    "7d": {"gecko": ("hour", 4, 43), "binance": ("4h", 43)},
    "30d": {"gecko": ("day", 1, 31), "binance": ("1d", 31)},
    # GeckoTerminal only supports aggregate=1 for daily OHLCV candles.
    # Request the complete daily range instead of unsupported 3/7-day aggregates.
    "90d": {"gecko": ("day", 1, 91), "binance": ("3d", 31)},
    "1y": {"gecko": ("day", 1, 366), "binance": ("1w", 53)},
    "Custom": {"gecko": ("day", 1, 31), "binance": ("1d", 31)},
}

MAX_PRIMARY_TOKENS = 3
MAX_COMPARISON_ASSETS = 3
MAX_TOTAL_SERIES = 6
CATALOG_CACHE_SECONDS = 900
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}$")
_NETWORK_RE = re.compile(r"^[a-z0-9-]{1,40}$")
_CONTRACT_RE = re.compile(r"^[A-Za-z0-9:_-]{20,128}$")
_CACHE: dict[tuple[str, str, str], tuple[float, dict]] = {}
_SERIES_CACHE: dict[tuple[str, str, str], tuple[float, tuple[dict, dict]]] = {}
_CACHE_LOCK = Lock()
_CACHE_SECONDS = 60
_CATALOG_CACHE: tuple[float, list[dict]] | None = None


def _request_json(url: str, *, params: dict | None = None, headers: dict | None = None):
    for attempt in range(3):
        response = requests.get(url, params=params, headers=headers, timeout=20)
        if response.status_code != 429 or attempt == 2:
            response.raise_for_status()
            return response.json()
        retry_after = response.headers.get("Retry-After")
        try:
            delay = min(5.0, max(1.0, float(retry_after)))
        except (TypeError, ValueError):
            delay = 1.5 * (attempt + 1)
        sleep(delay)
    raise RuntimeError("Market data provider retry failed")


def _clean_symbol(value: object) -> str:
    symbol = str(value or "").strip().upper()
    if not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError("Token symbols must contain 2-20 letters or numbers.")
    return symbol


def _clean_dex_identity(network: object, contract: object) -> tuple[str, str]:
    clean_network = str(network or "").strip().lower()
    clean_contract = str(contract or "").strip()
    if not _NETWORK_RE.fullmatch(clean_network):
        raise ValueError("Enter a valid GeckoTerminal network identifier.")
    if not _CONTRACT_RE.fullmatch(clean_contract):
        raise ValueError("Enter a valid token contract address.")
    return clean_network, clean_contract


def _binance_catalog() -> list[dict]:
    global _CATALOG_CACHE
    with _CACHE_LOCK:
        if _CATALOG_CACHE and monotonic() - _CATALOG_CACHE[0] < CATALOG_CACHE_SECONDS:
            return list(_CATALOG_CACHE[1])

    payload = _request_json(
        f"{BINANCE_BASE}/exchangeInfo",
        headers={"User-Agent": "RZWire/1.0 market-analytics"},
    )
    assets: dict[str, dict] = {}
    for market in payload.get("symbols") or []:
        symbol = str(market.get("baseAsset") or "").upper()
        if (
            market.get("status") != "TRADING"
            or market.get("quoteAsset") != "USDT"
            or market.get("isSpotTradingAllowed") is False
            or not _SYMBOL_RE.fullmatch(symbol)
        ):
            continue
        assets[symbol] = {
            "id": f"binance:{symbol}",
            "type": "binance",
            "symbol": symbol,
            "name": symbol,
            "pair": market.get("symbol") or f"{symbol}USDT",
            "source": "Binance Public Spot API",
        }
    result = sorted(assets.values(), key=lambda item: item["symbol"])
    with _CACHE_LOCK:
        _CATALOG_CACHE = (monotonic(), result)
    return list(result)


def handle_market_assets(params: dict[str, list[str]]) -> dict:
    query = (params.get("query") or params.get("q") or [""])[0].strip().upper()
    limit_value = (params.get("limit") or ["40"])[0]
    try:
        limit = min(100, max(1, int(limit_value)))
    except (TypeError, ValueError):
        limit = 40
    matches = [
        asset for asset in _binance_catalog()
        if not query or query in asset["symbol"] or query in asset["pair"]
    ][:limit]
    return {"ok": True, "query": query, "assets": matches}


def _best_pool(token: dict) -> tuple[dict, str]:
    network = token["network"]
    contract = token["contract"]
    payload = _request_json(
        f"{GECKO_BASE}/networks/{network}/tokens/{contract}/pools",
        params={"page": 1},
        headers=GECKO_HEADERS,
    )
    pools = payload.get("data") or []
    if not pools:
        raise ValueError(f"No GeckoTerminal pool was found for {token['symbol']}.")

    def reserve(item):
        try:
            return float(item.get("attributes", {}).get("reserve_in_usd") or 0)
        except (TypeError, ValueError):
            return 0

    pool = max(pools, key=reserve)
    relationships = pool.get("relationships", {})
    target_id = f"{network}_{contract}".lower()
    base_id = str(relationships.get("base_token", {}).get("data", {}).get("id", "")).lower()
    quote_id = str(relationships.get("quote_token", {}).get("data", {}).get("id", "")).lower()
    if target_id == base_id:
        side = "base"
    elif target_id == quote_id:
        side = "quote"
    else:
        raise ValueError(f"The selected pool does not contain {token['symbol']}.")
    return pool, side


def _gecko_token_profile(network: str, contract: str) -> dict:
    payload = _request_json(
        f"{GECKO_BASE}/networks/{network}/tokens/{contract}",
        headers=GECKO_HEADERS,
    )
    attributes = (payload.get("data") or {}).get("attributes") or {}
    symbol = str(attributes.get("symbol") or "").strip().upper()
    name = str(attributes.get("name") or symbol or "Custom DEX token").strip()
    if not symbol:
        raise ValueError("GeckoTerminal did not return a symbol for this contract.")
    return {
        "name": name,
        "symbol": symbol,
        "network": network,
        "contract": contract,
    }


def _resolve_dex_asset(network: object, contract: object) -> dict:
    clean_network, clean_contract = _clean_dex_identity(network, contract)
    token = _gecko_token_profile(clean_network, clean_contract)
    pool, side = _best_pool(token)
    attributes = pool.get("attributes") or {}
    pool_address = attributes.get("address") or str(pool.get("id", "")).split("_", 1)[-1]
    if not pool_address:
        raise ValueError("The most liquid GeckoTerminal pool has no usable address.")
    return {
        "id": f"dex:{clean_network}:{clean_contract.lower()}",
        "type": "dex",
        "name": token["name"],
        "symbol": token["symbol"],
        "network": clean_network,
        "contract": clean_contract,
        "pool": pool_address,
        "poolName": attributes.get("name") or pool.get("id"),
        "tokenSide": side,
        "source": "GeckoTerminal Public API",
    }


def handle_resolve_dex_asset(body: dict) -> dict:
    return {
        "ok": True,
        "verified": True,
        "asset": _resolve_dex_asset(body.get("network"), body.get("contract")),
    }


def _series_summary(name: str, symbol: str, points: list[dict]) -> dict:
    if len(points) < 2:
        raise ValueError(f"Not enough historical prices were returned for {symbol}.")
    start_price = points[0]["close"]
    end_price = points[-1]["close"]
    change = ((end_price - start_price) / start_price * 100) if start_price else 0
    return {
        "name": name,
        "symbol": symbol,
        "startPrice": start_price,
        "endPrice": end_price,
        "changePercent": change,
        "points": points,
    }


def _gecko_history(token: dict, period: str) -> tuple[dict, dict]:
    pool_address = token.get("pool")
    token_side = token.get("tokenSide")
    pool_name = token.get("poolName")
    if not pool_address or not token_side:
        pool, token_side = _best_pool(token)
        attributes = pool.get("attributes", {})
        pool_address = attributes.get("address") or str(pool.get("id", "")).split("_", 1)[-1]
        pool_name = attributes.get("name") or pool.get("id")
    timeframe, aggregate, limit = PERIOD_CONFIG[period]["gecko"]
    payload = _request_json(
        f"{GECKO_BASE}/networks/{token['network']}/pools/{pool_address}/ohlcv/{timeframe}",
        params={
            "aggregate": aggregate,
            "limit": limit,
            "currency": "usd",
            "token": token_side,
        },
        headers=GECKO_HEADERS,
    )
    raw_points = payload.get("data", {}).get("attributes", {}).get("ohlcv_list") or []
    points = [
        {
            "timestamp": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
        for row in reversed(raw_points)
        if isinstance(row, list) and len(row) >= 6
    ]
    source = {
        "provider": "GeckoTerminal Public API",
        "network": token["network"].upper(),
        "contract": token["contract"],
        "poolAddress": pool_address,
        "poolName": pool_name,
        "attributionUrl": f"https://www.geckoterminal.com/{token['network']}/pools/{pool_address}",
    }
    return _series_summary(token["name"], token["symbol"], points), source


def _binance_history(symbol: str, period: str) -> tuple[dict, dict]:
    interval, limit = PERIOD_CONFIG[period]["binance"]
    pair = f"{symbol}USDT"
    rows = _request_json(
        f"{BINANCE_BASE}/klines",
        params={"symbol": pair, "interval": interval, "limit": limit},
        headers={"User-Agent": "RZWire/1.0 market-analytics"},
    )
    points = [
        {
            "timestamp": int(row[0] / 1000),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
        for row in rows
        if isinstance(row, list) and len(row) >= 6
    ]
    source = {
        "provider": "Binance Public Spot API",
        "pair": pair,
        "attributionUrl": f"https://www.binance.com/en/trade/{symbol}_USDT",
    }
    return _series_summary(symbol, symbol, points), source


def _cached_series(cache_key: tuple[str, str, str], loader) -> tuple[dict, dict, bool]:
    with _CACHE_LOCK:
        cached = _SERIES_CACHE.get(cache_key)
        if cached and monotonic() - cached[0] < _CACHE_SECONDS:
            summary, source = cached[1]
            return summary, source, True
    summary, source = loader()
    with _CACHE_LOCK:
        _SERIES_CACHE[cache_key] = (monotonic(), (summary, source))
    return summary, source, False


def _normalise_batch_request(body: dict) -> tuple[list[dict], str, str]:
    primary_ids = body.get("primaryTokens") or []
    comparison_assets = body.get("comparisonAssets") or []
    period = str(body.get("period") or "30d").strip()
    scale = str(body.get("scale") or "relative").strip().lower()

    if not isinstance(primary_ids, list) or not 1 <= len(primary_ids) <= MAX_PRIMARY_TOKENS:
        raise ValueError("Select between one and three RZWire tokens.")
    if not isinstance(comparison_assets, list) or len(comparison_assets) > MAX_COMPARISON_ASSETS:
        raise ValueError("Select no more than three comparison assets.")
    if len(primary_ids) + len(comparison_assets) > MAX_TOTAL_SERIES:
        raise ValueError("A chart can contain no more than six token series.")
    if period not in PERIOD_CONFIG:
        raise ValueError("Unsupported period")
    if scale not in {"relative", "absolute"}:
        raise ValueError("scale must be relative or absolute")

    descriptors: list[dict] = []
    seen: set[str] = set()
    primary_symbols: set[str] = set()
    for raw_token_id in primary_ids:
        token_id = str(raw_token_id or "").strip().lower()
        brand = get_analytics_brand(token_id)
        key = f"rz:{token_id}"
        if key in seen:
            raise ValueError("Each RZWire token can only be selected once.")
        seen.add(key)
        token = {"name": brand["name"], "symbol": brand["symbol"], **brand["market"]}
        primary_symbols.add(token["symbol"].upper())
        descriptors.append({
            "id": key,
            "type": "rz",
            "role": "primary",
            "tokenId": token_id,
            "name": token["name"],
            "symbol": token["symbol"],
        })

    for raw_asset in comparison_assets:
        if not isinstance(raw_asset, dict):
            raise ValueError("Each comparison asset must be an object.")
        asset_type = str(raw_asset.get("type") or "binance").strip().lower()
        if asset_type == "binance":
            symbol = _clean_symbol(raw_asset.get("symbol"))
            key = f"binance:{symbol}"
            descriptor = {
                "id": key,
                "type": "binance",
                "role": "comparison",
                "name": str(raw_asset.get("name") or symbol).strip(),
                "symbol": symbol,
            }
        elif asset_type == "dex":
            network, contract = _clean_dex_identity(raw_asset.get("network"), raw_asset.get("contract"))
            key = f"dex:{network}:{contract.lower()}"
            descriptor = {
                "id": key,
                "type": "dex",
                "role": "comparison",
                "name": str(raw_asset.get("name") or "Custom DEX token").strip(),
                "symbol": str(raw_asset.get("symbol") or "DEX").strip().upper(),
                "network": network,
                "contract": contract,
            }
        else:
            raise ValueError("Comparison asset type must be binance or dex.")
        if key in seen:
            raise ValueError("Each comparison asset can only be selected once.")
        if descriptor["symbol"].upper() in primary_symbols:
            raise ValueError(f"{descriptor['symbol']} is already selected as an RZWire token.")
        seen.add(key)
        descriptors.append(descriptor)
    return descriptors, period, scale


def _fetch_descriptor(descriptor: dict, period: str) -> dict:
    asset_type = descriptor["type"]
    if asset_type == "rz":
        token_id = descriptor["tokenId"]
        brand = get_analytics_brand(token_id)
        token = {"name": brand["name"], "symbol": brand["symbol"], **brand["market"]}
        summary, source, cached = _cached_series(
            ("rz", token_id, period),
            lambda: _gecko_history(token, period),
        )
    elif asset_type == "binance":
        symbol = descriptor["symbol"]
        summary, source, cached = _cached_series(
            ("binance", symbol, period),
            lambda: _binance_history(symbol, period),
        )
    else:
        network = descriptor["network"]
        contract = descriptor["contract"]

        def load_dex():
            resolved = _resolve_dex_asset(network, contract)
            token = {
                "name": resolved["name"],
                "symbol": resolved["symbol"],
                "network": resolved["network"],
                "contract": resolved["contract"],
                "pool": resolved["pool"],
                "poolName": resolved["poolName"],
                "tokenSide": resolved["tokenSide"],
            }
            return _gecko_history(token, period)

        summary, source, cached = _cached_series(
            ("dex", f"{network}:{contract.lower()}", period),
            load_dex,
        )
    points = summary.get("points") or []
    return {
        **descriptor,
        **summary,
        "status": "verified",
        "coverageStart": points[0]["timestamp"] if points else None,
        "coverageEnd": points[-1]["timestamp"] if points else None,
        "source": source,
        "cached": cached,
    }


def handle_market_history_batch(body: dict) -> dict:
    descriptors, period, scale = _normalise_batch_request(body)
    series: list[dict] = []
    failures: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(MAX_TOTAL_SERIES, len(descriptors))) as executor:
        future_map = {executor.submit(_fetch_descriptor, item, period): item for item in descriptors}
        for future in as_completed(future_map):
            descriptor = future_map[future]
            try:
                series.append(future.result())
            except Exception as exc:
                failures.append({
                    **descriptor,
                    "status": "unavailable",
                    "error": str(exc),
                })

    order = {item["id"]: index for index, item in enumerate(descriptors)}
    series.sort(key=lambda item: order[item["id"]])
    failures.sort(key=lambda item: order[item["id"]])
    successful_primary = any(item["role"] == "primary" for item in series)
    warnings = [f"{item['symbol']} could not be loaded: {item['error']}" for item in failures]
    if series:
        earliest_end = min(item["coverageEnd"] for item in series if item.get("coverageEnd"))
        latest_start = max(item["coverageStart"] for item in series if item.get("coverageStart"))
        for item in series:
            if item.get("coverageStart") and item["coverageStart"] == latest_start and len(series) > 1:
                earlier = [entry for entry in series if entry.get("coverageStart", latest_start) < latest_start]
                if earlier:
                    warnings.append(f"{item['symbol']} begins later than at least one other selected series.")
            if item.get("coverageEnd") and item["coverageEnd"] < max(entry.get("coverageEnd", earliest_end) for entry in series):
                warnings.append(f"{item['symbol']} ends before at least one other selected series.")
    if scale == "absolute" and series:
        positive_prices = [float(item["endPrice"]) for item in series if float(item.get("endPrice") or 0) > 0]
        if positive_prices and max(positive_prices) / min(positive_prices) >= 100:
            warnings.append("Absolute USD mode compresses lower-priced lines because selected prices differ by more than 100x.")

    return {
        "ok": successful_primary,
        "verified": successful_primary,
        "partial": bool(failures),
        "sample": False,
        "period": period,
        "scale": scale,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "series": series,
        "failures": failures,
        "warnings": list(dict.fromkeys(warnings)),
        "sources": [item["source"] for item in series],
    }


def handle_market_history(params: dict[str, list[str]]) -> dict:
    token_id = (params.get("token") or [""])[0].strip().lower()
    period = (params.get("period") or ["30d"])[0].strip()
    compare = (params.get("compare") or [""])[0].strip().upper()

    try:
        brand = get_analytics_brand(token_id)
    except ValueError as exc:
        allowed = ", ".join(sorted(TOKEN_CONFIG))
        raise ValueError(f"token must be one of: {allowed}") from exc
    if period not in PERIOD_CONFIG:
        raise ValueError("Unsupported period")
    if compare:
        compare = _clean_symbol(compare)

    cache_key = (token_id, period, compare)
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached and monotonic() - cached[0] < _CACHE_SECONDS:
            return {**cached[1], "cached": True}

    token = {"name": brand["name"], "symbol": brand["symbol"], **brand["market"]}
    primary, primary_source = _gecko_history(token, period)
    comparison = comparison_source = None
    if compare:
        comparison, comparison_source = _binance_history(compare, period)

    result = {
        "ok": True,
        "verified": True,
        "sample": False,
        "period": period,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "primary": primary,
        "comparison": comparison,
        "sources": [source for source in (primary_source, comparison_source) if source],
        "cached": False,
    }
    with _CACHE_LOCK:
        _CACHE[cache_key] = (monotonic(), result)
    return result
