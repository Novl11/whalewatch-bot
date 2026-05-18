import aiohttp
import ssl
import certifi

_SSL_CTX = ssl.create_default_context(cafile=certifi.where())
_cache: dict[str, float] = {}
_cache_time = 0.0

CURRENCY_SYMBOLS = {
    "usd": "$",
    "uah": "₴",
    "rub": "₽",
    "eur": "€",
}


async def fetch_fiat_rates() -> dict[str, float]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd,uah,rub,eur"
    try:
        connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url, headers={"Accept": "application/json"}) as resp:
                if resp.status != 200:
                    return {"usd": 1.0, "uah": 41.0, "rub": 88.0, "eur": 0.92}
                data = await resp.json()
                tether = data.get("tether", {})
                return {
                    "usd": float(tether.get("usd", 1)),
                    "uah": float(tether.get("uah", 41)),
                    "rub": float(tether.get("rub", 88)),
                    "eur": float(tether.get("eur", 0.92)),
                }
    except Exception:
        return {"usd": 1.0, "uah": 41.0, "rub": 88.0, "eur": 0.92}


def format_fiat(usdt_amount: float, rates: dict[str, float]) -> str:
    parts = []
    for code in ("usd", "uah", "rub", "eur"):
        val = usdt_amount * rates.get(code, 1)
        symbol = CURRENCY_SYMBOLS.get(code, code.upper())
        if code == "rub":
            parts.append(f"~{val:.0f}{symbol}")
        else:
            parts.append(f"~{val:.2f}{symbol}")
    return " / ".join(parts)
