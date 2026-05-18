import asyncio, re, time
from aiogram import Router, F, types
from services.binance import fetch_ticker_24h
from utils.formatting import format_price, format_change
from utils.coins import COIN_WHITELIST, display_coin
from utils.footer import BOT_LINK

router = Router()

COIN_PATTERN = re.compile(
    r"(?i)(?:цена|price|сколько|стоит|курс|прайс)\s*(btc|bitcoin|eth|ethereum|sol|solana|xrp|ada|doge|trx|link|dot|bnb|avax|matic|pol|ton|shib|pepe|bonk|floki|wifi|jup|sui|sei|apt|arb|op|near|inja|atom|lite|ltc|bch|fil|etc|xtz|icp|render|fet|grt|aave|algo|stx|imx|ldo|pendle|rune|egld|sand|mana|axs|flow|kas|snx|crv|theta|ena|ondo|ordi|strk|dydx|gmx|comp|zec|tao|cake|ens|chz|gala|rosa|iota|qnt|blur|ape|mina|ckb|cfx|cello)",
)
RSI_PATTERN = re.compile(r"(?i)(rsi|индикатор|сигнал|анализ|trend|тренд|лонг|шорт|buy|sell)\s*(btc|bitcoin|eth|ethereum|sol|solana|xrp|ada|doge|trx)")
ANALYSIS_PATTERN = re.compile(r"(?i)(to\s*the\s*moon|moon|растёт|падает|обвал|x10|x100|гарант|сигнал|verdict|вердикт)")
WELCOME_PATTERN = re.compile(r"(?i)(привет|хай|хелло|hi|hello|здарова|куда)\s*бота|what can.*bot|бот.*умеет")


_LAST_REPLY: dict[int, float] = {}
COOLDOWN = 10


async def _reply_with_price(coins: list[str], msg: types.Message):
    for coin in coins[:3]:
        ticker = await fetch_ticker_24h(coin)
        if ticker:
            price = float(ticker.get("lastPrice", 0))
            change = float(ticker.get("priceChangePercent", 0))
            high = float(ticker.get("highPrice", 0))
            low = float(ticker.get("lowPrice", 0))
            vol = float(ticker.get("quoteVolume", 0))

            text = (
                f"💵 *{display_coin(coin)} / USDT*\n"
                f"💰 {format_price(price)} ({format_change(change)})\n"
                f"📈 {format_price(high)} / 📉 {format_price(low)} | 📦 ${vol/1e6:.1f}M\n\n"
                f"Подробнее: @WhaleAnalyst_bot\n{BOT_LINK}"
            )
            await msg.reply(text, parse_mode="Markdown")
            await asyncio.sleep(0.3)


@router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def group_autoreply(message: types.Message):
    text = message.text.strip()
    if not text or text.startswith("/"):
        return

    chat_id = message.chat.id
    now = time.time()
    if chat_id in _LAST_REPLY and now - _LAST_REPLY[chat_id] < COOLDOWN:
        return

    m = COIN_PATTERN.search(text)
    coin_name = m.group(2) if m and m.lastindex and m.group(2) else None
    if not coin_name:
        m2 = RSI_PATTERN.search(text)
        coin_name = m2.group(2) if m2 and m2.lastindex else None

    if coin_name:
        _LAST_REPLY[chat_id] = now
        coin = coin_name.upper()
        coin_map = {
            "BITCOIN": "BTC", "ETHEREUM": "ETH", "SOLANA": "SOL",
            "LITE": "LTC", "MATIC": "POL", "INJA": "INJ",
            "ROSA": "ROSE", "WIFI": "WIF",
        }
        coin = coin_map.get(coin, coin)
        if coin in COIN_WHITELIST:
            await _reply_with_price([coin], message)
            return

    if ANALYSIS_PATTERN.search(text):
        _LAST_REPLY[chat_id] = now
        await message.reply(
            f"🧐 Интересуешься криптой?\n\n"
            f"Попробуй @WhaleAnalyst_bot:\n"
            f"• /price BTC — цена и 24ч\n"
            f"• /indicators BTC — RSI, MACD, BB\n"
            f"• /futures BTC — фьючерсный анализ\n"
            f"• /fng — Fear & Greed Index\n"
            f"{BOT_LINK}",
            parse_mode="Markdown",
        )

    if WELCOME_PATTERN.search(text):
        _LAST_REPLY[chat_id] = now
        await message.reply(
            f"🐋 @WhaleAnalyst_bot — крипто-терминал!\n\n"
            f"• Цена 82 монет 24/7\n"
            f"• 18 индикаторов (RSI, MACD, BB)\n"
            f"• Фьючерсный анализ с вердиктом\n"
            f"• Fear & Greed, обзор рынка\n"
            f"• Ценовые оповещения\n\n"
            f"Бесплатно! Подробнее: /start",
            parse_mode="Markdown",
        )
