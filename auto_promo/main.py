import asyncio, logging, random, re
from pathlib import Path

from telethon import TelegramClient, events

from auto_promo.config import (
    API_ID, API_HASH, PHONE,
    ACTION_DELAY_MIN, ACTION_DELAY_MAX,
    MONITOR_CHECK_INTERVAL, LLM_PROVIDER, LLM_MODEL,
)
from auto_promo.database import (
    init_db, get_group_chat_ids, save_message, get_unreplied_messages,
    set_relevance, increment_daily_counter, get_daily_limits,
)
from auto_promo.scanner import scan_and_join
from auto_promo.llm import generate_reply
from auto_promo.sender import send_reply

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    handlers=[
        logging.FileHandler("auto_promo.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("promo.main")

RELEVANT_KEYWORDS = [
    "rsi", "macd", "bb", "bollinger", "atr", "stochastic", "adx",
    "индикатор", "анализ", "фьючерс", "funding", "open interest",
    "лонг", "шорт", "вердикт", "цена", "price", "курс",
    "график", "chart", "сигнал", "тренд", "trend",
    "binance", "bybit",
    "помогите", "подскажите", "что думаете", "вопрос",
]
SKIP_PATTERNS = [re.compile(r"https?://\S+")]


def relevance_score(text: str) -> float:
    if not text or len(text) < 10:
        return 0.0
    for pat in SKIP_PATTERNS:
        if pat.search(text):
            return 0.0
    text_lower = text.lower()
    score = sum(0.15 for kw in RELEVANT_KEYWORDS if kw in text_lower)
    if "?" in text or "?" in text:
        score += 0.2
    if any(w in text_lower for w in ["как", "что", "где", "почему", "сколько", "помогите", "подскажите"]):
        score += 0.15
    return min(score, 1.0)


async def setup_listener(client: TelegramClient):
    """Устанавливаем слушатель сообщений в joined-группах."""
    chat_ids = await get_group_chat_ids()
    if not chat_ids:
        return

    @client.on(events.NewMessage(chats=chat_ids))
    async def handler(event):
        msg = event.message
        if not msg or not msg.text or msg.out:
            return

        text = msg.text.strip()
        score = relevance_score(text)
        if score < 0.3:
            return

        log.info(f"  🎯 Relevant in {event.chat_id}: '{text[:80]}...' ({score:.2f})")
        await save_message(
            chat_id=event.chat_id,
            message_id=msg.id,
            user_id=msg.sender_id or 0,
            username=getattr(msg.sender, "username", None) if msg.sender else None,
            text=text,
            lang="ru" if any(ord(c) > 127 for c in text) else "en",
        )

    log.info(f"Listener active for {len(chat_ids)} groups")


async def process_pending(client: TelegramClient):
    """Ответы на накопленные релевантные сообщения."""
    pending = await get_unreplied_messages(limit=5)
    if not pending:
        return

    for msg in pending:
        log.info(f"  Generating reply for msg #{msg['id']}...")

        result = await generate_reply(msg["text"], msg.get("lang", "unknown"))
        await increment_daily_counter("llm_calls")

        await send_reply(
            client=client,
            msg_id=msg["message_id"],
            chat_id=msg["chat_id"],
            reply_text=result["reply"],
            model=result["model"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
        )

        await asyncio.sleep(random.uniform(ACTION_DELAY_MIN, ACTION_DELAY_MAX))


async def main():
    await init_db()

    if not all([API_ID, API_HASH, PHONE]):
        log.error("Missing USERBOT_API_ID/USERBOT_API_HASH/USERBOT_PHONE in .env")
        return

    session_path = str(Path(__file__).parent / "sessions" / "promo_user")
    client = TelegramClient(session_path, API_ID, API_HASH)

    await client.start(phone=PHONE)
    me = await client.get_me()
    log.info(f"✅ Logged in as: {me.first_name}")

    cycles_without_new = 0

    while True:
        try:
            # Phase 1 — сканирование и вступление
            log.info("=== Phase 1: Scan & Join ===")
            before = await get_group_chat_ids()
            await scan_and_join(client)
            after = await get_group_chat_ids()

            if len(after) > len(before):
                # Новые группы — переустанавливаем слушатель
                await setup_listener(client)
                cycles_without_new = 0
            else:
                cycles_without_new += 1

            # Phase 3 — ответы на релевантные сообщения
            log.info("=== Phase 3: Reply ===")
            await process_pending(client)

            # Если N циклов без новых групп — пересканируем с обновлением слушателя
            if cycles_without_new >= 5:
                log.info("Refreshing listener...")
                await setup_listener(client)
                cycles_without_new = 0

            await asyncio.sleep(MONITOR_CHECK_INTERVAL)

        except Exception as e:
            log.error(f"Main error: {e}", exc_info=True)
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
