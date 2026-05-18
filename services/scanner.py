import asyncio, re, random, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telethon import TelegramClient
from telethon.events import NewMessage
from config import TELEGRAM_TOKEN
from services.binance import fetch_ticker_24h

API_ID = int(os.getenv("TG_API_ID", "0"))
API_HASH = os.getenv("TG_API_HASH", "")
PHONE = os.getenv("TG_PHONE", "")
SESSION = os.getenv("TG_SESSION", "scanner")

TARGET_CHANNELS = [
    "https://t.me/bitcoin",          # Bitcoin channel
    "https://t.me/ethereum",         # Ethereum
    "https://t.me/cryptochannel",    # общие крипто-чаты нужно добавить свои
]

QUESTION_PATTERNS = [
    re.compile(r"(?i)(цена|прайс|price|сколько)\s*(btc|bitcoin|eth|ethereum|sol|solana|xrp|doge|ada|trx)"),
    re.compile(r"(?i)(rsi|индикатор|сигнал|анализ|аналитика|фьючерс|лонг|шорт|вердикт)"),
    re.compile(r"(?i)(\w+)\s*(to\s*the\s*moon|moon|растёт|падает|buy|sell|купить|продать)"),
]

BOT_LINK = f"🤖 @WhaleAnalyst_bot — крипто-терминал: цена, индикаторы, фьючерсы, FNG, обзор рынка"


async def reply_with_info(event: NewMessage.Event, coin: str = None):
    text = event.message.text or ""
    chat = await event.get_chat()

    if coin:
        ticker = await fetch_ticker_24h(coin)
        if ticker:
            price = float(ticker.get("lastPrice", 0))
            change = float(ticker.get("priceChangePercent", 0))
            emoji = "🟢" if change >= 0 else "🔴"
            reply = (
                f"📊 *{coin}/USDT* — {emoji} ${price:,.2f} ({change:+.2f}%)\n\n"
                f"Подробнее: /price_{coin} или @WhaleAnalyst_bot\n{BOT_LINK}"
            )
            await event.reply(reply, parse_mode="Markdown")
            return

    reply = (
        f"🧐 Вижу вопрос про крипту!\n\n"
        f"Попробуй @WhaleAnalyst_bot:\n"
        f"• /price BTC — цена и 24ч статистика\n"
        f"• /indicators BTC — RSI, MACD, BB\n"
        f"• /futures BTC — фьючерсный анализ\n"
        f"• /fng — Fear & Greed Index\n"
        f"• /market — обзор рынка\n"
        f"{BOT_LINK}"
    )
    await event.reply(reply, parse_mode="Markdown")


async def handler(event: NewMessage.Event):
    text = event.message.text or ""
    if not text:
        return

    coin = None
    for pat in QUESTION_PATTERNS:
        m = pat.search(text)
        if m:
            if m.lastindex and m.group(2):
                coin = m.group(2).upper() if len(m.group(2)) <= 10 else None
                if coin in ("BITCOIN",):
                    coin = "BTC"
                elif coin in ("ETHEREUM",):
                    coin = "ETH"
                elif coin in ("SOLANA",):
                    coin = "SOL"
            await reply_with_info(event, coin)
            return


async def main():
    if not API_ID or not API_HASH or not PHONE:
        print("❌ Укажи TG_API_ID, TG_API_HASH, TG_PHONE в .env")
        print("Получить: https://my.telegram.org/apps")
        return

    client = TelegramClient(SESSION, API_ID, API_HASH)

    await client.start(phone=PHONE)
    print(f"✅ Telethon logged in as: {(await client.get_me()).username or (await client.get_me()).id}")

    for url in TARGET_CHANNELS:
        try:
            entity = await client.get_entity(url)
            print(f"📡 Мониторю: {entity.title or url}")
        except Exception as e:
            print(f"⚠️ Не могу получить {url}: {e}")

    client.on(NewMessage(chats=TARGET_CHANNELS))(handler)
    print("🔍 Сканер запущен. Жду вопросы про крипту...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
