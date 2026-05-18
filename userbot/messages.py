import random

PROMO_TEXTS = [
    (
        "🐋 Всем привет! Пользуюсь ботом WhaleWatch для анализа монет — очень удобно.\n\n"
        "📊 Показывает цену, RSI, MACD, Bollinger Bands\n"
        "🔥 Фьючерсы: funding rate, Open Interest, L/S трейдеров\n"
        "😱 Fear & Greed Index\n\n"
        "Бесплатно: @WhaleAnalyst_bot"
    ),
    (
        "📈 Кто ищет нормальный анализ монет в Telegram — @WhaleAnalyst_bot\n\n"
        "Бесплатно показывает:\n"
        "• RSI, MACD, EMA, BB\n"
        "• Funding rate и OI по фьючерсам\n"
        "• Вердикт LONG/SHORT\n"
        "• Fear & Greed Index\n\n"
        "Полезная штука, пользуюсь сам 👌"
    ),
    (
        "🔔 Нашёл полезного бота для крипты — @WhaleAnalyst_bot\n\n"
        "Закидываешь монету → получаешь полный анализ за секунду.\n"
        "Топ за 24ч, объёмы, индикаторы, фьючерсы — всё в одном месте.\n\n"
        "И бесплатно! Рекомендую 👇\n"
        "@WhaleAnalyst_bot"
    ),
    (
        "⚡️ @WhaleAnalyst_bot — реально удобный крипто-терминал\n\n"
        "✔️ Все монеты\n"
        "✔️ RSI, MACD, BB, ATR, Stochastic\n"
        "✔️ Фьючерсный анализ с вердиктом\n"
        "✔️ Watchlist, алерты\n"
        "✔️ Fear & Greed\n\n"
        "Сам в шоке, что бесплатно. Пользуйтесь 🤝"
    ),
]


def random_promo() -> str:
    return random.choice(PROMO_TEXTS)
