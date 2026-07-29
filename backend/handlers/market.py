"""Verified public-market history for RZWire analytics posts."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from time import monotonic, sleep

import requests


GECKO_BASE = "https://api.geckoterminal.com/api/v2"
BINANCE_BASE = "https://api.binance.com/api/v3"
GECKO_HEADERS = {
    "Accept": "application/json;version=20230203",
    "User-Agent": "RZWire/1.0 market-analytics",
}

TOKEN_CONFIG = {
    "mgc": {
        "name": "MGC Coin",
        "symbol": "MGC",
        "network": "bsc",
        "contract": "0xbb73BB2505AC4643d5C0a99c2A1F34B3DfD09D11",
        "pool": "0x771e1c638a9409bfc93158588f1745f638f4d10b",
        "poolName": "RZ / MGC",
        "tokenSide": "quote",
    },
    "oasis": {
        "name": "Oasis Coin",
        "symbol": "OASIS",
        "network": "bsc",
        "contract": "0x1a4D41219C547f3A0EE36cf3d9E68F80699cF283",
        "pool": "0xc60bb735abcaa4be9a271bfe3af2fad19a953397",
        "poolName": "OASIS / MGC",
        "tokenSide": "base",
    },
    "jewelry": {
        "name": "Jewelry Coin",
        "symbol": "JEWELRY",
        "network": "bsc",
        "contract": "0xf04FaB6Dda66261eaBfD65e92A6b81dDaF6a950a",
        "pool": "0xd85df7190cdc09a42d7a2567f68812128c71e9a7",
        "poolName": "Jewelry / MGC",
        "tokenSide": "base",
    },
}

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

COMPARE_SYMBOLS = {"BTC", "XRP", "ETH", "BNB"}
_CACHE: dict[tuple[str, str, str], tuple[float, dict]] = {}
_CACHE_LOCK = Lock()
_CACHE_SECONDS = 60


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


def handle_market_history(params: dict[str, list[str]]) -> dict:
    token_id = (params.get("token") or [""])[0].strip().lower()
    period = (params.get("period") or ["30d"])[0].strip()
    compare = (params.get("compare") or [""])[0].strip().upper()

    if token_id not in TOKEN_CONFIG:
        raise ValueError("token must be mgc, oasis, or jewelry")
    if period not in PERIOD_CONFIG:
        raise ValueError("Unsupported period")
    if compare and compare not in COMPARE_SYMBOLS:
        raise ValueError("Unsupported comparison coin")

    cache_key = (token_id, period, compare)
    with _CACHE_LOCK:
        cached = _CACHE.get(cache_key)
        if cached and monotonic() - cached[0] < _CACHE_SECONDS:
            return {**cached[1], "cached": True}

    primary, primary_source = _gecko_history(TOKEN_CONFIG[token_id], period)
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
