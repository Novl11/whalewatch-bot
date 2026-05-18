import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PRO_DURATION_DAYS = int(os.getenv("PRO_DURATION_DAYS", "30"))
PRO_PRICE_USDT = float(os.getenv("PRO_PRICE_USDT", "10"))
USDT_WALLET = os.getenv("USDT_WALLET", "")
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "")

BINANCE_SPOT_API = "https://api.binance.com"
BINANCE_FUTURES_API = "https://fapi.binance.com"
