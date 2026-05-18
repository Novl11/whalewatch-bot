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
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>WhaleWatch Bot — крипто-терминал в Telegram</title>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0e17;color:#e0e6f0;text-align:center;padding:60px 20px;line-height:1.6}"
        "h1{font-size:48px;margin-bottom:8px;background:linear-gradient(135deg,#4facfe,#00f2fe);-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
        ".sub{font-size:18px;color:#8892b0;margin-bottom:32px}"
        ".btn{display:inline-block;background:linear-gradient(135deg,#4facfe,#00f2fe);color:#0a0e17;padding:14px 36px;border-radius:12px;text-decoration:none;font-weight:700;font-size:18px;transition:transform .2s}"
        ".btn:hover{transform:translateY(-2px)}"
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;max-width:700px;margin:48px auto;text-align:left}"
        "@media(max-width:500px){.grid{grid-template-columns:1fr}}"
        ".card{background:#111827;border:1px solid #1e293b;border-radius:16px;padding:20px}"
        ".card h3{margin-bottom:6px;font-size:18px}"
        ".card p{color:#8892b0;font-size:14px}"
        ".footer{color:#4a5568;font-size:14px;margin-top:48px}"
        ".footer a{color:#4facfe}"
        "</style></head><body>"
        "<h1>&#x1F40B; WhaleWatch Bot</h1>"
        "<p class='sub'>Крипто-терминал в Telegram</p>"
        "<a class='btn' href='https://t.me/WhaleAnalyst_bot' target='_blank'>&#x1F680; Открыть в Telegram</a>"
        "<div class='grid'>"
        "<div class='card'><h3>&#x1F4B5; Цена 24/7</h3><p>82 монеты: цена, 24ч статистика, макс/мин, объём с Binance.</p></div>"
        "<div class='card'><h3>&#x1F4CA; 18 индикаторов</h3><p>RSI, MACD, BB, ATR, Stoch, ADX, CCI и другие. Бесплатно: RSI + EMA21.</p></div>"
        "<div class='card'><h3>&#x1F525; Фьючерсы</h3><p>Funding rate, Open Interest, L/S трейдеров, тех. анализ, вердикт LONG/SHORT.</p></div>"
        "<div class='card'><h3>&#x1F631; Fear &amp; Greed</h3><p>Индекс страха и жадности + обзор рынка: доминация BTC, капитализация, объём.</p></div>"
        "<div class='card'><h3>&#x1F4C8; Топ монет</h3><p>Топ роста, падения и объёма за 24ч. Свежие данные.</p></div>"
        "<div class='card'><h3>&#x1F514; Оповещения</h3><p>Ценовые алерты. Бесплатно до 2, Pro безлимит.</p></div>"
        "</div>"
        "<div style='background:#111827;border:1px solid #1e293b;border-radius:16px;padding:24px;max-width:500px;margin:0 auto'>"
        "<h2>&#x1F4B0; Тарифы</h2>"
        "<p style='margin-top:8px'><b>Бесплатно:</b> все монеты, спот, RSI+EMA21, 1 пробный фьючерс, топ, FNG, рынок</p>"
        "<p style='margin-top:8px'><b>&#x2B50; Pro:</b> 10 USDT / 30 дней — все 18 индикаторов, все таймфреймы, безлимитные фьючерсы и оповещения</p>"
        "</div>"
        "<div class='footer'><p>&#x1F40B; <a href='https://t.me/WhaleAnalyst_bot'>@WhaleAnalyst_bot</a> &middot; Оплата USDT (TRC20) без посредников</p></div>"
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
