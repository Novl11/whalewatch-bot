import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from aiohttp import web
from bot import dp, bot, on_startup


async def health_check(request):
    return web.Response(text="ok", content_type="text/plain")


async def index_page(request):
    return web.Response(
        text="<!DOCTYPE html><html lang='ru'><head><meta charset='UTF-8'>"
        "<title>WhaleWatch Bot</title></head><body style='background:#0a0e17;color:#e0e6f0;font-family:sans-serif;text-align:center;padding:60px 20px'>"
        "<h1 style='font-size:48px'>🐋 WhaleWatch Bot</h1>"
        "<p style='font-size:20px;color:#8892b0;margin:20px 0'>Крипто-терминал в Telegram</p>"
        "<a href='https://t.me/WhaleAnalyst_bot' style='display:inline-block;background:linear-gradient(135deg,#4facfe,#00f2fe);color:#0a0e17;padding:14px 36px;border-radius:12px;text-decoration:none;font-weight:700;font-size:18px'>🚀 Открыть в Telegram</a>"
        "<p style='margin-top:40px;color:#4a5568'>Анализ спота и фьючерсов · 18 индикаторов · Fear &amp; Greed · Обзор рынка</p>"
        "</body></html>",
        content_type="text/html",
    )


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", index_page)
    app.router.add_get("/health", health_check)
    port = int(os.getenv("PORT", "8080"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌐 Health server on port {port}")


async def main():
    await asyncio.gather(
        start_health_server(),
        _run_bot(),
    )


async def _run_bot():
    await on_startup()
    print("🐋 WhaleWatch Bot is running...")
    await dp.start_polling(bot, handle_signals=True)


if __name__ == "__main__":
    asyncio.run(main())
