from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import get_or_create_user
from utils.keyboards import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
    )
    is_pro = user and user["plan"] == "pro"
    trial_available = not is_pro and user.get("trial_futures_used", 0) < 1
    name = message.from_user.first_name or "Трейдер"

    text = (
        f"🐋 *Привет, {name}!*\n\n"
        "Я *WhaleWatch Bot* — крипто-терминал.\n\n"
        "📊 *Анализ Spot и Futures*\n"
        "📈 18 технических индикаторов\n"
        "🔥 Funding rate, OI, L/S ratio\n"
        "🔔 Ценовые оповещения\n\n"
        f"Тариф: {'⭐ PRO' if is_pro else '🆓 Бесплатный'}\n"
    )
    if not is_pro:
        text += (
            "\n*Бесплатно:* все монеты, спот, базовые индикаторы + 1 пробный фьючерс.\n"
            "*Pro:* все 18 индикаторов, безлимитные фьючерсы, безлимитные оповещения.\n\n"
            "Купи /pro для полного доступа."
        )

    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(is_pro, trial_available))
