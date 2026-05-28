import asyncio
from services.binance import (
    fetch_all_futures_tickers, fetch_klines, fetch_funding_rate,
)
from services.indicators import calc_rsi, _ema

TOP_N = 50


async def scan_signals() -> dict:
    """Scan all top futures coins and return LONG/SHORT signals."""
    tickers = await fetch_all_futures_tickers()
    tickers.sort(key=lambda t: float(t.get("quoteVolume", 0) or 0), reverse=True)

    top = tickers[:TOP_N]
    symbols = [t["symbol"].replace("USDT", "") for t in top]

    results = await asyncio.gather(
        *[_analyze_coin(t) for t in top],
        return_exceptions=True,
    )

    signals = {"long": [], "short": []}
    for res in results:
        if isinstance(res, dict):
            s = res["score"]
            if s > 0:
                signals["long"].append(res)
            elif s < 0:
                signals["short"].append(res)

    signals["long"].sort(key=lambda s: s["score"], reverse=True)
    signals["short"].sort(key=lambda s: s["score"])
    signals["long"] = signals["long"][:5]
    signals["short"] = signals["short"][:5]

    return signals


async def _analyze_coin(ticker: dict) -> dict | None:
    """Analyze a single coin and return signal data."""
    symbol = ticker["symbol"]
    coin = symbol.replace("USDT", "")
    price = float(ticker.get("lastPrice", 0))
    change = float(ticker.get("priceChangePercent", 0))
    vol = float(ticker.get("quoteVolume", 0))

    if price == 0:
        return None

    klines = await fetch_klines(coin, "15m", 100)
    if len(klines) < 50:
        return None

    closes = [k["close"] for k in klines]
    rsi_arr = calc_rsi(closes)
    ema21_arr = _ema(closes, 21)

    rsi = rsi_arr[-1] if rsi_arr else 50
    ema21 = ema21_arr[-1] if ema21_arr else price

    funding = None
    try:
        f = await fetch_funding_rate(coin)
        if f:
            funding = float(f.get("lastFundingRate", 0)) * 100
    except Exception:
        pass

    long_score = 0
    short_score = 0

    if funding is not None:
        if funding < -0.005:
            long_score += 2
        elif funding < -0.001:
            long_score += 1
        if funding > 0.005:
            short_score += 2
        elif funding > 0.001:
            short_score += 1

    if rsi < 40:
        long_score += 2
    elif rsi < 45:
        long_score += 1
    elif rsi > 60:
        short_score += 2
    elif rsi > 55:
        short_score += 1

    if price > ema21:
        long_score += 1
    elif price < ema21:
        short_score += 1

    score = long_score - short_score

    if abs(score) < 2:
        return None

    reasons = []
    if funding is not None:
        if score > 0 and funding < -0.001:
            reasons.append(f"funding {funding:.3f}%")
        elif score < 0 and funding > 0.001:
            reasons.append(f"funding +{funding:.3f}%")
    if (score > 0 and rsi < 45) or (score < 0 and rsi > 55):
        reasons.append(f"RSI {rsi:.0f}")
    if score > 0 and price > ema21:
        reasons.append("trend UP")
    elif score < 0 and price < ema21:
        reasons.append("trend DOWN")

    emoji = "🟢" if score > 0 else "🔴"
    change_emoji = "🟢" if change >= 0 else "🔴"

    return {
        "coin": coin,
        "signal": "LONG" if score > 0 else "SHORT",
        "score": score,
        "price": price,
        "change": change,
        "rsi": rsi,
        "funding": funding,
        "volume_m": vol / 1e6,
        "reasons": reasons,
        "text": (
            f"{emoji} *{coin}* ${price:,.2f} {change_emoji} {change:+.2f}%\n"
            f"   RSI {rsi:.0f} | "
            + (f"Funding {funding:+.3f}% | " if funding is not None else "")
            + f"{', '.join(reasons)}"
        ),
    }
