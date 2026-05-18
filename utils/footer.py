BOT_LINK = "🤖 [@WhaleAnalyst_bot](https://t.me/WhaleAnalyst_bot) — крипто-терминал в Telegram"


def add_footer(text: str) -> str:
    return text + "\n\n" + BOT_LINK


def add_footer_to_builder(builder, row: int = -1):
    from aiogram.types import InlineKeyboardButton
    builder.row(
        InlineKeyboardButton(text="🤖 @WhaleAnalyst_bot", url="https://t.me/WhaleAnalyst_bot"),
    )
