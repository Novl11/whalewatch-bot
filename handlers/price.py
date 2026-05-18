import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import is_pro, get_or_create_user, get_user
from services.binance import fetch_ticker_24h, fetch_klines, fetch_spot_price, fetch_all_tickers
from services.indicators import build_snapshots
from utils.coins import COIN_WHITELIST, FREE_COINS, display_coin
from utils.limits import FREE_INDICATORS, FREE_INTERVALS
from utils.keyboards import coin_selection, timeframe_selection
from utils.formatting import format_price, format_change, format_volume
from utils.footer import add_footer, add_footer_to_builder

router = Router()


class PriceState(StatesGroup):
    waiting_for_coin = State()


@router.message(Command("price"))
async def cmd_price(message: types.Message, state: FSMContext):
    await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        coin = args[1].upper()
        await show_price(message, coin)
    else:
        pro = await is_pro(message.from_user.id)
        await message.answer(
            "Выбери монету:",
            reply_markup=coin_selection("price", pro=pro),
        )
        await state.set_state(PriceState.waiting_for_coin)


@router.callback_query(F.data == "price")
async def price_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await get_or_create_user(callback.from_user.id, callback.from_user.username, callback.from_user.first_name)
    pro = await is_pro(callback.from_user.id)
    await callback.message.edit_text("Выбери монету:", reply_markup=coin_selection("price", pro=pro))
    await state.set_state(PriceState.waiting_for_coin)
    await callback.answer()


@router.callback_query(F.data.startswith("price:"))
async def price_callback(callback: types.CallbackQuery):
    coin = callback.data.split(":")[1]
    await show_price(callback.message, coin)
    await callback.answer()


async def show_price(msg: types.Message, coin: str):
    coin = coin.upper()
    pro = await is_pro(msg.chat.id)
    if not pro and coin not in FREE_COINS:
        await msg.answer(f"❌ {display_coin(coin)} только для Pro. Купить: /pro")
        return
    if coin not in COIN_WHITELIST:
        await msg.answer(f"❌ Неизвестная монета: {coin}")
        return

    sent = await msg.answer(f"🔍 Загружаю {display_coin(coin)}...")
    ticker = await fetch_ticker_24h(coin)
    if not ticker:
        await sent.edit_text(f"❌ Не удалось получить данные для {display_coin(coin)}")
        return

    price = float(ticker.get("lastPrice", 0))
    change = float(ticker.get("priceChangePercent", 0))
    high = float(ticker.get("highPrice", 0))
    low = float(ticker.get("lowPrice", 0))
    vol = float(ticker.get("quoteVolume", 0))

    text = (
        f"🐋 *{display_coin(coin)} / USDT — Spot*\n"
        f"💰 *Цена:* {format_price(price)}\n"
        f"📊 24ч: {format_change(change)}\n"
        f"📈 Макс: {format_price(high)}\n"
        f"📉 Мин: {format_price(low)}\n"
        f"📦 Объём: {format_volume(vol)}\n"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Индикаторы", callback_data=f"indicators:{coin}"),
    )
    uid = msg.chat.id
    pro = await is_pro(uid)
    if pro:
        builder.add(InlineKeyboardButton(text="🔥 Фьючерсы", callback_data=f"futures:{coin}"))
    else:
        user = await get_user(uid)
        trial_ok = user and user.get("trial_futures_used", 0) < 1
        if trial_ok:
            builder.add(InlineKeyboardButton(text="🔥 Фьючерсы", callback_data=f"futures:{coin}"))
        else:
            builder.add(InlineKeyboardButton(text="🔒 Фьючерсы (Pro)", callback_data="futures_locked"))
    builder.row(
        InlineKeyboardButton(text="👁 В список", callback_data=f"watch_add:{coin}"),
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Меню", callback_data="menu"),
    )

    add_footer_to_builder(builder)
    await sent.edit_text(add_footer(text), parse_mode="Markdown", reply_markup=builder.as_markup())


@router.message(Command("indicators"))
async def cmd_indicators(message: types.Message):
    await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        coin = args[1].upper()
        await show_indicators(message, coin)
    else:
        pro = await is_pro(message.from_user.id)
        await message.answer("Выбери монету:", reply_markup=coin_selection("indicators", pro=pro))


