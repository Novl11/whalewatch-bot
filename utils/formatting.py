from utils.coins import display_coin


def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    if price >= 1:
        return f"${price:.4f}"
    if price >= 0.01:
        return f"${price:.6f}"
    return f"${price:.8f}"


def format_change(pct: float) -> str:
    sign = "+" if pct >= 0 else ""
    emoji = "🟢" if pct >= 0 else "🔴"
    return f"{emoji} {sign}{pct:.2f}%"


def format_volume(vol: float) -> str:
    if vol >= 1_000_000_000:
        return f"${vol / 1_000_000_000:.2f}B"
    if vol >= 1_000_000:
        return f"${vol / 1_000_000:.2f}M"
    return f"${vol:,.0f}"


def format_funding_rate(rate: float) -> str:
    pct = rate * 100
    if pct > 0:
        return f"🟢 {pct:.4f}%"
    if pct < 0:
        return f"🔴 {pct:.4f}%"
    return f"⚪ {pct:.4f}%"
