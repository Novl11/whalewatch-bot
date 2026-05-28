import asyncio
import aiohttp
import ssl
import certifi
from config import BINANCE_SPOT_API, BINANCE_FUTURES_API
from utils.coins import binance_symbol, binance_futures_symbol

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


async def _fetch(url: str, timeout: int = 10) -> dict | list | None:
    try:
        connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as session:
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


# ── Spot ──────────────────────────────────────────


async def fetch_ticker_24h(coin: str) -> dict | None:
    symbol = binance_symbol(coin)
    data = await _fetch(f"{BINANCE_SPOT_API}/api/v3/ticker/24hr?symbol={symbol}")
    return data if isinstance(data, dict) else None


async def fetch_klines(
    coin: str, interval: str = "15m", limit: int = 200
) -> list:
    symbol = binance_symbol(coin)
    data = await _fetch(
        f"{BINANCE_SPOT_API}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    )
    if isinstance(data, list):
        return [
            {
                "time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            for k in data
        ]
    return []


async def fetch_all_tickers() -> list[dict]:
    data = await _fetch(f"{BINANCE_SPOT_API}/api/v3/ticker/24hr")
    if isinstance(data, list):
        return [t for t in data if t.get("symbol", "").endswith("USDT")]
    return []


async def fetch_all_futures_tickers() -> list[dict]:
    data = await _fetch(f"{BINANCE_FUTURES_API}/fapi/v1/ticker/24hr")
    if isinstance(data, list):
        return [t for t in data if t.get("symbol", "").endswith("USDT")]
    return []


async def fetch_spot_price(coin: str) -> float | None:
    symbol = binance_symbol(coin)
    data = await _fetch(f"{BINANCE_SPOT_API}/api/v3/ticker/price?symbol={symbol}")
    if isinstance(data, dict):
        return float(data.get("price", 0))
    return None


# ── Futures ticker & funding ─────────────────────


async def fetch_futures_ticker(coin: str) -> dict | None:
    symbol = binance_futures_symbol(coin)
    return await _fetch(f"{BINANCE_FUTURES_API}/fapi/v1/ticker/24hr?symbol={symbol}")


async def fetch_funding_rate(coin: str) -> dict | None:
    symbol = binance_futures_symbol(coin)
    return await _fetch(f"{BINANCE_FUTURES_API}/fapi/v1/premiumIndex?symbol={symbol}")


async def fetch_funding_rate_history(
    coin: str, limit: int = 100
) -> list[dict]:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/fapi/v1/fundingRate?symbol={symbol}&limit={limit}"
    )
    return data if isinstance(data, list) else []


# ── Open Interest ─────────────────────────────────


async def fetch_open_interest(coin: str) -> float | None:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(f"{BINANCE_FUTURES_API}/fapi/v1/openInterest?symbol={symbol}")
    if isinstance(data, dict):
        return float(data.get("openInterest", 0))
    return None


async def fetch_oi_24h_ago(coin: str) -> float | None:
    symbol = binance_futures_symbol(coin)
    now_ts = int(asyncio.get_event_loop().time() * 1000)
    day_ago = now_ts - 86_400_000
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/openInterestHist?symbol={symbol}&period=1h&limit=1&startTime={day_ago}"
    )
    if isinstance(data, list) and len(data) > 0:
        return float(data[0].get("sumOpenInterest", 0))
    return None


async def fetch_oi_history(coin: str, period: str = "1h", limit: int = 24) -> list[dict]:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/openInterestHist?symbol={symbol}&period={period}&limit={limit}"
    )
    return data if isinstance(data, list) else []


# ── Long / Short ratios ──────────────────────────


async def fetch_long_short_ratio(coin: str, period: str = "5m") -> float | None:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/globalLongShortAccountRatio?symbol={symbol}&period={period}&limit=1"
    )
    if isinstance(data, list) and len(data) > 0:
        return float(data[0].get("longShortRatio", 1))
    return None


async def fetch_top_trader_ls_ratio(coin: str, period: str = "5m") -> float | None:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/topLongShortAccountRatio?symbol={symbol}&period={period}&limit=1"
    )
    if isinstance(data, list) and len(data) > 0:
        return float(data[0].get("longShortRatio", 1))
    return None


async def fetch_top_trader_position_ratio(coin: str, period: str = "5m") -> dict | None:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/topLongShortPositionRatio?symbol={symbol}&period={period}&limit=1"
    )
    if isinstance(data, list) and len(data) > 0:
        return {
            "long_position": float(data[0].get("longAccount", 0)),
            "short_position": float(data[0].get("shortAccount", 0)),
        }
    return None


# ── Trades / volume ──────────────────────────────


async def fetch_futures_klines(
    coin: str, interval: str = "15m", limit: int = 100
) -> list:
    symbol = binance_futures_symbol(coin)
    data = await _fetch(
        f"{BINANCE_FUTURES_API}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    )
    if isinstance(data, list):
        return [
            {
                "time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
            }
            for k in data
        ]
    return []


async def fetch_taker_volume(coin: str, period: str = "15m", limit: int = 24) -> dict:
    symbol = binance_futures_symbol(coin)
    buy = await _fetch(
        f"{BINANCE_FUTURES_API}/futures/data/takerlongshortRatio?symbol={symbol}&period={period}&limit={limit}"
    )
    if isinstance(buy, list) and len(buy) > 0:
        total = len(buy)
        buys = sum(1 for b in buy if float(b.get("buySellRatio", 1)) > 1)
        avg = sum(float(b.get("buyVol", 0)) for b in buy) / total
        return {
            "buy_ratio": buys / total if total else 0.5,
            "avg_buy_vol": avg,
        }
    return {"buy_ratio": 0.5, "avg_buy_vol": 0}


async def fetch_futures_24h_agg(coin: str) -> dict:
    symbol = binance_futures_symbol(coin)
    stats = await _fetch(f"{BINANCE_FUTURES_API}/fapi/v1/ticker/24hr?symbol={symbol}")
    if not isinstance(stats, dict):
        return {}
    return {
        "high": float(stats.get("highPrice", 0)),
        "low": float(stats.get("lowPrice", 0)),
        "volume": float(stats.get("volume", 0)),
        "quote_volume": float(stats.get("quoteVolume", 0)),
        "change": float(stats.get("priceChangePercent", 0)),
        "last": float(stats.get("lastPrice", 0)),
        "count": int(stats.get("count", 0)),
    }
