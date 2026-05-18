import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PRO_DURATION_DAYS = int(os.getenv("PRO_DURATION_DAYS", "30"))
PRO_PRICE_USDT = float(os.getenv("PRO_PRICE_USDT", "10"))
USDT_WALLET = os.getenv("USDT_WALLET", "")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "")
CHANNEL_IDS_RAW = os.getenv("CHANNEL_IDS", "")

def _parse_channel_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                ids.append(int(part))
            except ValueError:
                pass
    return ids

CHANNEL_IDS = _parse_channel_ids(CHANNEL_IDS_RAW)

BINANCE_SPOT_API = "https://api.binance.com"
BINANCE_FUTURES_API = "https://fapi.binance.com"
