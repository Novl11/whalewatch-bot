import asyncio, logging, random
from datetime import datetime, timedelta

from telethon import TelegramClient, errors as tel_errors

from auto_promo.config import REPLY_DELAY_MIN, REPLY_DELAY_MAX, \
    MAX_REPLIES_PER_DAY, MAX_REPLIES_PER_GROUP_PER_DAY, GROUP_COOLDOWN_HOURS
from auto_promo.database import mark_replied, save_reply, \
    get_daily_limits, increment_daily_counter, get_group_reply_count_today, get_group_last_reply_time

log = logging.getLogger("promo.sender")


def _is_group_on_cooldown(last_reply_time: str | None) -> bool:
    """Проверяем, не отвечали ли в эту группу слишком недавно."""
    if not last_reply_time:
        return False
    last = datetime.fromisoformat(last_reply_time)
    cooldown = timedelta(hours=GROUP_COOLDOWN_HOURS)
    return datetime.utcnow() - last < cooldown


async def send_reply(client: TelegramClient, msg_id: int, chat_id: int, reply_text: str, model: str, prompt_tokens: int = 0, completion_tokens: int = 0):
    """Фаза 3: отправка ответа с проверкой лимитов."""
    # Лимиты
    limits = await get_daily_limits()
    if limits["replies"] >= MAX_REPLIES_PER_DAY:
        log.info("Daily reply limit reached")
        return False

    group_today = await get_group_reply_count_today(chat_id)
    if group_today >= MAX_REPLIES_PER_GROUP_PER_DAY:
        log.info(f"Group {chat_id} daily reply limit reached")
        await _log_skip(chat_id, msg_id, "group_daily_limit")
        return False

    last_reply = await get_group_last_reply_time(chat_id)
    if _is_group_on_cooldown(last_reply):
        log.info(f"Group {chat_id} is on cooldown")
        await _log_skip(chat_id, msg_id, "cooldown")
        return False

    # Рандомная задержка перед ответом
    delay = random.uniform(REPLY_DELAY_MIN, REPLY_DELAY_MAX)
    log.info(f"  Waiting {delay:.0f}s before reply in chat {chat_id}...")
    await asyncio.sleep(delay)

    # Отправка
    try:
        await client.send_message(chat_id, reply_text, reply_to=msg_id)
        log.info(f"  ✅ Reply sent to chat {chat_id}, msg {msg_id}")

        await save_reply(chat_id, msg_id, reply_text, model, prompt_tokens, completion_tokens, success=True)
        await mark_replied(msg_id)
        await increment_daily_counter("replies")

        # Обновляем счётчик ответов в группе
        from auto_promo.database import DB_PATH
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE target_groups SET answers_sent = answers_sent + 1 WHERE chat_id = ?",
                (chat_id,),
            )
            await db.commit()

        return True

    except tel_errors.FloodWaitError as e:
        log.warning(f"  FloodWait: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 5)
        await _log_fail(chat_id, msg_id, reply_text, model, f"FloodWait:{e.seconds}s")
        return False
    except Exception as e:
        log.warning(f"  Send error: {e}")
        await _log_fail(chat_id, msg_id, reply_text, model, str(e))
        return False


async def _log_skip(chat_id: int, msg_id: int, reason: str):
    await save_reply(chat_id, msg_id, f"SKIPPED:{reason}", "none", success=False, error=reason)


async def _log_fail(chat_id: int, msg_id: int, reply_text: str, model: str, error: str):
    await save_reply(chat_id, msg_id, reply_text, model, success=False, error=error)
