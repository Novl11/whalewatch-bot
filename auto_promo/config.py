import os
from dotenv import load_dotenv

load_dotenv()

# Telethon (user account)
API_ID = int(os.getenv("USERBOT_API_ID", "0"))
API_HASH = os.getenv("USERBOT_API_HASH", "")
PHONE = os.getenv("USERBOT_PHONE", "")

# LLM (choose one)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Scanner
SCAN_KEYWORDS = [
    "крипта", "криптовалюта", "трейдинг", "bitcoin",
    "crypto trading", "binance", "инвестиции",
    "помогите с", "вопрос по", "как торговать",
]
SEARCH_LIMIT = 50
MIN_GROUP_MEMBERS = 100

# Limits
MAX_JOINS_PER_HOUR = 3
MAX_REPLIES_PER_DAY = 10
MAX_REPLIES_PER_GROUP_PER_DAY = 3
ACTION_DELAY_MIN = 60  # seconds
ACTION_DELAY_MAX = 300
REPLY_DELAY_MIN = 300  # 5 min
REPLY_DELAY_MAX = 900  # 15 min
GROUP_COOLDOWN_HOURS = 72  # dont reply in same group within 3 days
MONITOR_CHECK_INTERVAL = 30  # check new messages every 30s

# LLM prompt template
LLM_PROMPT_TEMPLATE = """Ты — обычный трейдер в крипто-чате Telegram. 
Ответь на сообщение пользователя ПОЛЕЗНО и ЕСТЕСТВЕННО, как живой человек.

Сообщение: "{message}"

Правила:
1. Сначала дай реально полезный ответ по существу
2. В конце ОДНИМ предложением упомяни, что ты используешь @WhaleAnalyst_bot для быстрого анализа
3. Пиши на том же языке, что и сообщение
4. Не рекламируй агрессивно — просто поделись опытом
5. Ответ 2-4 предложения, не больше"""
