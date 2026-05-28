import asyncio
from services.binance import (
    fetch_all_futures_tickers, fetch_klines, fetch_funding_rate,
)
from services.indicators import calc_rsi, _ema, calc_macd, calc_bollinger, calc_adx, calc_stochastic, calc_vwap

TOP_N = 200
TIMEOUT = 8


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0
    return sum(values[-period:]) / period


async def scan_signals() -> dict:
    """Scan top 200 coins, compute multi-factor score, return best LONG/SHORT."""
    tickers = await fetch_all_futures_tickers()
    tickers.sort(key=lambda t: float(t.get("quoteVolume", 0) or 0), reverse=True)

    results = await asyncio.gather(
        *[_analyze_one(t) for t in tickers[:TOP_N]],
        return_exceptions=True,
    )

    long_list = []
    short_list = []
    for r in results:
        if isinstance(r, dict) and "score" in r:
            if r["score"] >= 3:
                long_list.append(r)
            elif r["score"] <= -3:
                short_list.append(r)

    long_list.sort(key=lambda x: x["score"], reverse=True)
    short_list.sort(key=lambda x: x["score"])
    return {"long": long_list[:5], "short": short_list[:5]}


async def _analyze_one(ticker: dict) -> dict | None:
    try:
        return await _analyze(ticker)
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None


