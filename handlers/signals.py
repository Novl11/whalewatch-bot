from aiogram import Router, types
from aiogram.filters import Command
from services.signals import scan_signals
from config import SCAN_INTERVAL_MINUTES
from utils.footer import add_footer

router = Router()


def _fmt(result: dict) -> str:
    lines = ["📊 *Торговые сигналы*\n"]

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
        lines.append("_Нет уверенных LONG_")

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
        lines.append("_Нет уверенных SHORT_")

    lines.append("")
    lines.append(f"⏱ Сканируется топ-200 монет каждые {SCAN_INTERVAL_MINUTES} мин")
    return add_footer("\n".join(lines))


@router.message(Command("signals"))
async def signals(message: types.Message):
    msg = await message.answer("🔍 *Сканирую 200 монет…*", parse_mode="Markdown")
    try:
        result = await scan_signals()
    except Exception as e:
        await msg.edit_text(f"❌ *Ошибка:* {e}", parse_mode="Markdown")
        return

    text = _fmt(result)
    try:
        await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
