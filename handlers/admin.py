import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID, PRO_DURATION_DAYS
from database import activate_pro, cancel_pro, get_user
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "bot.db"

router = Router()


def _is_admin(uid: int) -> bool:
    return ADMIN_ID > 0 and uid == ADMIN_ID


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not _is_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT COUNT(*) as cnt FROM users")
        total = (await cur.fetchone())["cnt"]
        cur = await db.execute("SELECT COUNT(*) as cnt FROM users WHERE plan = 'pro'")
        pro = (await cur.fetchone())["cnt"]
        cur = await db.execute("SELECT COUNT(*) as cnt FROM alerts")
        alerts = (await cur.fetchone())["cnt"]
        cur = await db.execute("SELECT COUNT(*) as cnt FROM pending_payments WHERE status = 'pending'")
        pending_pays = (await cur.fetchone())["cnt"]
        cur = await db.execute("SELECT COUNT(*) as cnt FROM pending_payments WHERE status = 'confirmed'")
        confirmed_pays = (await cur.fetchone())["cnt"]

    text = (
        f"👤 *Панель администратора*\n\n"
        f"👥 Всего: {total}  |  ⭐ Pro: {pro}\n"
        f"🔔 Оповещений: {alerts}\n"
        f"⏳ Ожидают оплаты: {pending_pays}  |  ✅ Подтверждено: {confirmed_pays}\n"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="💰 Платежи", callback_data="admin_payments"),
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.message(Command("users"))
async def cmd_users(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    await show_users_page(message, 0)


async def show_users_page(msg: types.Message, page: int, edit: bool = False):
    per_page = 10
    offset = page * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT telegram_id, username, first_name, plan, expires_at, created_at, trial_futures_used "
            "FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        )
        users = await cur.fetchall()
        cur = await db.execute("SELECT COUNT(*) as cnt FROM users")
        total = (await cur.fetchone())["cnt"]

    if not users:
        txt = "👥 Нет пользователей."
        if edit:
            await msg.edit_text(txt)
        else:
            await msg.answer(txt)
        return

    lines = [f"👥 *Пользователи* (стр. {page + 1} / всего {total}):\n"]
    for u in users:
        name = u["username"] or u["first_name"] or f"id{u['telegram_id']}"
        plan = "⭐" if u["plan"] == "pro" else "🆓"
        created = u["created_at"][:10] if u["created_at"] else "?"
        trial = f" 🔥{u['trial_futures_used']}/1" if u["trial_futures_used"] else ""
        lines.append(f"• `{u['telegram_id']}` {name} — {plan} [{created}]{trial}")

    builder = InlineKeyboardBuilder()
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_p:{page - 1}"))
    if offset + per_page < total:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"admin_users_p:{page + 1}"))
    if nav:
        builder.row(*nav)

    for u in users[:6]:
        uid = u["telegram_id"]
        name = u["username"] or u["first_name"] or str(uid)
        short = (name[:10] + "..") if len(name) > 10 else name
        builder.row(InlineKeyboardButton(text=f"👤 {short} (id{uid})", callback_data=f"admin_user:{uid}"))

    builder.row(InlineKeyboardButton(text="🏠 Назад в админку", callback_data="admin"))

    if edit:
        await msg.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=builder.as_markup())
    else:
        await msg.answer("\n".join(lines), parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_users_p:"))
async def admin_users_page_callback(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    page = int(callback.data.split(":")[1])
    await show_users_page(callback.message, page, edit=True)
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: types.CallbackQuery):
    await show_users_page(callback.message, 0, edit=True)
    await callback.answer()


async def _show_user_detail(msg: types.Message, uid: int):
    user = await get_user(uid)
    if not user:
        await msg.edit_text(f"Пользователь `{uid}` не найден.", parse_mode="Markdown")
        return

    name = user["username"] or user["first_name"] or "—"
    plan = "⭐ Pro" if user["plan"] == "pro" else "🆓 Бесплатно"
    exp = f"\nДействует до: {user['expires_at'][:10]}" if user["expires_at"] else ""
    trial = user.get("trial_futures_used", 0)

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) as cnt FROM pending_payments WHERE telegram_id = ?", (uid,))
        pays = (await cur.fetchone())["cnt"]

    text = (
        f"👤 *Информация о пользователе*\n\n"
        f"🆔 `{uid}`\n"
        f"📛 {name}\n"
        f"💰 {plan}{exp}\n"
        f"🔥 Пробных фьючерсов: {trial}/1\n"
        f"💳 Платежей: {pays}\n"
    )

    builder = InlineKeyboardBuilder()
    if user["plan"] != "pro":
        builder.row(InlineKeyboardButton(text="⭐ Выдать Pro", callback_data=f"admin_grant:{uid}"))
    else:
        builder.row(InlineKeyboardButton(text="❌ Отозвать Pro", callback_data=f"admin_revoke:{uid}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="admin_users"))

    await msg.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("admin_user:"))
async def admin_user_detail(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    uid = int(callback.data.split(":")[1])
    await _show_user_detail(callback.message, uid)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_grant:"))
async def admin_grant_callback(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    uid = int(callback.data.split(":")[1])
    user = await get_user(uid)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return
    await activate_pro(uid, PRO_DURATION_DAYS, "admin_grant", 0)
    await callback.answer(f"✅ Pro выдан на {PRO_DURATION_DAYS} дней!", show_alert=True)
    try:
        await callback.bot.send_message(
            uid,
            f"🎉 *Pro активирован администратором!*\n\nДоступ открыт на {PRO_DURATION_DAYS} дней.",
            parse_mode="Markdown",
        )
    except Exception:
        pass
    await _show_user_detail(callback.message, uid)


@router.callback_query(F.data.startswith("admin_revoke:"))
async def admin_revoke_callback(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    uid = int(callback.data.split(":")[1])
    await cancel_pro(uid)
    await callback.answer("❌ Pro отозван!", show_alert=True)
    try:
        await callback.bot.send_message(uid, "❌ Ваш Pro доступ отозван администратором.")
    except Exception:
        pass
    await _show_user_detail(callback.message, uid)


@router.callback_query(F.data == "admin_payments")
async def admin_payments_callback(callback: types.CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT p.*, u.username, u.first_name "
            "FROM pending_payments p "
            "LEFT JOIN users u ON p.user_id = u.id "
            "ORDER BY p.created_at DESC LIMIT 20"
        )
        pays = await cur.fetchall()

    if not pays:
        await callback.message.edit_text("Нет платежей.")
        await callback.answer()
        return

    lines = ["💰 *Платежи:*\n"]
    for p in pays:
        name = p["username"] or p["first_name"] or str(p["telegram_id"])
        em = {"pending": "⏳", "confirmed": "✅", "expired": "❌"}.get(p["status"], "❓")
        tx = (p["tx_id"] or "—")[:20]
        lines.append(f"{em} `{p['telegram_id']}` {name} — {p['amount_usdt']} USDT")
        lines.append(f"   `{tx}` — {p['status']}")

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin"))

    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin")
async def admin_back_callback(callback: types.CallbackQuery):
    await cmd_admin(callback.message)
    await callback.answer()


@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /broadcast <сообщение>")
        return

    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT telegram_id FROM users")
        users = await cur.fetchall()

    sent = 0
    failed = 0
    for u in users:
        try:
            await message.bot.send_message(u[0], args[1], parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await message.answer(f"✅ Рассылка завершена: {sent} успешно, {failed} с ошибками")


@router.message(Command("addpro"))
async def cmd_addpro(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /addpro <telegram_id>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    user = await get_user(uid)
    if not user:
        await message.answer(f"Пользователь {uid} не найден. Сначала он должен написать /start.")
        return
    await activate_pro(uid, PRO_DURATION_DAYS, "admin_grant", 0)
    await message.answer(f"✅ Pro выдан пользователю `{uid}` на {PRO_DURATION_DAYS} дней.", parse_mode="Markdown")
    try:
        await message.bot.send_message(uid, f"🎉 *Pro активирован администратором!*\n\nДоступ открыт на {PRO_DURATION_DAYS} дней.", parse_mode="Markdown")
    except Exception:
        pass


@router.message(Command("rmpro"))
async def cmd_rmpro(message: types.Message):
    if not _is_admin(message.from_user.id):
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /rmpro <telegram_id>")
        return
    try:
        uid = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return
    await cancel_pro(uid)
    await message.answer(f"✅ Pro отозван у пользователя `{uid}`.", parse_mode="Markdown")
    try:
        await message.bot.send_message(uid, "❌ Ваш Pro доступ отозван администратором.")
    except Exception:
        pass
