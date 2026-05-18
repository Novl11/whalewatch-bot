import re
from aiogram import Router, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.binance import fetch_ticker_24h, fetch_klines
from services.chart import _branded_chart_url
from utils.footer import BOT_LINK

router = Router()
COIN_PATTERN = re.compile(r"^([A-Za-z]+)")


@router.inline_query()
async def inline_query(query: types.InlineQuery):
    q = query.query.strip().upper()
    if not q:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="🐋 WhaleWatch Bot",
                description="Введи тикер монеты, например: BTC, ETH, SOL",
                input_message_content=InputTextMessageContent(
                    message_text=f"🐋 *WhaleWatch Bot*\n\nВведи название монеты, например:\n`@WhaleAnalyst_bot BTC`\n`@WhaleAnalyst_bot ETH`\n`@WhaleAnalyst_bot SOL`",
                    parse_mode="Markdown",
                ),
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🚀 Запустить", url=BOT_LINK)
                ).as_markup(),
            )
        ]
        await query.answer(results, cache_time=10, is_personal=True)
        return

    m = COIN_PATTERN.match(q)
    if not m:
        await query.answer([], cache_time=5, is_personal=True)
        return

    coin = m.group(1).upper()
    ticker = await fetch_ticker_24h(coin)
    if not ticker:
        results = [
            InlineQueryResultArticle(
                id="not_found",
                title=f"❌ {coin} не найден",
                description=f"Монета {coin} не найдена на Binance",
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ *{coin}* не найден на Binance.\n\nПроверь тикер или выбери другую монету.",
                    parse_mode="Markdown",
                ),
            )
        ]
        await query.answer(results, cache_time=10, is_personal=True)
        return

    price = float(ticker.get("lastPrice", 0))
    change = float(ticker.get("priceChangePercent", 0))
    high = float(ticker.get("highPrice", 0))
    low = float(ticker.get("lowPrice", 0))
    vol = float(ticker.get("quoteVolume", 0))
    emoji = "🟢" if change >= 0 else "🔴"

    klines = await fetch_klines(coin, "15m", 48)
    chart_url = _branded_chart_url(coin, klines) if klines else None

    text = (
        f"📊 *{coin}USDT*\n"
        f"{emoji} Цена: *${price:,.4f}*\n"
        f"24h: {emoji} *{change:+.2f}%*\n"
        f"📈 H: ${high:,.4f} | 📉 L: ${low:,.4f}\n"
        f"💧 Объём: ${vol/1e6:.2f}M\n\n"
        f"⚡ @WhaleAnalyst_bot"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Детальный анализ", url=f"https://t.me/WhaleAnalyst_bot?start=price_{coin}"))
    builder.row(InlineKeyboardButton(text="🐋 Открыть бота", url=BOT_LINK))

    result = InlineQueryResultArticle(
        id=coin,
        title=f"{coin} — ${price:,.2f} ({change:+.2f}%)",
        description=f"24h H:{high:.2f} L:{low:.2f} Vol:${vol/1e6:.1f}M",
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="Markdown",
        ),
        reply_markup=builder.as_markup(),
        thumbnail_url=chart_url,
    )

    await query.answer([result], cache_time=30, is_personal=True)