@router.callback_query(F.data == "indicators")
async def indicators_menu_callback(callback: types.CallbackQuery):
    pro = await is_pro(callback.from_user.id)
    await callback.message.edit_text("Выбери монету:", reply_markup=coin_selection("indicators", pro=pro))
    await callback.answer()


TIMEFRAMES = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h"}
TIMEFRAME_LABELS = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1ч", "4h": "4ч"}


@router.callback_query(F.data.regexp(r"^indicators_tf:(\w+):(\w+)$"))
async def indicators_timeframe_callback(callback: types.CallbackQuery):
    import re
    m = re.match(r"^indicators_tf:(\w+):(\w+)$", callback.data)
    if not m:
        await callback.answer()
        return
    coin = m.group(1)
    tf = m.group(2)
    pro = await is_pro(callback.from_user.id)
    if not pro and tf not in FREE_INTERVALS:
        await callback.answer("🔒 Таймфрейм только для Pro. Купи /pro", show_alert=True)
        return
    if tf not in TIMEFRAMES:
        await callback.answer()
        return
    await show_indicators(callback.message, coin, tf)
    await callback.answer()


@router.callback_query(F.data.regexp(r"^indicators:(\w+)$"))
async def indicators_callback_simple(callback: types.CallbackQuery):
    import re
    m = re.match(r"^indicators:(\w+)$", callback.data)
    if not m:
        await callback.answer()
        return
    coin = m.group(1)
    await show_indicators(callback.message, coin)
    await callback.answer()


async def show_indicators(msg: types.Message, coin: str, timeframe: str = "15m"):
    coin = coin.upper()
    pro = await is_pro(msg.chat.id)
    if not pro and coin not in FREE_COINS:
        await msg.answer(f"❌ {display_coin(coin)} только для Pro. Купить: /pro")
        return
    if coin not in COIN_WHITELIST:
        await msg.answer(f"❌ Неизвестная монета: {coin}")
        return

    limit = 500 if timeframe in ("1h", "4h") else 250
    sent = await msg.answer(f"🔍 Загружаю индикаторы для {display_coin(coin)} ({TIMEFRAME_LABELS.get(timeframe, timeframe)})...")
    candles = await fetch_klines(coin, timeframe, limit)
    if not candles:
        await sent.edit_text(f"❌ Не удалось загрузить данные для {display_coin(coin)}")
        return

    allowed = None if pro else FREE_INDICATORS
    snaps = build_snapshots(candles, pro=pro, allowed=allowed)

    if not snaps:
        await sent.edit_text("❌ Недостаточно данных для индикаторов")
        return

    tf_label = TIMEFRAME_LABELS.get(timeframe, timeframe)
    lines = [f"🐋 *{display_coin(coin)} — Индикаторы ({tf_label})*\n"]
    signal_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
    for s in snaps:
        emoji = signal_emoji.get(s["signal"], "⚪")
        detail = f" — _{s['detail']}_" if s.get("detail") else ""
        lines.append(f"{emoji} *{s['label']}:* `{s['value']}`{detail}")

    builder = InlineKeyboardBuilder()
    if pro:
        builder.row(
            InlineKeyboardButton(text="🔄 Таймфрейм", callback_data=f"indicators_tf_menu:{coin}"),
        )
    if not pro:
        lines.append("\n_➕ 16 индикаторов заблокировано. Купи Pro чтобы открыть все._")
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu"))
    add_footer_to_builder(builder)
    await sent.edit_text(add_footer("\n".join(lines)), parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data.regexp(r"^indicators_tf_menu:(\w+)$"))
async def indicators_tf_menu_callback(callback: types.CallbackQuery):
    import re
    m = re.match(r"^indicators_tf_menu:(\w+)$", callback.data)
    if not m:
        await callback.answer()
        return
    coin = m.group(1)
    pro = await is_pro(callback.from_user.id)
    if not pro:
        await callback.answer("🔒 Только для Pro", show_alert=True)
        return
    from utils.keyboards import timeframe_selection
    await callback.message.edit_text(
        f"Выбери таймфрейм для *{display_coin(coin)}*:",
        parse_mode="Markdown",
        reply_markup=timeframe_selection(coin),
    )
    await callback.answer()
