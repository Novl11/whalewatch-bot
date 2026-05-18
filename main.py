import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from aiohttp import web
from bot import dp, bot, on_startup


async def health_check(request):
    return web.Response(text="ok", content_type="text/plain")


async def index_page(request):
    html = (
        "<!DOCTYPE html><html lang='ru'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>WhaleWatch Bot — крипто-терминал в Telegram</title>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0e17;color:#e0e6f0;line-height:1.6}"
        ".container{max-width:800px;margin:0 auto;padding:40px 20px}"
        ".header{text-align:center;padding:60px 0 40px}"
        ".logo{font-size:64px}"
        "h1{font-size:36px;background:linear-gradient(135deg,#4facfe,#00f2fe);-webkit-background-clip:text;-webkit-text-fill-color:transparent}"
        ".btn{display:inline-block;background:linear-gradient(135deg,#4facfe,#00f2fe);color:#0a0e17;padding:14px 36px;border-radius:12px;text-decoration:none;font-weight:700}"
        ".card{background:#111827;border:1px solid #1e293b;border-radius:16px;padding:24px;margin:12px 0}"
        "@media(max-width:640px){.features{grid-template-columns:1fr}}"
        "</style></head><body>"
        "<div class='container'>"
        "<div class='header'><div class='logo'>&#x1F40B;</div>"
        "<h1>WhaleWatch Bot</h1>"
        "<p>Крипто-терминал в Telegram: цена, 18 индикаторов, фьючерсы, FNG, обзор рынка.</p><br/>"
        "<a class='btn' href='https://t.me/WhaleAnalyst_bot' target='_blank'>&#x1F680; Открыть в Telegram</a></div>"
        "<div class='features'>"
        "<div class='card'><h3>&#x1F4B5; Цена 24/7</h3><p>82 монеты: цена, 24ч статистика, макс/мин, объём.</p></div>"
        "<div class='card'><h3>&#x1F4CA; 18 индикаторов</h3><p>RSI, MACD, BB, ATR, Stoch, ADX, CCI и другие. Бесплатно: RSI + EMA21.</p></div>"
        "<div class='card'><h3>&#x1F525; Фьючерсы</h3><p>Funding rate, OI, L/S, Taker volume, тех. анализ, вердикт LONG/SHORT.</p></div>"
        "<div class='card'><h3>&#x1F631; Fear &amp; Greed</h3><p>Индекс страха и жадности + обзор рынка: доминация BTC, капитализация.</p></div>"
        "<div class='card'><h3>&#x1F4C8; Топ монет</h3><p>Топ роста, падения и объёма за 24ч. Данные Binance.</p></div>"
        "<div class='card'><h3>&#x1F514; Оповещения</h3><p>Ценовые алерты. Бесплатно до 2, Pro безлимит.</p></div>"
        "</div>"
        "<div style='text-align:center;padding:20px;background:#111827;border-radius:16px;margin:24px 0'>"
        "<h2>Тарифы</h2>"
        "<p><b>Бесплатно:</b> все монеты, спот, базовые индикаторы, 1 пробный фьючерс</p>"
        "<p><b>&#x2B50; Pro:</b> 10 USDT / 30 дней — все 18 индикаторов, все таймфреймы, безлимитные фьючерсы</p>"
        "</div>"
        "<div style='text-align:center;color:#4a5568;padding:20px'>"
        "<p>Оплата: USDT (TRC20) — без посредников</p>"
        "<p>&#x1F40B; <a href='https://t.me/WhaleAnalyst_bot' style='color:#4facfe'>@WhaleAnalyst_bot</a></p>"
        "</div></div></body></html>"
    )
    return web.Response(text=html, content_type="text/html; charset=utf-8")


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
