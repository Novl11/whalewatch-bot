from urllib.parse import quote

BOT_LINK = "🤖 [@WhaleAnalyst_bot](https://t.me/WhaleAnalyst_bot) — крипто-терминал в Telegram"
BOT_USERNAME = "@WhaleAnalyst_bot"


def share_url(text: str) -> str:
    msg = f"{text}\n\n{BOT_USERNAME} — крипто-терминал в Telegram"
    return f"https://t.me/share/url?url=https://t.me/WhaleAnalyst_bot&text={quote(msg)}"


def add_footer(text: str) -> str:
    return text + "\n\n" + BOT_LINK


def add_footer_to_builder(builder, share_text: str = ""):
    from aiogram.types import InlineKeyboardButton
    builder.row(
        InlineKeyboardButton(text="🔗 Поделиться", url=share_url(share_text)),
        InlineKeyboardButton(text="🤖 @WhaleAnalyst_bot", url="https://t.me/WhaleAnalyst_bot"),
    )
