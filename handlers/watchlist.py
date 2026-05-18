from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_watchlist, add_to_watchlist, remove_from_watchlist, is_pro
from services.binance import fetch_ticker_24h
from utils.coins import COIN_WHITELIST, FREE_COINS, display_coin
from utils.limits import FREE_MAX_WATCHLIST, PRO_MAX_WATCHLIST
from utils.formatting import format_price, format_change
from utils.keyboards import coin_selection

router = Router()


class WatchState(StatesGroup):
    waiting_for_add = State()


@router.message(Command("watchlist"))
async def cmd_watchlist(message: types.Message, state: FSMContext):
    await state.clear()
    await show_watchlist(message)


async def show_watchlist(msg: types.Message):
    uid = msg.chat.id
    coins = await get_watchlist(uid)
    pro = await is_pro(uid)
    limit = PRO_MAX_WATCHLIST if pro else FREE_MAX_WATCHLIST

    if not coins:
        text = "👁 *Список пуст*\n\nИспользуй /add BTC чтобы добавить монету, или нажми кнопку ниже."
    else:
        lines = ["👁 *Твой список:*\n"]
        for c in coins:
            ticker = await fetch_ticker_24h(c)
            if ticker:
                price = float(ticker.get("lastPrice", 0))
                change = float(ticker.get("priceChangePercent", 0))
                lines.append(f"• *{display_coin(c)}*: {format_price(price)} {format_change(change)}")
            else:
                lines.append(f"• *{display_coin(c)}*: ⏳ ошибка")
        text = "\n".join(lines)
        text += f"\n\n_{len(coins)}/{limit} слотов занято_"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="watchlist_add"))
    if coins:
        builder.row(InlineKeyboardButton(text="➖ Удалить", callback_data="watchlist_remove"))

    await msg.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data == "watchlist")
async def watchlist_callback(callback: types.CallbackQuery):
    await show_watchlist(callback.message)
    await callback.answer()


@router.callback_query(F.data == "watchlist_add")
async def watchlist_add_prompt(callback: types.CallbackQuery):
    pro = await is_pro(callback.from_user.id)
    coins = await get_watchlist(callback.from_user.id)
    limit = PRO_MAX_WATCHLIST if pro else FREE_MAX_WATCHLIST
    if len(coins) >= limit:
        await callback.answer(f"❌ Список полон ({limit} макс). Удали что-нибудь или купи Pro.", show_alert=True)
        return
    await callback.message.edit_text(
        "Выбери монету:",
        reply_markup=coin_selection("watch_add", pro=pro),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("watch_add:"))
async def watch_add_callback(callback: types.CallbackQuery):
    coin = callback.data.split(":")[1]
    ok = await add_to_watchlist(callback.from_user.id, coin)
    if ok:
        await callback.answer(f"✅ {display_coin(coin)} добавлена в список!")
    else:
        await callback.answer(f"⚠️ {display_coin(coin)} уже в списке")
    await show_watchlist(callback.message)


@router.callback_query(F.data == "watchlist_remove")
async def watchlist_remove_prompt(callback: types.CallbackQuery):
    coins = await get_watchlist(callback.from_user.id)
    if not coins:
        await callback.answer("Список пуст", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for c in coins:
        builder.row(InlineKeyboardButton(text=f"❌ {display_coin(c)}", callback_data=f"watch_remove:{c}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="watchlist"))
    await callback.message.edit_text("Выбери монету для удаления:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("watch_remove:"))
async def watch_remove_callback(callback: types.CallbackQuery):
    coin = callback.data.split(":")[1]
    await remove_from_watchlist(callback.from_user.id, coin)
    await callback.answer(f"❌ {display_coin(coin)} удалена")
    await show_watchlist(callback.message)


@router.message(Command("add"))
async def cmd_add(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /add BTC")
        return
    coin = args[1].upper()
    if coin not in COIN_WHITELIST:
        await message.answer(f"❌ Неизвестная монета: {coin}")
        return
    pro = await is_pro(message.from_user.id)
    if not pro and coin not in FREE_COINS:
        await message.answer(f"❌ {display_coin(coin)} только для Pro. /pro")
        return
    coins = await get_watchlist(message.from_user.id)
    limit = PRO_MAX_WATCHLIST if pro else FREE_MAX_WATCHLIST
    if len(coins) >= limit:
        await message.answer(f"❌ Список полон ({limit} макс). Удали что-нибудь или купи Pro.")
        return
    ok = await add_to_watchlist(message.from_user.id, coin)
    if ok:
        await message.answer(f"✅ {display_coin(coin)} добавлена в список!")
    else:
        await message.answer(f"⚠️ {display_coin(coin)} уже в списке")


@router.message(Command("remove"))
async def cmd_remove(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        coins = await get_watchlist(message.from_user.id)
        if not coins:
            await message.answer("Твой список пуст.")
            return
        await message.answer(f"Использование: /remove BTC\n\nТвой список: {', '.join(display_coin(c) for c in coins)}")
        return
    coin = args[1].upper()
    await remove_from_watchlist(message.from_user.id, coin)
    await message.answer(f"✅ {display_coin(coin)} удалена из списка")
