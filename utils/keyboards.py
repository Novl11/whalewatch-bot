from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.coins import COIN_WHITELIST, FREE_COINS


def main_menu(is_pro: bool, trial_available: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💵 Цена", callback_data="price"),
        InlineKeyboardButton(text="📊 Индикаторы", callback_data="indicators"),
    )
    if is_pro or trial_available:
        builder.row(
            InlineKeyboardButton(text="🔥 Фьючерсы", callback_data="futures"),
            InlineKeyboardButton(text="👁 Список", callback_data="watchlist"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🔒 Фьючерсы (Pro)", callback_data="futures_locked"),
            InlineKeyboardButton(text="👁 Список", callback_data="watchlist"),
        )
    builder.row(
        InlineKeyboardButton(text="🔔 Оповещения", callback_data="alerts_list"),
        InlineKeyboardButton(text="⭐ Pro", callback_data="pro_info"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Топ монет", callback_data="top_menu"),
        InlineKeyboardButton(text="🌍 Рынок", callback_data="market"),
    )
    builder.row(
        InlineKeyboardButton(text="😱 FNG", callback_data="fng"),
    )
    return builder.as_markup()


def timeframe_selection(coin: str, callback_prefix: str = "indicators") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    intervals = [("1m", "1m"), ("5m", "5m"), ("15m", "15m"), ("1h", "1h"), ("4h", "4h")]
    for label, tf in intervals:
        builder.button(text=label, callback_data=f"{callback_prefix}_tf:{coin}:{tf}")
    builder.adjust(5)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"{callback_prefix}:{coin}"))
    return builder.as_markup()


def top_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 Рост", callback_data="top:gainers"),
        InlineKeyboardButton(text="📉 Падение", callback_data="top:losers"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Объём", callback_data="top:volume"),
    )
    builder.row(InlineKeyboardButton(text="🏠 Меню", callback_data="menu"))
    return builder.as_markup()


def coin_selection(callback_prefix: str, page: int = 0, pro: bool = False) -> InlineKeyboardMarkup:
    coins = COIN_WHITELIST if pro else FREE_COINS
    per_page = 10
    start = page * per_page
    chunk = coins[start:start + per_page]

    builder = InlineKeyboardBuilder()
    for c in chunk:
        builder.row(
            InlineKeyboardButton(text=c, callback_data=f"{callback_prefix}:{c}")
        )
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}_page:{page - 1}"))
    if start + per_page < len(coins):
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}_page:{page + 1}"))
    if nav_row:
        builder.row(*nav_row)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()
