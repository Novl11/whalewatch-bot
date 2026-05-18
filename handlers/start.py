import re
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import aiosqlite
from pathlib import Path
from database import get_or_create_user, get_user, is_pro, add_pro_days
from utils.keyboards import main_menu

router = Router()
DB_PATH = Path(__file__).parent.parent / "bot.db"
REFERRALS_NEEDED = 3
BONUS_DAYS = 1


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    args = message.text.split(maxsplit=1)
    ref_by = None
    if len(args) > 1:
        m = re.match(r"ref_(\d+)", args[1])
        if m:
            ref_by = int(m.group(1))

    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )

    if ref_by and ref_by != user["id"] and not user.get("referrer_id"):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET referrer_id = ? WHERE telegram_id = ?",
                (ref_by, message.from_user.id),
            )
            await db.execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE id = ?",
                (ref_by,),
            )
            cur = await db.execute(
                "SELECT telegram_id, referral_count FROM users WHERE id = ?", (ref_by,)
            )
            row = await cur.fetchone()
            await db.commit()
            if row and row[1] % REFERRALS_NEEDED == 0:
                await add_pro_days(row[0], BONUS_DAYS)
                try:
                    await message.bot.send_message(
                        row[0],
                        f"🎉 *Новый реферал!*\n\n"
                        f"Ты привёл *{row[1]}* друзей!\n"
                        f"+{BONUS_DAYS} день Pro начислен.\n"
                        f"Продолжай в том же духе → /referral",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass

    is_pro_user = user and user["plan"] == "pro"
    trial_available = not is_pro_user and user.get("trial_futures_used", 0) < 1
    name = message.from_user.first_name or "Трейдер"

    text = (
        f"🐋 *Привет, {name}!*\n\n"
        "Я *WhaleWatch Bot* — крипто-терминал.\n\n"
        "📊 *Анализ Spot и Futures*\n"
        "📈 18 технических индикаторов\n"
        "🔥 Funding rate, OI, L/S ratio\n"
        "🔔 Ценовые оповещения\n\n"
        f"Тариф: {'⭐ PRO' if is_pro_user else '🆓 Бесплатный'}\n"
    )
    if not is_pro_user:
        text += (
            "\n*Бесплатно:* все монеты, спот, базовые индикаторы + 1 пробный фьючерс.\n"
            "*Pro:* все 18 индикаторов, безлимитные фьючерсы, безлимитные оповещения.\n\n"
            "Купи /pro для полного доступа."
        )
    if ref_by:
        text += "\n\n👋 Ты пришёл по реферальной ссылке!"

    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(is_pro_user, trial_available))
