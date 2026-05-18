from aiogram import Router, types
from aiogram.filters import Command
from utils.keyboards import main_menu
from database import is_pro, get_user

router = Router()


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    uid = message.from_user.id
    pro = await is_pro(uid)
    user = await get_user(uid)
    trial_available = not pro and user and user.get("trial_futures_used", 0) < 1
    text = (
        "🐋 *WhaleWatch Bot — Команды*\n\n"
        "/start — Главное меню\n"
        "/price <монета> — Цена + 24ч статистика\n"
        "/indicators <монета> — Технические индикаторы\n"
        "/futures <монета> — Фьючерсный анализ\n"
        "/gainers — Топ роста за 24ч\n"
        "/losers — Топ падения за 24ч\n"
        "/volume — Самые активные по объёму\n"
        "/fng — Fear & Greed Index\n"
        "/market — Обзор крипторынка\n"
        "/watchlist — Твой список монет\n"
        "/add <монета> — Добавить в список\n"
        "/remove <монета> — Удалить из списка\n"
        "/alert — Создать оповещение\n"
        "/alerts — Твои оповещения\n"
        "/pro — Купить Pro\n"
        "/referral — Пригласить друга, получить Pro\n"
        "/help — Это сообщение\n\n"
        "*Бесплатно:* все монеты, спот, базовые индикаторы, топ, FNG, обзор рынка + 1 пробный фьючерс\n"
        "*Pro:* все 18 индикаторов, все таймфреймы, безлимитные фьючерсы и оповещения"
        if not pro
        else "*У тебя Pro* — все функции открыты!"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu(pro, trial_available))
