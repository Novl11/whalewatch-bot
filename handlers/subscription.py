from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import PRO_PRICE_USDT, PRO_DURATION_DAYS, ADMIN_ID, USDT_WALLET
from database import is_pro, activate_pro, cancel_pro, get_user, create_pending_payment
from services.prices import fetch_fiat_rates, format_fiat

router = Router()


@router.message(Command("pro"))
async def cmd_pro(message: types.Message):
    uid = message.from_user.id
    user = await get_user(uid)
    pro_active = user and user["plan"] == "pro"
    if pro_active:
        exp = user.get("expires_at", "N/A")
        text = (
            "⭐ *У тебя Pro!*\n\n"
            f"Действует до: {exp}\n\n"
            "Доступно:\n"
            "✅ Все 50+ монет\n"
            "✅ Все 18 индикаторов\n"
            "✅ Безлимитные фьючерсы (funding, OI, L/S)\n"
            "✅ Безлимитные список и оповещения"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="❌ Отменить подписку", callback_data="pro_cancel"))
        await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    else:
        rates = await fetch_fiat_rates()
        fiat_str = format_fiat(PRO_PRICE_USDT, rates)
        text = (
            "⭐ *WhaleWatch Pro*\n\n"
            f"Цена: *{PRO_PRICE_USDT} USDT* ({fiat_str})\n"
            f"Срок: {PRO_DURATION_DAYS} дней\n\n"
            "*Бесплатный тариф:*\n"
            "• Все 50+ монет\n"
            "• RSI + EMA 21 индикаторы\n"
            "• 1 пробный фьючерс\n"
            "• 3 слота в списке, 2 оповещения\n"
            "• Только 15m таймфрейм\n\n"
            "*Pro открывает:*\n"
            "✅ Все 50+ монет\n"
            "✅ Все 18 индикаторов\n"
            "✅ Безлимитные фьючерсы: funding, OI, L/S\n"
            "✅ Безлимитные список и оповещения\n"
            "✅ Все таймфреймы 1m–4h\n\n"
            "💳 *Оплата:* USDT (TRC20)\n"
        )
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(
            text=f"💳 Купить Pro — {PRO_PRICE_USDT} USDT",
            callback_data="pro_buy",
        ))
        await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data == "pro_info")
async def pro_info_callback(callback: types.CallbackQuery):
    await cmd_pro(callback.message)
    await callback.answer()


@router.callback_query(F.data == "pro_buy")
async def pro_buy_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if await is_pro(uid):
        await callback.answer("У тебя уже есть Pro! ⭐", show_alert=True)
        return

    rates = await fetch_fiat_rates()
    fiat_str = format_fiat(PRO_PRICE_USDT, rates)

    payment_id = await create_pending_payment(uid, PRO_PRICE_USDT)

    text = (
        "💳 *Оплата Pro подписки*\n\n"
        "Отправь **ровно** указанную сумму USDT в сети **TRC20**:\n\n"
        f"💰 *Сумма:* {PRO_PRICE_USDT} USDT ({fiat_str})\n"
        f"📍 *Адрес:* `{USDT_WALLET}`\n"
        f"⛓ *Сеть:* TRC20 (Tron)\n\n"
        f"🆔 *Код платежа:* `{payment_id}`\n\n"
        "После отправки бот проверит транзакцию в течение 1-2 минут.\n"
        "Pro активируется автоматически ✅\n\n"
        "⏳ Платёж действителен 30 минут."
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="✅ Я отправил, проверить",
        callback_data=f"pro_check:{payment_id}",
    ))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="pro_cancel_pay"))

    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("pro_check:"))
async def pro_check_callback(callback: types.CallbackQuery):
    uid = callback.from_user.id
    payment_id = int(callback.data.split(":")[1])
    if await is_pro(uid):
        await callback.message.edit_text(
            "🎉 *Pro активирован!*\n\n"
            "Всё в порядке, спасибо за покупку.\n"
            "Используй /start для меню.",
            parse_mode="Markdown",
        )
        await callback.answer()
        return
    await callback.answer(
        "⏳ Платёж ещё не обнаружен.\n"
        "Убедись, что отправил ровно 10 USDT в сети TRC20.\n"
        "Проверка происходит каждые 30 секунд — подожди ещё немного.",
        show_alert=True,
    )


@router.callback_query(F.data == "pro_cancel_pay")
async def pro_cancel_pay_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Платёж отменён.")
    await callback.answer()


@router.callback_query(F.data == "pro_cancel")
async def pro_cancel_callback(callback: types.CallbackQuery):
    await cancel_pro(callback.from_user.id)
    await callback.message.edit_text("❌ Подписка Pro отменена. Ты на бесплатном тарифе.")
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message):
    if not await is_pro(message.from_user.id):
        await message.answer("Ты на бесплатном тарифе. Отменять нечего.")
        return
    await cancel_pro(message.from_user.id)
    await message.answer("❌ Подписка Pro отменена. Ты на бесплатном тарифе.")
