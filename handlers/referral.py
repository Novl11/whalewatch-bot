from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_or_create_user, get_user, is_pro
from utils.keyboards import main_menu

router = Router()

REFERRALS_NEEDED = 5
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
    needed = REFERRALS_NEEDED - progress
    bars = "▓" * progress + "░" * (REFERRALS_NEEDED - progress) if progress < REFERRALS_NEEDED else "▓" * REFERRALS_NEEDED

    text = (
        f"🤝 *Реферальная программа*\n\n"
        f"Приглашай друзей и получай *{BONUS_DAYS} день Pro* за каждые {REFERRALS_NEEDED} приглашений!\n\n"
        f"👥 Приглашено: *{ref_count}*\n"
        f"{bars} ({progress}/{REFERRALS_NEEDED})\n\n"
        f"👇 Твоя ссылка:\n"
        f"`{ref_link}`\n\n"
        f"Просто отправь её другу — когда он зайдёт в бота, тебе зачтётся."
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔗 Поделиться", url=f"https://t.me/share/url?url={ref_link}&text=🐋 WhaleWatch Bot — крипто-терминал в Telegram. Бесплатный анализ монет!"),
    )
    pro = await is_pro(uid)
    trial_available = not pro and user.get("trial_futures_used", 0) < 1
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu"))

    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())
