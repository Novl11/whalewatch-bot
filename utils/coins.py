COIN_WHITELIST = [
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "AVAX", "LINK",
    "DOT", "POL", "LTC", "BCH", "UNI", "ATOM", "XLM", "ETC", "FIL", "HBAR",
    "APT", "ARB", "OP", "VET", "NEAR", "INJ", "SUI", "SEI", "TIA", "ICP",
    "RENDER", "FET", "GRT", "AAVE", "ALGO", "STX", "IMX", "LDO", "PEPE",
    "SHIB", "BONK", "FLOKI", "WIF", "JUP", "WLD", "PENDLE", "RUNE", "EGLD",
    "SAND", "MANA", "AXS", "FLOW", "XTZ", "KAS", "SNX", "CRV", "THETA", "TON",
    "ENA", "ONDO", "ORDI", "TRUMP", "W", "STRK", "DYDX", "GMX", "COMP", "ZEC",
    "TAO", "CAKE", "ENS", "CHZ", "GALA", "ROSE", "IOTA", "QNT", "BLUR", "APE",
    "MINA", "CKB", "CFX", "CELO",
]

FREE_COINS = list(COIN_WHITELIST)

COIN_DISPLAY = {
    "PEPE": "PEPE",
    "SHIB": "SHIB",
    "BONK": "BONK",
    "FLOKI": "FLOKI",
}


def display_coin(symbol: str) -> str:
    return COIN_DISPLAY.get(symbol, symbol)


def binance_symbol(symbol: str) -> str:
    return f"{symbol}USDT"


def binance_futures_symbol(symbol: str) -> str:
    return f"{symbol}USDT"
