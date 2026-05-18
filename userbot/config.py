import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("USERBOT_API_ID", "0"))
API_HASH = os.getenv("USERBOT_API_HASH", "")
PHONE = os.getenv("USERBOT_PHONE", "")

# Maximum groups to join per hour
MAX_JOINS_PER_HOUR = 3
# Maximum messages to send per day
MAX_MSGS_PER_DAY = 10
# Delay range before sending first message in a new group (seconds)
FIRST_MSG_DELAY_MIN = 300   # 5 min
FIRST_MSG_DELAY_MAX = 900   # 15 min
# Delay between actions (seconds)
ACTION_DELAY_MIN = 60
ACTION_DELAY_MAX = 180
# Don't repost to the same group within this many hours
GROUP_COOLDOWN_HOURS = 24

# Search keywords (Russian + English)
SEARCH_KEYWORDS = [
    "крипта",
    "криптовалюта",
    "трейдинг",
    "bitcoin",
    "crypto trading",
    "binance",
    "инвестиции",
]
