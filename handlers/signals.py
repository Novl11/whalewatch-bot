from aiogram import Router, types
from aiogram.filters import Command
from services.signals import scan_signals
from utils.footer import add_footer

router = Router()


@router.message(Command("signals"))
async def signals(message: types.Message):
    """Show LONG/SHORT trading signals for top coins."""
    msg = await message.answer(
        "🔍 *Анализирую рынок…*"
    )

    try:
        result = await scan_signals()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка анализа: {e}")
        return

    long_list = result.get("long", [])
    short_list = result.get("short", [])

    lines = ["📊 *Торговые сигналы*\n"]

    lines.append("🟢 *LONG сигналы (недооценено)*")
    if long_list:
        for s in long_list:
            lines.append(s["text"])
    else:
        lines.append("_Нет сильных LONG сигналов_")
    lines.append("")

    lines.append("🔴 *SHORT сигналы (переоценено)*")
    if short_list:
        for s in short_list:
            lines.append(s["text"])
    else:
        lines.append("_Нет сильных SHORT сигналов_")
    lines.append("")

    lines.append(
        "_Сигнал когда: funding в экстремуме + RSI перекуплен/перепродан + тренд_\n"
        "_Не инвестиционная рекомендация_"
    )

    text = add_footer("\n".join(lines))
    try:
        await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception:
        await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)
