import aiosqlite
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot.db"


def get_now():
    return datetime.datetime.utcnow()


# ── pending payments ──────────────────────────────


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                plan TEXT DEFAULT 'free',
                expires_at DATETIME,
                trial_futures_used INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, coin)
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                value REAL,
                active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan TEXT NOT NULL,
                telegram_payment_charge_id TEXT,
                amount INTEGER,
                start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_date DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS pending_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                amount_usdt REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                tx_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                confirmed_at DATETIME
            );
        """)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN trial_futures_used INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER DEFAULT NULL")
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            pass
        await db.commit()


async def get_or_create_user(telegram_id: int, username: str | None = None, first_name: str | None = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await cur.fetchone()
        if user:
            if username or first_name:
                await db.execute(
                    "UPDATE users SET username = COALESCE(?, username), first_name = COALESCE(?, first_name) WHERE telegram_id = ?",
                    (username, first_name, telegram_id),
                )
                await db.commit()
            return dict(user)
        await db.execute(
            "INSERT INTO users (telegram_id, username, first_name) VALUES (?, ?, ?)",
            (telegram_id, username, first_name),
        )
        await db.commit()
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return dict(await cur.fetchone())


async def get_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def is_pro(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user or user["plan"] != "pro":
        return False
    if user["expires_at"]:
        exp = datetime.datetime.fromisoformat(user["expires_at"])
        if exp < get_now():
            return False
    return True


async def activate_pro(telegram_id: int, days: int, charge_id: str | None = None, amount: int | None = None):
    user = await get_or_create_user(telegram_id)
    now = get_now()
    expires = now + datetime.timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan = 'pro', expires_at = ? WHERE telegram_id = ?",
            (expires.isoformat(), telegram_id),
        )
        await db.execute(
            "INSERT INTO subscriptions (user_id, plan, telegram_payment_charge_id, amount, end_date) VALUES (?, 'pro', ?, ?, ?)",
            (user["id"], charge_id, amount, expires.isoformat()),
        )
        await db.commit()


async def cancel_pro(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan = 'free', expires_at = NULL WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()


async def get_watchlist(telegram_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        user = await get_user(telegram_id)
        if not user:
            return []
        cur = await db.execute("SELECT coin FROM watchlist WHERE user_id = ? ORDER BY created_at", (user["id"],))
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def add_to_watchlist(telegram_id: int, coin: str) -> bool:
    user = await get_or_create_user(telegram_id)
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO watchlist (user_id, coin) VALUES (?, ?)",
                (user["id"], coin.upper()),
            )
            await db.commit()
            return True
    except aiosqlite.IntegrityError:
        return False


async def remove_from_watchlist(telegram_id: int, coin: str):
    user = await get_or_create_user(telegram_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND coin = ?",
            (user["id"], coin.upper()),
        )
        await db.commit()


# ── pending payments ──────────────────────────────


async def create_pending_payment(telegram_id: int, amount_usdt: float) -> int:
    user = await get_or_create_user(telegram_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO pending_payments (user_id, telegram_id, amount_usdt) VALUES (?, ?, ?)",
            (user["id"], telegram_id, amount_usdt),
        )
        await db.commit()
        return cur.lastrowid


async def get_pending_payments(status: str = "pending") -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM pending_payments WHERE status = ? ORDER BY created_at ASC",
            (status,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def confirm_payment(payment_id: int, tx_id: str):
    now = get_now()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET status = 'confirmed', tx_id = ?, confirmed_at = ? WHERE id = ?",
            (tx_id, now.isoformat(), payment_id),
        )
        await db.commit()


async def get_confirmed_txids() -> set[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT tx_id FROM pending_payments WHERE tx_id IS NOT NULL",
        )
        rows = await cur.fetchall()
        return {r[0] for r in rows if r[0]}


async def mark_payment_expired(payment_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_payments SET status = 'expired' WHERE id = ?",
            (payment_id,),
        )
        await db.commit()


# ── trial futures ────────────────────────────────


async def use_trial_futures(telegram_id: int) -> bool:
    user = await get_user(telegram_id)
    if not user:
        return False
    used = user.get("trial_futures_used", 0)
    if used >= 1:
        return False
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET trial_futures_used = trial_futures_used + 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    return True
