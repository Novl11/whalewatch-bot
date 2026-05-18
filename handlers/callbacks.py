import re
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from database import is_pro, get_user
from utils.keyboards import main_menu, coin_selection

router = Router()

PAGE_PREFIXES = {"price", "indicators", "futures", "watch_add", "alert_coin"}


@router.callback_query(F.data == "top_menu")
async def top_menu_callback(callback: types.CallbackQuery):
    from utils.keyboards import top_menu_keyboard
    await callback.message.edit_text("📊 *Топ монет за 24ч*\n\nВыбери категорию:", parse_mode="Markdown", reply_markup=top_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("top:"))
async def top_callback(callback: types.CallbackQuery):
    from handlers.top import show_top
    top_type = callback.data.split(":", 1)[1]
    await callback.answer()
    await show_top(callback.message, top_type)


@router.callback_query(F.data == "market")
async def market_callback(callback: types.CallbackQuery):
    from handlers.market import cmd_market
    await callback.answer()
    await cmd_market(callback.message)


@router.callback_query(F.data == "fng")
async def fng_callback(callback: types.CallbackQuery):
    from handlers.fng import cmd_fng
    await callback.answer()
    await cmd_fng(callback.message)


@router.callback_query(F.data == "futures_locked")
async def futures_locked_callback(callback: types.CallbackQuery):
    await callback.answer(
        "🔒 Фьючерсы только для Pro.\n\nКупи /pro чтобы открыть funding rate, OI, L/S топ-трейдеров и торговый вердикт.",
        show_alert=True,
    )


@router.callback_query(F.data == "menu")
async def menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    pro = await is_pro(uid)
    user = await get_user(uid)
    trial_available = not pro and user and user.get("trial_futures_used", 0) < 1
    await callback.message.edit_text("Выбери опцию:", reply_markup=main_menu(pro, trial_available))
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    pro = await is_pro(uid)
    user = await get_user(uid)
    trial_available = not pro and user and user.get("trial_futures_used", 0) < 1
    await callback.message.edit_text("❌ Отменено.")
    await callback.message.answer("Выбери опцию:", reply_markup=main_menu(pro, trial_available))
    await callback.answer()


@router.callback_query(F.data.regexp(r"^(\w+)_page:(\d+)$"))
async def pagination_callback(callback: types.CallbackQuery):
    m = re.match(r"^(\w+)_page:(\d+)$", callback.data)
    if not m:
        await callback.answer()
        return
    prefix = m.group(1)
    page = int(m.group(2))
    if prefix not in PAGE_PREFIXES:
        await callback.answer()
        return
    pro = await is_pro(callback.from_user.id)
    use_pro = pro or prefix in ("futures",)
    await callback.message.edit_text(
        "Выбери монету:",
        reply_markup=coin_selection(prefix, page=page, pro=use_pro),
    )
    await callback.answer()
