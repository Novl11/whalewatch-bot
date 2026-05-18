from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from services.binance import fetch_all_tickers

router = Router()


@router.message(Command("gainers"))
async def cmd_gainers(message: Message):
    await show_top(message, top_type="gainers")


@router.message(Command("losers"))
async def cmd_losers(message: Message):
    await show_top(message, top_type="losers")


@router.message(Command("volume"))
async def cmd_volume(message: Message):
    await show_top(message, top_type="volume")


async def show_top(message: Message, top_type: str):
    msg = await message.answer("⏳ Загружаю данные...")
    try:
        tickers = await fetch_all_tickers()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка загрузки: {e}")
        return

    if top_type == "gainers":
        key = lambda t: t.get("priceChangePercent", 0)
        best = sorted(tickers, key=key, reverse=True)[:10]
        title = "🚀 Топ роста за 24ч"
        fmt = lambda t: f"+{t['priceChangePercent']:.2f}%"
    elif top_type == "losers":
        key = lambda t: t.get("priceChangePercent", 0)
        best = sorted(tickers, key=key)[:10]
        title = "📉 Топ падения за 24ч"
        fmt = lambda t: f"{t['priceChangePercent']:.2f}%"
    else:
        key = lambda t: float(t.get("quoteVolume", 0))
        best = sorted(tickers, key=key, reverse=True)[:10]
        title = "📊 Самые активные по объёму"
        fmt = lambda t: f"${float(t['quoteVolume']):,.0f}"

    lines = [f"📌 *{title}*\n"]
    for i, t in enumerate(best, 1):
        symbol = t["symbol"].replace("USDT", "")
        price = float(t.get("lastPrice", 0))
        extra = fmt(t)
        lines.append(f"{i}. *{symbol}* — ${price:,.2f} ({extra})")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")
