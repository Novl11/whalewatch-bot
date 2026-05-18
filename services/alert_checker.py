import asyncio
import aiohttp
import ssl
import certifi
from config import BINANCE_SPOT_API
from utils.coins import binance_symbol, display_coin
from utils.formatting import format_price
from handlers.alerts import ALERT_TYPES
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "bot.db"
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

_notified: set[int] = set()
_CLEANUP_CYCLE = 0
_fetcher_session: aiohttp.ClientSession | None = None


async def _get_session() -> aiohttp.ClientSession:
    global _fetcher_session
    if _fetcher_session is None or _fetcher_session.closed:
        _fetcher_session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=_SSL_CTX),
            timeout=aiohttp.ClientTimeout(total=5),
        )
    return _fetcher_session


async def _fetch_price(symbol: str) -> float | None:
    try:
        s = await _get_session()
        async with s.get(f"{BINANCE_SPOT_API}/api/v3/ticker/price?symbol={symbol}") as r:
            async with s.get(f"{BINANCE_SPOT_API}/api/v3/ticker/price?symbol={symbol}") as r:
                if r.status == 200:
                    d = await r.json()
                    return float(d.get("price", 0))
    except Exception:
        return None
    return None


async def check_alerts(bot):
    global _CLEANUP_CYCLE
    _CLEANUP_CYCLE += 1

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT a.*, u.telegram_id FROM alerts a JOIN users u ON a.user_id = u.id WHERE a.active = 1"
        )
        alerts = await cur.fetchall()

    # cleanup stale notified ids every 50 cycles (~25 min)
    if _CLEANUP_CYCLE % 50 == 0:
        active_ids = {a["id"] for a in alerts}
        stale = _notified - active_ids
        if stale:
            _notified.difference_update(stale)

    if not alerts:
        return

    coins_needed = set()
    for a in alerts:
        coins_needed.add(a["coin"])

    prices: dict[str, float] = {}
    for coin in coins_needed:
        sym = binance_symbol(coin)
        p = await _fetch_price(sym)
        if p:
            prices[coin] = p
        await asyncio.sleep(0.1)

    for a in alerts:
        alert_id = a["id"]
        if alert_id in _notified:
            continue

        coin = a["coin"]
        price = prices.get(coin)
        if price is None:
            continue

        alert_type = a["alert_type"]
        value = a["value"]
        triggered = False

        if alert_type == "price_above" and price >= value:
            triggered = True
        elif alert_type == "price_below" and price <= value:
            triggered = True

        if triggered:
            _notified.add(alert_id)
            label = ALERT_TYPES.get(alert_type, alert_type)
            try:
                await bot.send_message(
                    a["telegram_id"],
                    f"🔔 *Ценовое оповещение!*\n\n"
                    f"Монета: *{display_coin(coin)}*\n"
                    f"Условие: {label} {format_price(value)}\n"
                    f"Текущая цена: {format_price(price)}\n\n"
                    f"Оповещение деактивировано.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass

            async with aiosqlite.connect(DB_PATH) as db2:
                await db2.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
                await db2.commit()
