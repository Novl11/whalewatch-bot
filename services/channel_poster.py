import asyncio, random
from services.binance import fetch_all_tickers
from services.futures_analysis import analyze_futures
from utils.footer import BOT_LINK

TOP_COINS = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "DOT", "AVAX"]
DIGEST_INTERVAL = 4 * 3600
PROMO_INTERVAL = 24 * 3600

PROMO_TEXTS = [
    (
        "🐋 *WhaleWatch Bot — твой крипто-терминал в Telegram*\n\n"
        "📊 *Анализируй любую монету:*\n"
        "• /price BTC — цена и 24ч статистика\n"
        "• /indicators BTC — RSI, MACD, BB, ATR и другие\n"
        "• /futures BTC — фьючерсный анализ с вердиктом\n"
        "• /fng — Fear & Greed Index\n"
        "• /market — обзор рынка\n\n"
        "🔥 *Фьючерсный анализ:* funding rate, Open Interest, L/S топ-трейдеров, тренд, вердикт LONG/SHORT\n\n"
        "💰 *Бесплатно:* все монеты, базовые индикаторы, 1 пробный фьючерс\n"
        "⭐ *Pro:* 10 USDT / 30 дней — все 18 индикаторов, все таймфреймы, безлимитные фьючерсы\n\n"
        f"👉 @WhaleAnalyst_bot"
    ),
    (
        "😱 *Fear & Greed Index* — покажи /fng боту @WhaleAnalyst_bot\n\n"
        "📈 Индикатор настроения рынка. Extreme Fear = &#x1F4AA; покупай, Extreme Greed = &#x1F6A9; продавай.\n\n"
        "А ещё бот умеет:\n"
        "• /gainers — топ роста за 24ч\n"
        "• /losers — топ падения\n"
        "• /volume — самые активные\n"
        "• /market — обзор всего рынка\n\n"
        "🐋 @WhaleAnalyst_bot — бесплатный крипто-терминал"
    ),
    (
        "📊 *18 технических индикаторов* в одном боте!\n\n"
        "🐋 @WhaleAnalyst_bot даёт:\n"
        "• RSI (Relative Strength Index)\n"
        "• MACD (Moving Average Convergence Divergence)\n"
        "• Bollinger Bands\n"
        "• ATR, Stochastic, ADX, CCI, WillR, MFI\n"
        "• EMA 9/21/50/200, SMA 20/50/200\n"
        "• OBV, VWAP\n\n"
        "Бесплатно: RSI + EMA21\n"
        "⭐ Pro: все 18, все таймфреймы (1m–4h)\n\n"
        f"👉 @WhaleAnalyst_bot"
    ),
]


async def generate_digest() -> str:
    tickers = await fetch_all_tickers()
    usdt_pairs = {t["symbol"].replace("USDT", ""): t for t in tickers if t["symbol"].endswith("USDT")}

    lines = [f"🐋 *WhaleWatch — Дайджест рынка*\n"]

    for coin in TOP_COINS:
        t = usdt_pairs.get(coin)
        if not t:
            continue
        price = float(t.get("lastPrice", 0))
        change = float(t.get("priceChangePercent", 0))
        emoji = "🟢" if change >= 0 else "🔴"
        vol = float(t.get("quoteVolume", 0))

        line = f"• *{coin}* ${price:,.2f} | {emoji} {change:+.2f}% | Vol: ${vol/1e6:.0f}M"

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
        f"Анализируй любую монету: @WhaleAnalyst_bot",
    ])
    return "\n".join(lines)


async def send_to_all_channels(bot, text: str):
    from config import CHANNEL_IDS
    for cid in CHANNEL_IDS:
        try:
            await bot.send_message(cid, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Channel {cid} error: {e}")
        await asyncio.sleep(1)


async def channel_poster(bot):
    from config import CHANNEL_IDS
    if not CHANNEL_IDS:
        print("No CHANNEL_IDS configured — channel poster disabled")
        return

    await asyncio.sleep(60)
    cycle = 0
    while True:
        try:
            if cycle % 6 == 0:
                promo = random.choice(PROMO_TEXTS)
                await send_to_all_channels(bot, promo)
            else:
                digest = await generate_digest()
                await send_to_all_channels(bot, digest)
        except Exception as e:
            print(f"Channel poster error: {e}")
        cycle += 1
        await asyncio.sleep(DIGEST_INTERVAL)