async def _analyze(ticker: dict) -> dict | None:
    symbol = ticker["symbol"]
    coin = symbol.replace("USDT", "")
    price = float(ticker.get("lastPrice", 0))
    change = float(ticker.get("priceChangePercent", 0))
    volume = float(ticker.get("quoteVolume", 0))

    if not price:
        return None

    # ── 1h klines (50 candles is enough for indicators) ──
    raw = await asyncio.wait_for(fetch_klines(coin, "1h", 60), timeout=TIMEOUT)
    if len(raw) < 50:
        return None

    candles = raw
    closes = [c["close"] for c in candles]
    last_close = closes[-1]

    # ── All indicators ──
    rsi_vals = calc_rsi(closes)
    rsi = rsi_vals[-1] if rsi_vals else 50

    ema21 = _ema(closes, 21)[-1] if len(closes) >= 21 else last_close
    ema9 = _ema(closes, 9)[-1] if len(closes) >= 9 else last_close
    ema50 = _ema(closes, 50)[-1] if len(closes) >= 50 else last_close

    macd = calc_macd(closes)
    m_line = macd["macdLine"][-1] if macd["macdLine"] else 0
    m_sig = macd["signal"][-1] if macd["signal"] else 0
    m_hist = macd["histogram"][-1] if macd["histogram"] else 0
    m_hist_p = macd["histogram"][-2] if len(macd["histogram"]) > 1 else 0

    bb = calc_bollinger(closes)
    bb_up = bb["upper"][-1] if bb["upper"] else last_close
    bb_lo = bb["lower"][-1] if bb["lower"] else last_close

    adx_vals = calc_adx(candles)
    adx = adx_vals[-1] if adx_vals else 0

    stoch_vals = calc_stochastic(candles)
    stoch_k = stoch_vals["k"][-1] if stoch_vals["k"] else 50

    vwap_vals = calc_vwap(candles)
    vwap = vwap_vals[-1] if vwap_vals else last_close

    vol_current = candles[-1]["volume"]
    vol_avg = _sma([c["volume"] for c in candles], 20)

    # ── Funding (only one API call per coin) ──
    funding = None
    try:
        f = await asyncio.wait_for(fetch_funding_rate(coin), timeout=TIMEOUT)
        if f:
            funding = float(f.get("lastFundingRate", 0)) * 100
    except Exception:
        pass

    # ═══════════════ S C O R I N G ═══════════════
    long_score = 0
    short_score = 0
    long_r: list[str] = []
    short_r: list[str] = []

    # 1. Funding rate (max ±3)
    if funding is not None:
        if funding < -0.01:
            long_score += 3; long_r.append("funding -1%")
        elif funding < -0.005:
            long_score += 2; long_r.append("funding -0.5%")
        elif funding < -0.001:
            long_score += 1; long_r.append("funding -0.1%")
        if funding > 0.01:
            short_score += 3; short_r.append("funding +1%")
        elif funding > 0.005:
            short_score += 2; short_r.append("funding +0.5%")
        elif funding > 0.001:
            short_score += 1; short_r.append("funding +0.1%")

    # 2. RSI (max ±4)
    if rsi < 30:
        long_score += 4; long_r.append("RSI перепродан")
    elif rsi < 35:
        long_score += 3; long_r.append("RSI 30-35")
    elif rsi < 40:
        long_score += 2; long_r.append("RSI 35-40")
    elif rsi < 45:
        long_score += 1
    if rsi > 70:
        short_score += 4; short_r.append("RSI перекуплен")
    elif rsi > 65:
        short_score += 3; short_r.append("RSI 65-70")
    elif rsi > 60:
        short_score += 2; short_r.append("RSI 60-65")
    elif rsi > 55:
        short_score += 1

    # 3. EMA alignment (max ±3)
    if last_close > ema9 and ema9 > ema21 and ema21 > ema50:
        long_score += 3; long_r.append("тренд вверх")
    elif last_close > ema9 and ema9 > ema21:
        long_score += 2
    elif last_close > ema21:
        long_score += 1
    if last_close < ema9 and ema9 < ema21 and ema21 < ema50:
        short_score += 3; short_r.append("тренд вниз")
    elif last_close < ema9 and ema9 < ema21:
        short_score += 2
    elif last_close < ema21:
        short_score += 1

    # 4. MACD (max ±2)
    if m_line > m_sig and m_hist > m_hist_p:
        long_score += 2; long_r.append("MACD +")
    elif m_line > m_sig:
        long_score += 1
    if m_line < m_sig and m_hist < m_hist_p:
        short_score += 2; short_r.append("MACD -")
    elif m_line < m_sig:
        short_score += 1

    # 5. Bollinger (max ±2)
    if last_close <= bb_lo * 1.01:
        long_score += 2; long_r.append("у нижней BB")
    elif last_close <= bb_lo * 1.02:
        long_score += 1
    if last_close >= bb_up * 0.99:
        short_score += 2; short_r.append("у верхней BB")
    elif last_close >= bb_up * 0.98:
        short_score += 1

    # 6. ADX (max ±1)
    if adx > 30:
        if long_score > short_score:
            long_score += 1; long_r.append("ADX сильный")
        elif short_score > long_score:
            short_score += 1; short_r.append("ADX сильный")

    # 7. Stochastic (max ±2)
    if stoch_k < 15:
        long_score += 2; long_r.append("Stoch перепродан")
    elif stoch_k < 25:
        long_score += 1
    if stoch_k > 85:
        short_score += 2; short_r.append("Stoch перекуплен")
    elif stoch_k > 75:
        short_score += 1

    # 8. VWAP (max ±1)
    if last_close > vwap:
        long_score += 1
    elif last_close < vwap:
        short_score += 1

    # 9. Volume spike (max ±1)
    if vol_current > vol_avg * 1.5:
        if long_score > short_score:
            long_score += 1
        elif short_score > long_score:
            short_score += 1

    # ── Result ──
    score = long_score - short_score
    reasons = long_r if score > 0 else short_r

    if score >= 9:
        label = "🔥 STRONG LONG"; emoji = "🔥"
    elif score >= 6:
        label = "🟢 LONG"; emoji = "🟢"
    elif score >= 3:
        label = "🟡 SLIGHT LONG"; emoji = "🟡"
    elif score <= -9:
        label = "🔥 STRONG SHORT"; emoji = "🔥"
    elif score <= -6:
        label = "🔴 SHORT"; emoji = "🔴"
    elif score <= -3:
        label = "🟡 SLIGHT SHORT"; emoji = "🟡"
    else:
        return None

    return {
        "coin": coin,
        "signal": label,
        "score": score,
        "price": round(price, 4),
        "change": round(change, 2),
        "rsi": round(rsi, 1),
        "funding": round(funding, 4) if funding is not None else None,
        "adx": round(adx, 1),
        "macd": round(m_hist, 4),
        "volume_m": round(volume / 1e6, 1),
        "reasons": reasons,
        "text": (
            f"{emoji} *{coin}* ${price:,.2f} ({change:+.2f}%) — {label}\n"
            f"   RSI {rsi:.0f} | ADX {adx:.0f}"
            + (f" | Funding {funding:+.3f}%" if funding is not None else "")
            + ("\n   " + " · ".join(reasons) if reasons else "")
        ),
    }
