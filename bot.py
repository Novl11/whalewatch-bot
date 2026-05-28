import asyncio
import logging

from aiogram import Bot, Dispatcher
from config import TELEGRAM_TOKEN, ADMIN_ID, PRO_DURATION_DAYS, PRO_PRICE_USDT
from database import init_db, get_pending_payments, confirm_payment, activate_pro, get_confirmed_txids
from services.tron import check_incoming_usdt
from services.alert_checker import check_alerts
from services.channel_poster import channel_poster
from services.reminder import daily_reminder
logger = logging.getLogger(__name__)
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


async def on_startup():
    await init_db()
    asyncio.create_task(payment_checker())
    asyncio.create_task(alert_checker_loop())
    asyncio.create_task(channel_poster(bot))
    asyncio.create_task(daily_reminder(bot))
    print("Bot started. All services running.")
