import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import is_pro, use_trial_futures, get_user
from services.futures_analysis import analyze_futures
from utils.coins import COIN_WHITELIST, display_coin
from utils.formatting import format_price, format_change, format_volume, format_funding_rate
from utils.keyboards import coin_selection
from utils.footer import add_footer, add_footer_to_builder

router = Router()


def _not_pro(msg: str) -> str:
    return f"❌ *Только для Pro*\n\n{msg}\n\nКупи /pro чтобы продолжить пользоваться фьючерсами."


async def _trial_ok(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    return user and user.get("trial_futures_used", 0) < 1


@router.message(Command("futures"))
async def cmd_futures(message: types.Message):
    pro = await is_pro(message.from_user.id)
    if not pro:
        if not await _trial_ok(message.from_user.id):
            await message.answer(
                _not_pro("Фьючерсный анализ включает funding rate, Open Interest, L/S ratio топ-трейдеров, "
                         "технические индикаторы и торговый вердикт.")
            )
            return
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            coin = args[1].upper()
            await show_futures(message, coin, trial=True)
        else:
            await message.answer("Выбери монету:", reply_markup=coin_selection("futures", pro=False))
    else:
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            coin = args[1].upper()
            await show_futures(message, coin)
        else:
            await message.answer("Выбери монету:", reply_markup=coin_selection("futures", pro=True))


@router.callback_query(F.data == "futures")
async def futures_menu_callback(callback: types.CallbackQuery):
    pro = await is_pro(callback.from_user.id)
    if not pro:
        if not await _trial_ok(callback.from_user.id):
            await callback.message.edit_text(
                _not_pro("Фьючерсы: funding, OI, L/S топ-трейдеров, тех. анализ и вердикт LONG/SHORT.")
            )
            await callback.answer()
            return
        await callback.message.edit_text("Выбери монету:", reply_markup=coin_selection("futures", pro=False))
        await callback.answer()
    else:
        await callback.message.edit_text("Выбери монету:", reply_markup=coin_selection("futures", pro=True))
        await callback.answer()


@router.callback_query(F.data.startswith("futures:"))
async def futures_callback(callback: types.CallbackQuery):
    coin = callback.data.split(":")[1]
    pro = await is_pro(callback.from_user.id)
    if not pro:
        if not await _trial_ok(callback.from_user.id):
            await callback.message.edit_text(_not_pro("Фьючерсы доступны только с подпиской Pro."))
            await callback.answer()
            return
        await show_futures(callback.message, coin, trial=True)
        await callback.answer()
    else:
        await show_futures(callback.message, coin)
        await callback.answer()


async def show_futures(msg: types.Message, coin: str, trial: bool = False):
    coin = coin.upper()
    if coin not in COIN_WHITELIST:
        await msg.answer(f"❌ Неизвестная монета: {coin}")
        return

    sent = await msg.answer(f"🔍 Загружаю фьючерсы {display_coin(coin)}...")

    if trial:
        await use_trial_futures(msg.chat.id)

    a = await analyze_futures(coin)
    price = a["price"]
    change = a["change_24h"]

    text = (
        f"🐋 *{display_coin(coin)} / USDT — Фьючерсы*\n"
        f"💰 *Mark:* {format_price(price)} ({format_change(change)})\n"
        f"📊 *Тренд:* {a['trend_label']}\n\n"
    )

    text += "*📊 Рыночные метрики:*\n"
    text += f"📈 24h High: {format_price(a['high_24h'])}  |  📉 Low: {format_price(a['low_24h'])}\n"
    text += f"📦 Объём 24ч: {format_volume(a['volume_24h'])}\n"
    text += f"🔁 Сделок: {a['trades_24h']:,}\n"
    if a["oi"] is not None:
        text += f"📊 Open Interest: {a['oi']:,.0f} {coin}\n"
    if a["oi_change_pct"] is not None:
        em = "🟢" if a["oi_change_pct"] > 0 else "🔴"
        text += f"{em} OI изм. за 24ч: {a['oi_change_pct']:+.2f}%\n"
    text += "\n"

    text += "*💸 Funding Rate:*\n"
    text += f"{format_funding_rate(a['funding_rate'])} текущий\n"
    text += f"{a['funding_trend']} Средний за 8ч: {a['avg_funding_8h'] * 100:.4f}%\n"
    text += "\n"

    text += "*⚖️ Long / Short:*\n"
    if a["ls_ratio"] is not None:
        ls_pct_long = a["ls_ratio"] / (1 + a["ls_ratio"]) * 100
        ls_pct_short = 100 - ls_pct_long
        text += f"👥 Все трейдеры: 📈 {ls_pct_long:.1f}% / 📉 {ls_pct_short:.1f}% (ratio: {a['ls_ratio']:.2f})\n"
    if a["top_trader_ls"] is not None:
        tt_long = a["top_trader_ls"] / (1 + a["top_trader_ls"]) * 100
        tt_short = 100 - tt_long
        text += f"🐳 Топ трейдеры: 📈 {tt_long:.1f}% / 📉 {tt_short:.1f}% (ratio: {a['top_trader_ls']:.2f})\n"
    if a["taker_buy_ratio"] is not None:
        text += f"💰 Taker buy/sell: {a['taker_buy_ratio'] * 100:.0f}% buy\n"
    text += "\n"

    text += "*📐 Технический анализ (15m):*\n"
    for t in a["technical"]:
        text += f"{t}\n"
    text += "\n"

    text += "*📡 Сигналы:*\n"
    for s in a["signals"]:
        text += f"{s}\n"
    for o in a["oi_analysis"]:
        text += f"{o}\n"
    text += "\n"

    text += f"*🎯 Вердикт: {a['verdict']}*\n\n"
    if a["reasons_for"]:
        text += "*За:*\n"
        for r in a["reasons_for"]:
            text += f"✅ {r}\n"
        text += "\n"
    if a["reasons_against"]:
        text += "*Против:*\n"
        for r in a["reasons_against"]:
            text += f"❌ {r}\n"

    if trial:
        text += "\n🔥 *Пробный доступ использован!*\nКупи /pro для безлимитных фьючерсов."

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu"))
    add_footer_to_builder(builder)
    if len(text) > 4000:
        text = text[:3997] + "..."

    await sent.edit_text(add_footer(text), parse_mode="Markdown", reply_markup=builder.as_markup())
