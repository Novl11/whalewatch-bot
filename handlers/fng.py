from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
import aiohttp
import ssl
import certifi

router = Router()
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())


@router.message(Command("fng"))
async def cmd_fng(message: Message):
    msg = await message.answer("⏳ Загружаю Fear & Greed Index...")
    try:
        connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get("https://api.alternative.me/fng/?limit=7") as r:
                data = await r.json()
    except Exception as e:
        await msg.edit_text(f"❌ Ошибка загрузки: {e}")
        return

    items = data.get("data", [])
    if not items:
        await msg.edit_text("❌ Нет данных Fear & Greed.")
        return

    today = items[0]
    value = today["value"]
    classification = today["value_classification"]

    emoji_map = {
        "Extreme Fear": "😱",
        "Fear": "😨",
        "Neutral": "😐",
        "Greed": "😏",
        "Extreme Greed": "🔥",
    }
    emoji = emoji_map.get(classification, "❓")

    lines = [
        f"{emoji} *Fear & Greed Index*",
        f"",
        f"Сегодня: *{value}* — {classification}",
        f"",
        f"📊 *Последние 7 дней:*",
    ]

    for item in items:
        v = item["value"]
        ts = item.get("timestamp", "")
        if ts and ts != "0":
            import datetime
            dt = datetime.datetime.fromtimestamp(int(ts))
            date_str = dt.strftime("%d.%m")
        else:
            date_str = "—"
        lines.append(f"  {date_str}: {v}")

    await msg.edit_text("\n".join(lines), parse_mode="Markdown")
