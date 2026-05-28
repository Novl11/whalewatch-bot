"""Персональный бот сигналов. Запускается как фоновый таск из main.py"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from services.signals import scan_signals

ADMIN_ID = int(os.getenv("ADMIN_ID", "7628819631"))
SIGNALS_BOT_TOKEN = os.getenv("SIGNALS_BOT_TOKEN", "")
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL", "30"))

logger = logging.getLogger(__name__)

bot = Bot(token=SIGNALS_BOT_TOKEN)
dp = Dispatcher()


def _fmt(result: dict, header: str = "") -> str:
    lines = [header] if header else []
    lines.append("🟢 *LONG*")
    for s in result.get("long", []):
        r = ", ".join(s["reasons"])
        funding = f"funding {s['funding']:+.3f}%" if s["funding"] is not None else ""
        lines.append(f"• *{s['coin']}* ${s['price']:,.2f} | RSI {s['rsi']:.0f} | {funding} | {r}")
    if not result.get("long"):
        lines.append("_Нет_")
    lines.append("")
    lines.append("🔴 *SHORT*")
    for s in result.get("short", []):
        r = ", ".join(s["reasons"])
        funding = f"funding {s['funding']:+.3f}%" if s["funding"] is not None else ""
        lines.append(f"• *{s['coin']}* ${s['price']:,.2f} | RSI {s['rsi']:.0f} | {funding} | {r}")
    if not result.get("short"):
        lines.append("_Нет_")
    lines.append("")
    lines.append(f"⏱ Каждые {SCAN_INTERVAL_MINUTES} мин · /signals ручной запрос")
    return "\n".join(lines)


async def scan_loop():
    """Background: scan every N minutes, send to admin."""
    await asyncio.sleep(15)

    for attempt in range(30):
        try:
            await bot.send_chat_action(ADMIN_ID, "typing")
            break
        except Exception:
            logger.info("Жду пока админ запустит @WhaleSignals_bot... (%d/30)", attempt + 1)
            await asyncio.sleep(5)
    else:
        logger.warning("Админ не запустил бота")

    logger.info("Сканер запущен, интервал %d мин", SCAN_INTERVAL_MINUTES)
    while True:
        try:
            result = await scan_signals()
            text = _fmt(result, "📊 *Авто-скан сигналов*\n")
            await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Ошибка скана: %s", e)
        await asyncio.sleep(SCAN_INTERVAL_MINUTES * 60)


@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    await msg.answer(
        f"👋 *WhaleSignals Bot*\n\n"
        f"Каждые {SCAN_INTERVAL_MINUTES} мин сканирую топ-100 монет → сигналы.\n\n"
        f"/signals — сигналы сейчас\n"
        f"/start — это сообщение",
        parse_mode="Markdown",
    )


@dp.message(Command("signals"))
async def cmd_signals(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    m = await msg.answer("🔍 *Сканирую…*", parse_mode="Markdown")
    try:
        result = await scan_signals()
        await m.edit_text(_fmt(result, "📊 *Сигналы сейчас*\n"), parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        await m.edit_text(f"❌ *Ошибка:* {e}", parse_mode="Markdown")


async def start_polling():
    asyncio.create_task(scan_loop())
    await dp.start_polling(bot)
