from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import aiohttp
import ssl
import certifi

router = Router()
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


@router.message(Command("market"))
async def cmd_market(message: Message):
    msg = await message.answer("⏳ Загружаю обзор рынка...")
    try:
        connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(
                "https://api.coingecko.com/api/v3/global"
            ) as r:
                data = await r.json()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка загрузки: {e}")
        return

    d = data.get("data", {})

    total_cap = d.get("total_market_cap", {}).get("usd", 0)
    total_vol = d.get("total_volume", {}).get("usd", 0)
    btc_dom = d.get("market_cap_percentage", {}).get("btc", 0)
    eth_dom = d.get("market_cap_percentage", {}).get("eth", 0)
    active_cryptos = d.get("active_cryptocurrencies", 0)

    def fmt(n):
        if n >= 1_000_000_000_000:
            return f"${n/1_000_000_000_000:.2f}T"
        return f"${n/1_000_000_000:.2f}B"

    lines = [
        "🌍 *Обзор крипторынка*\n",
        f"🏆 BTC доминация: *{btc_dom:.2f}%*",
        f"🥈 ETH доминация: *{eth_dom:.2f}%*\n",
        f"💰 Общая капитализация: *{fmt(total_cap)}*",
        f"📊 Объём за 24ч: *{fmt(total_vol)}*\n",
        f"🪙 Активных криптовалют: *{active_cryptos}*",
    ]

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")
