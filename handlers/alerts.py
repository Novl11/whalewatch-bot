from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import is_pro, get_user
from utils.limits import FREE_MAX_ALERTS, PRO_MAX_ALERTS
from utils.coins import display_coin
from utils.keyboards import coin_selection
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "bot.db"

router = Router()

ALERT_TYPES = {
    "price_above": "Цена выше",
    "price_below": "Цена ниже",
}


async def _get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


@router.message(Command("alerts"))
async def cmd_alerts(message: types.Message):
    await show_alerts(message)


async def show_alerts(msg: types.Message):
    uid = msg.chat.id
    user = await get_user(uid)
    if not user:
        await msg.answer("Сначала используй /start")
        return

    db = await _get_db()
    cur = await db.execute("SELECT * FROM alerts WHERE user_id = ? AND active = 1 ORDER BY created_at DESC", (user["id"],))
    rows = await cur.fetchall()
    await db.close()

    if not rows:
        text = "🔔 *Нет активных оповещений*\n\nИспользуй /alert чтобы создать ценовое оповещение."
    else:
        lines = ["🔔 *Твои оповещения:*\n"]
        for r in rows:
            atype = ALERT_TYPES.get(r["alert_type"], r["alert_type"])
            lines.append(f"• *{display_coin(r['coin'])}*: {atype} ${r['value']:,.2f}")
        text = "\n".join(lines)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Новое", callback_data="alert_new"))
    if rows:
        builder.row(InlineKeyboardButton(text="❌ Удалить", callback_data="alert_delete_list"))
    builder.row(InlineKeyboardButton(text="🔄 Обновить", callback_data="alerts_list"))

    await msg.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data == "alerts_list")
async def alerts_list_callback(callback: types.CallbackQuery):
    await show_alerts(callback.message)
    await callback.answer()


@router.message(Command("alert"))
async def cmd_alert(message: types.Message):
    uid = message.from_user.id
    pro = await is_pro(uid)
    user = await get_user(uid)
    if not user:
        await message.answer("Сначала используй /start")
        return

    db = await _get_db()
    cur = await db.execute("SELECT COUNT(*) as cnt FROM alerts WHERE user_id = ? AND active = 1", (user["id"],))
    count = (await cur.fetchone())["cnt"]
    await db.close()

    limit = PRO_MAX_ALERTS if pro else FREE_MAX_ALERTS
    if count >= limit:
        await message.answer(f"❌ Лимит оповещений ({limit}). Удали старые или купи Pro.")
        return

    await message.answer(
        "Выбери монету для оповещения:",
        reply_markup=coin_selection("alert_coin", pro=pro),
    )


@router.callback_query(F.data.startswith("alert_coin:"))
async def alert_coin_callback(callback: types.CallbackQuery):
    coin = callback.data.split(":")[1]
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Цена выше", callback_data=f"alert_type:price_above:{coin}"),
        InlineKeyboardButton(text="📉 Цена ниже", callback_data=f"alert_type:price_below:{coin}"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="alert_new"))
    await callback.message.edit_text(f"Выбери тип оповещения для *{display_coin(coin)}*:", parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("alert_type:"))
async def alert_type_callback(callback: types.CallbackQuery):
    _, atype, coin = callback.data.split(":")
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используй /start")
        return

    db = await _get_db()
    await db.execute(
        "INSERT INTO alerts (user_id, coin, alert_type, value) VALUES (?, ?, ?, 0)",
        (user["id"], coin, atype),
    )
    await db.commit()
    await db.close()

    await callback.message.edit_text(
        f"✅ Оповещение создано для *{display_coin(coin)}* ({ALERT_TYPES.get(atype, atype)}).\n\n"
        f"Ценовые оповещения будут проверяться периодически.\n\n"
        f"Используй /alerts чтобы управлять оповещениями.",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "alert_delete_list")
async def alert_delete_list_callback(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала используй /start")
        return

    db = await _get_db()
    cur = await db.execute("SELECT * FROM alerts WHERE user_id = ? AND active = 1", (user["id"],))
    rows = await cur.fetchall()
    await db.close()

    if not rows:
        await callback.answer("Нет оповещений для удаления", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for r in rows:
        atype = ALERT_TYPES.get(r["alert_type"], r["alert_type"])
        label = f"❌ {display_coin(r['coin'])} — {atype}"
        builder.row(InlineKeyboardButton(text=label, callback_data=f"alert_del:{r['id']}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="alerts_list"))

    await callback.message.edit_text("Выбери оповещение для удаления:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("alert_del:"))
async def alert_delete_callback(callback: types.CallbackQuery):
    alert_id = int(callback.data.split(":")[1])
    db = await _get_db()
    await db.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    await db.commit()
    await db.close()
    await callback.answer("✅ Оповещение удалено")
    await show_alerts(callback.message)


@router.callback_query(F.data == "alert_new")
async def alert_new_callback(callback: types.CallbackQuery):
    await cmd_alert(callback.message)
    await callback.answer()
