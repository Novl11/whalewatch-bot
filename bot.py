import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from config import TELEGRAM_TOKEN, ADMIN_ID, PRO_DURATION_DAYS, PRO_PRICE_USDT
from database import init_db, get_pending_payments, confirm_payment, activate_pro, get_confirmed_txids
from services.tron import check_incoming_usdt
from services.alert_checker import check_alerts
from services.channel_poster import channel_poster
from services.reminder import daily_reminder
from services.signals import scan_signals

logger = logging.getLogger(__name__)
SCAN_INTERVAL = int(os.getenv("SCAN_INTERVAL", "30"))
from handlers.start import router as start_router
from handlers.price import router as price_router
from handlers.futures import router as futures_router
from handlers.watchlist import router as watchlist_router
from handlers.alerts import router as alerts_router
from handlers.subscription import router as subscription_router
from handlers.admin import router as admin_router
from handlers.help import router as help_router
from handlers.referral import router as referral_router
from handlers.callbacks import router as callbacks_router
from handlers.top import router as top_router
from handlers.fng import router as fng_router
from handlers.market import router as market_router
from handlers.autoreply import router as autoreply_router
from handlers.inline import router as inline_router
from handlers.signals import router as signals_router

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

dp.include_routers(
    start_router,
    price_router,
    futures_router,
    watchlist_router,
    alerts_router,
    subscription_router,
    admin_router,
    help_router,
    referral_router,
    callbacks_router,
    top_router,
    fng_router,
    market_router,
    autoreply_router,
    inline_router,
    signals_router,
)


async def payment_checker():
    await asyncio.sleep(15)
    while True:
        try:
            txs = await check_incoming_usdt(PRO_PRICE_USDT - 1, PRO_PRICE_USDT + 1)
            pending = await get_pending_payments("pending")
            confirmed_ids = await get_confirmed_txids()

            for tx in txs:
                tx_id = tx["tx_id"]
                if tx_id in confirmed_ids:
                    continue
                for pay in pending:
                    await confirm_payment(pay["id"], tx_id)
                    await activate_pro(pay["telegram_id"], PRO_DURATION_DAYS, tx_id, pay["amount_usdt"])
                    try:
                        await bot.send_message(
                            pay["telegram_id"],
                            "🎉 *Оплата получена!*\n\n"
                            f"✅ Pro активирован на {PRO_DURATION_DAYS} дней.\n"
                            "Спасибо за покупку! Используй /start для меню.",
                            parse_mode="Markdown",
                        )
                    except Exception:
                        pass
                    if ADMIN_ID:
                        try:
                            await bot.send_message(
                                ADMIN_ID,
                                f"💰 *Новая Pro подписка (USDT)*\n"
                                f"Пользователь ID: {pay['telegram_id']}\n"
                                f"Сумма: {pay['amount_usdt']} USDT\n"
                                f"TX: {tx_id}",
                                parse_mode="Markdown",
                            )
                        except Exception:
                            pass
                    break
        except Exception:
            pass
        await asyncio.sleep(30)


async def alert_checker_loop():
    await asyncio.sleep(20)
    while True:
        try:
            await check_alerts(bot)
        except Exception:
            pass
        await asyncio.sleep(30)


def _fmt_signals(result: dict) -> str:
    lines = ["📊 *Авто-скан сигналов*\n"]
    lines.append("🟢 *LONG*")
    for s in result.get("long", []):
        r = ", ".join(s["reasons"])
        f = f"funding {s['funding']:+.3f}%" if s["funding"] is not None else ""
        lines.append(f"• *{s['coin']}* ${s['price']:,.2f} | RSI {s['rsi']:.0f} | {f} | {r}")
    if not result.get("long"):
        lines.append("_Нет_")
    lines.append("")
    lines.append("🔴 *SHORT*")
    for s in result.get("short", []):
        r = ", ".join(s["reasons"])
        f = f"funding {s['funding']:+.3f}%" if s["funding"] is not None else ""
        lines.append(f"• *{s['coin']}* ${s['price']:,.2f} | RSI {s['rsi']:.0f} | {f} | {r}")
    if not result.get("short"):
        lines.append("_Нет_")
    lines.append("")
    lines.append(f"⏱ Каждые {SCAN_INTERVAL} мин · /signals ручной запрос")
    return "\n".join(lines)


async def signal_scanner():
    """Background: scan every N min, send signals to admin."""
    await asyncio.sleep(30)
    logger.info("Signal scanner started, interval=%d min", SCAN_INTERVAL)
    while True:
        try:
            result = await scan_signals()
            text = _fmt_signals(result)
            await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logger.error("Signal scan error: %s", e)
        await asyncio.sleep(SCAN_INTERVAL * 60)


async def on_startup():
    await init_db()
    asyncio.create_task(payment_checker())
    asyncio.create_task(alert_checker_loop())
    asyncio.create_task(channel_poster(bot))
    asyncio.create_task(daily_reminder(bot))
    if ADMIN_ID:
        asyncio.create_task(signal_scanner())
    print("Bot started. All services running.")
