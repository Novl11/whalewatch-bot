import asyncio
from services.binance import fetch_all_tickers, fetch_ticker_24h
from services.futures_analysis import analyze_futures
from utils.footer import BOT_LINK

TOP_COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "DOT", "AVAX"]
POST_INTERVAL = 4 * 3600  # 4 hours


async def generate_digest() -> str:
    tickers = await fetch_all_tickers()
    usdt_pairs = {t["symbol"].replace("USDT", ""): t for t in tickers if t["symbol"].endswith("USDT")}

    lines = [f"🐋 *WhaleWatch — Дайджест рынка ({POST_INTERVAL // 3600}ч)*\n"]

    for coin in TOP_COINS:
        t = usdt_pairs.get(coin)
        if not t:
            continue
        price = float(t.get("lastPrice", 0))
        change = float(t.get("priceChangePercent", 0))
        emoji = "🟢" if change >= 0 else "🔴"
        vol = float(t.get("quoteVolume", 0))

        change_str = f"{emoji} {change:+.2f}%"
        line = f"• *{coin}* ${price:,.2f} | {change_str} | Vol: ${vol/1e6:.0f}M"

        try:
            f = await analyze_futures(coin)
            if f and f.get("verdict"):
                line += f" | {f['verdict']}"
        except Exception:
            pass

        lines.append(line)

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━",
        "",
        f"📊 *Топ за 24ч:* /gainers | 📉 *Падение:* /losers",
        f"😱 *Fear & Greed:* /fng | 🌍 *Обзор:* /market",
        f"🔥 *Фьючерсы:* /futures BTC | *Pro:* /pro",
        "",
        f"Анализируй любую монету: @WhaleAnalyst_bot",
    ])
    return "\n".join(lines)


async def channel_poster(bot):
    from config import CHANNEL_ID
    if not CHANNEL_ID:
        return

    await asyncio.sleep(60)
    while True:
        try:
            digest = await generate_digest()
            await bot.send_message(CHANNEL_ID, digest, parse_mode="Markdown")
        except Exception as e:
            print(f"Channel post error: {e}")
        await asyncio.sleep(POST_INTERVAL)
