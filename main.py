import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from aiohttp import web
from bot import dp, bot, on_startup


async def health_check(request):
    return web.Response(text="ok", content_type="text/plain")


async def index_page(request):
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return web.Response(text=f.read(), content_type="text/html; charset=utf-8")
    except FileNotFoundError:
        return web.Response(text="WhaleWatch Bot", content_type="text/plain")


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
