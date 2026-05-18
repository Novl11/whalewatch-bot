import asyncio
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "bot.db"
REMINDER_INTERVAL = 3 * 24 * 3600  # 3 days


async def daily_reminder(bot):
    await asyncio.sleep(7200)
    while True:
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                cur = await db.execute(
                    "SELECT u.telegram_id FROM users u "
                    "LEFT JOIN alerts a ON a.user_id = u.id "
                    "LEFT JOIN watchlist w ON w.user_id = u.id "
                    "WHERE u.plan = 'free' AND (a.id IS NOT NULL OR w.id IS NOT NULL) "
                    "GROUP BY u.id"
                )
                rows = await cur.fetchall()

            for row in rows:
                uid = row["telegram_id"]
                try:
                    await bot.send_message(
                        uid,
                        "🐋 *WhaleWatch Bot*\n\n"
                        "Пользуешься ботом? Пора попробовать Pro!\n\n"
                        "⭐ *Преимущества Pro:*\n"
                        "• Все 18 индикаторов (RSI, MACD, BB, ATR и другие)\n"
                        "• Все таймфреймы (1m, 5m, 1h, 4h)\n"
                        "• Безлимитные фьючерсы + вердикт LONG/SHORT\n"
                        "• Безлимитные оповещения и вотчлист\n\n"
                        "💰 *10 USDT* (TRC20) на 30 дней\n\n"
                        "👥 *Или бесплатно:* пригласи 5 друзей → /referral",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass
                await asyncio.sleep(0.3)

        except Exception:
            pass
        await asyncio.sleep(REMINDER_INTERVAL)
