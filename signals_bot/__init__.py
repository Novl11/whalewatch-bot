import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from services.signals import scan_signals

logger = logging.getLogger("signals_bot")

TOKEN = os.getenv("SIGNALS_BOT_TOKEN", "")
ADMIN = int(os.getenv("ADMIN_ID", "7628819631"))
INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))

bot = Bot(token=TOKEN)
dp = Dispatcher()


def _fmt(result: dict, header: str = "") -> str:
    lines = ([header] if header else ["📊 *Сигналы*\n"])
    lines.append("🟢 *LONG*")
    for s in result.get("long", []):
        r = " · ".join(s["reasons"]) if s.get("reasons") else ""
        lines.append(
            f"• *{s['coin']}* ${s['price']:,.2f} ({s['change']:+.2f}%) — {s['signal']}\n"
            f"   RSI {s['rsi']:.0f} | ADX {s['adx']:.0f}"
            + (f" | Funding {s['funding']:+.3f}%" if s.get("funding") is not None else "")
            + (f"\n   {r}" if r else "")
        )
    if not result.get("long"):
        lines.append("_Нет_")
    lines.append("")
    lines.append("🔴 *SHORT*")
    for s in result.get("short", []):
        r = " · ".join(s["reasons"]) if s.get("reasons") else ""
        lines.append(
            f"• *{s['coin']}* ${s['price']:,.2f} ({s['change']:+.2f}%) — {s['signal']}\n"
            f"   RSI {s['rsi']:.0f} | ADX {s['adx']:.0f}"
            + (f" | Funding {s['funding']:+.3f}%" if s.get("funding") is not None else "")
            + (f"\n   {r}" if r else "")
        )
    if not result.get("short"):
        lines.append("_Нет_")
    lines.append("")
    lines.append(f"⏱ Каждые {INTERVAL} мин · /signals ручной запрос")
    return "\n".join(lines)


async def auto_scan():
    await asyncio.sleep(30)
    logger.info("Auto-scan starts every %d min", INTERVAL)
    while True:
        try:
            data = await scan_signals()
            await bot.send_message(ADMIN, _fmt(data, "📊 *Авто-скан*\n"), parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.warning("Auto-scan: %s", e)
        await asyncio.sleep(INTERVAL * 60)


@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer(
        f"👋 *WhaleSignals*\n\n"
        f"Каждые {INTERVAL} мин — авто-скан топ-200 монет.\n"
        f"/signals — сигналы сейчас\n"
        f"/start — это сообщение",
        parse_mode="Markdown",
    )


@dp.message(Command("signals"))
async def signals(msg: types.Message):
    m = await msg.answer("🔍 *Сканирую 200 монет…*", parse_mode="Markdown")
    try:
        data = await scan_signals()
        await m.edit_text(_fmt(data), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await m.edit_text(f"❌ *Ошибка:* {e}", parse_mode="Markdown")


@dp.message(Command("status"))
async def status(msg: types.Message):
    """Диагностика: проверка связи с Binance."""
    from services.binance import fetch_all_futures_tickers, fetch_klines
    lines = ["📊 *Статус*\n"]
    try:
        t = await fetch_all_futures_tickers()
        lines.append(f"✅ Binance: {len(t)} USDT пар")
        btc = next((x for x in t if x["symbol"] == "BTCUSDT"), None)
        if btc:
            lines.append(f"BTC: ${float(btc['lastPrice']):,.2f}")
    except Exception as e:
        lines.append(f"❌ Binance: {e}")
    try:
        k = await fetch_klines("BTC", "1h", 2)
        lines.append(f"✅ Klines: {len(k)} свечей")
    except Exception as e:
        lines.append(f"❌ Klines: {e}")
    await msg.answer("\n".join(lines), parse_mode="Markdown")


async def start_polling():
    asyncio.create_task(auto_scan())
    await dp.start_polling(bot)
