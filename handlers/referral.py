from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
from pathlib import Path
from database import get_or_create_user, get_user, is_pro

router = Router()
DB_PATH = Path(__file__).parent.parent / "bot.db"

REFERRALS_NEEDED = 3
BONUS_DAYS = 1


@router.message(Command("referral"))
async def cmd_referral(message: types.Message):
    uid = message.from_user.id
    user = await get_or_create_user(uid, message.from_user.username, message.from_user.first_name)

    ref_count = user.get("referral_count", 0)
    ref_id = user["id"]

    bot_username = (await message.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{ref_id}"

    progress = ref_count % REFERRALS_NEEDED
    bars = "▓" * progress + "░" * (REFERRALS_NEEDED - progress) if progress < REFERRALS_NEEDED else "▓" * REFERRALS_NEEDED

    pro = await is_pro(uid)
    pro_bonus = ref_count // REFERRALS_NEEDED
    pro_days = pro_bonus * BONUS_DAYS
    if pro:
        text = (
            f"🤝 *Реферальная программа*\n\n"
            f"⭐ *Ты уже Pro!* Новые рефералы добавляют дни.\n"
            f"Всего заработано: *{pro_days} дн. Pro*\n\n"
        )
    else:
        text = (
            f"🤝 *Реферальная программа*\n\n"
            f"Приглашай друзей — получи Pro!\n"
            f"• {REFERRALS_NEEDED} приглашений = {BONUS_DAYS} день Pro\n"
            f"• Безлимитное накопление дней\n\n"
        )

    text += (
        f"👥 Приглашено: *{ref_count}*\n"
        f"{bars} ({progress}/{REFERRALS_NEEDED})\n\n"
        f"👇 *Твоя ссылка:*\n"
        f"`{ref_link}`\n\n"
        f"Просто отправь её другу — когда он зайдёт в бота, тебе зачтётся."
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Поделиться", url=f"https://t.me/share/url?url={ref_link}&text=🐋 WhaleWatch Bot — крипто-терминал в Telegram. Бесплатный анализ монет!"),
        InlineKeyboardButton(text="📢 В канал", url=f"https://t.me/share/url?url={ref_link}&text=🐋 WhaleWatch Bot — крипто-терминал в Telegram!\n\n📊 Цена, RSI, MACD, BB, ATR\n🔥 Фьючерсы: funding, OI, L/S, вердикт\n😱 Fear & Greed Index\n📈 Топ за 24ч: /gainers /losers /volume\n\nБесплатно! 👇\n{ref_link}"),
    )
    builder.row(InlineKeyboardButton(text="🏆 Топ реферралов", callback_data="referral_top"))
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu"))

    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(lambda c: c.data == "referral_top")
async def referral_top_callback(callback: types.CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT username, first_name, referral_count FROM users WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT 10"
        )
        rows = await cur.fetchall()

    if not rows:
        await callback.answer("Пока никто не привёл друзей. Будь первым! 🚀", show_alert=True)
        return

    lines = ["🏆 *Топ реферралов*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, row in enumerate(rows):
        name = row["first_name"] or row["username"] or f"User_{i+1}"
        count = row["referral_count"]
        medal = medals[i] if i < 3 else f"{i+1}."
        lines.append(f"{medal} {name} — *{count} пригл.*")

    lines.extend([
        "",
        "━━━━━━━━━━━━━━━",
        "Приведи 3 друзей → 1 день Pro!",
        "Используй /referral",
    ])

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="menu"))

    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()
