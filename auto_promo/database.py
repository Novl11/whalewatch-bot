import aiosqlite
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).parent / "promo.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS target_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                title TEXT,
                username TEXT,
                members INTEGER DEFAULT 0,
                lang TEXT DEFAULT 'unknown',
                status TEXT DEFAULT 'found',
                joined_at DATETIME,
                last_seen DATETIME,
                messages_analyzed INTEGER DEFAULT 0,
                answers_sent INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS monitored_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                user_id INTEGER,
                username TEXT,
                text TEXT,
                lang TEXT DEFAULT 'unknown',
                replied INTEGER DEFAULT 0,
                relevance_score REAL DEFAULT 0,
                created_at DATETIME,
                UNIQUE(chat_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                message_id INTEGER,
                reply_text TEXT,
                llm_model TEXT,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                error TEXT,
                created_at DATETIME,
                FOREIGN KEY(chat_id, message_id) REFERENCES monitored_messages(chat_id, message_id)
            );

            CREATE TABLE IF NOT EXISTS daily_limits (
                date TEXT PRIMARY KEY,
                joins INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                llm_calls INTEGER DEFAULT 0
            );
        """)
        await db.commit()


# ── Groups ──────────────────────────────────────────


async def save_group(chat_id: int, title: str, username: str | None, members: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO target_groups (chat_id, title, username, members, status, joined_at, last_seen)
               VALUES (?, ?, ?, ?, 'found', ?, ?)
               ON CONFLICT(chat_id) DO UPDATE SET last_seen = excluded.last_seen""",
            (chat_id, title, username, members, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_groups_by_status(status: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM target_groups WHERE status = ? ORDER BY members DESC", (status,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def update_group_status(chat_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE target_groups SET status = ?, joined_at = COALESCE(joined_at, ?), last_seen = ? WHERE chat_id = ?",
            (status, datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), chat_id),
        )
        await db.commit()


async def get_group_chat_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT chat_id FROM target_groups WHERE status = 'joined'")
        rows = await cur.fetchall()
        return [r[0] for r in rows]


# ── Messages ────────────────────────────────────────


async def save_message(chat_id: int, message_id: int, user_id: int, username: str | None, text: str, lang: str = "unknown"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO monitored_messages (chat_id, message_id, user_id, username, text, lang, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, message_id, user_id, username, text, lang, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_unreplied_messages(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM monitored_messages WHERE replied = 0 ORDER BY relevance_score DESC, created_at ASC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def mark_replied(msg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monitored_messages SET replied = 1 WHERE id = ?", (msg_id,))
        await db.commit()


async def set_relevance(msg_id: int, score: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE monitored_messages SET relevance_score = ? WHERE id = ?", (score, msg_id))
        await db.commit()


# ── Replies ─────────────────────────────────────────


async def save_reply(chat_id: int, message_id: int, reply_text: str, model: str, prompt_tokens: int = 0, completion_tokens: int = 0, success: bool = True, error: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO replies (chat_id, message_id, reply_text, llm_model, prompt_tokens, completion_tokens, success, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (chat_id, message_id, reply_text, model, prompt_tokens, completion_tokens, int(success), error, datetime.utcnow().isoformat()),
        )
        await db.commit()


# ── Limits ──────────────────────────────────────────


async def get_daily_limits() -> dict:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM daily_limits WHERE date = ?", (today,))
        row = await cur.fetchone()
        if row:
            return dict(row)
        return {"date": today, "joins": 0, "replies": 0, "llm_calls": 0}


async def increment_daily_counter(field: str):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"INSERT INTO daily_limits (date, {field}) VALUES (?, 1) ON CONFLICT(date) DO UPDATE SET {field} = {field} + 1",
            (today,),
        )
        await db.commit()


async def get_group_reply_count_today(chat_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM replies WHERE chat_id = ? AND date(created_at) = ? AND success = 1",
            (chat_id, today),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_group_last_reply_time(chat_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT MAX(created_at) FROM replies WHERE chat_id = ? AND success = 1",
            (chat_id,),
        )
        row = await cur.fetchone()
        return row[0] if row and row[0] else None
