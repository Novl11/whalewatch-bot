import asyncio
from services.binance import (
    fetch_all_futures_tickers, fetch_klines, fetch_funding_rate, fetch_open_interest,
    binance_futures_symbol,
)
from services.indicators import calc_rsi, _ema, calc_macd, calc_bollinger, calc_adx, calc_stochastic, calc_vwap

TOP_N = 200
SEM = asyncio.Semaphore(15)  # max 15 concurrent calls to Binance


def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0
    return sum(values[-period:]) / period


async def scan_signals() -> dict:
    """Full multi-factor scan: top 200 coins, 10+ indicators, confident LONG/SHORT."""
    tickers = await fetch_all_futures_tickers()
    tickers.sort(key=lambda t: float(t.get("quoteVolume", 0) or 0), reverse=True)
    top = tickers[:TOP_N]

    results = await asyncio.gather(
        *[_analyze_one(t) for t in top],
        return_exceptions=True,
    )

    signals = {"long": [], "short": []}
    for r in results:
        if isinstance(r, dict) and "score" in r:
            s = r["score"]
            if s >= 4:
                signals["long"].append(r)
            elif s <= -4:
                signals["short"].append(r)

    signals["long"].sort(key=lambda x: x["score"], reverse=True)
    signals["short"].sort(key=lambda x: x["score"])
    signals["long"] = signals["long"][:5]
    signals["short"] = signals["short"][:5]

    return signals


async def _analyze_one(ticker: dict) -> dict | None:
    async with SEM:
        symbol = ticker["symbol"]
        coin = symbol.replace("USDT", "")
        price = float(ticker.get("lastPrice", 0))
        change = float(ticker.get("priceChangePercent", 0))
        volume = float(ticker.get("quoteVolume", 0))

        if price == 0 or price is None:
            return None

        # ── 1h klines ──
        raw = await fetch_klines(coin, "1h", 100)
        if len(raw) < 50:
            return None

        candles = raw
        closes = [c["close"] for c in candles]
        n = len(closes) - 1
        last_close = closes[-1]

        # ── Indicators ──
        rsi_vals = calc_rsi(closes)
        rsi = rsi_vals[-1] if len(rsi_vals) > 0 else 50

        ema21 = _ema(closes, 21)[-1] if len(closes) >= 21 else last_close
        ema50 = _ema(closes, 50)[-1] if len(closes) >= 50 else last_close
        ema9 = _ema(closes, 9)[-1] if len(closes) >= 9 else last_close

        macd = calc_macd(closes)
        macd_line = macd["macdLine"][-1] if macd["macdLine"] else 0
        macd_signal = macd["signal"][-1] if macd["signal"] else 0
        macd_hist = macd["histogram"][-1] if macd["histogram"] else 0
        macd_hist_prev = macd["histogram"][-2] if len(macd["histogram"]) > 1 else 0

        bb = calc_bollinger(closes)
        bb_upper = bb["upper"][-1] if bb["upper"] else last_close
        bb_lower = bb["lower"][-1] if bb["lower"] else last_close

        adx_vals = calc_adx(candles)
        adx = adx_vals[-1] if adx_vals else 0

        stoch = calc_stochastic(candles)
        stoch_k = stoch["k"][-1] if stoch["k"] else 50

        vwap_vals = calc_vwap(candles)
        vwap = vwap_vals[-1] if vwap_vals else last_close

        vol_avg = _sma([c["volume"] for c in candles], 20)
        vol_current = candles[-1]["volume"]

        # ── Funding ──
        funding = None
        try:
            f = await fetch_funding_rate(coin)
            if f:
                funding = float(f.get("lastFundingRate", 0)) * 100
        except Exception:
            pass

        # ── Open Interest ──
        oi = None
        try:
            oi = await fetch_open_interest(coin)
        except Exception:
            pass

        # ══════════════════════════════════════════
        #  SCORING — LONG side
        # ══════════════════════════════════════════
        long_score = 0
        short_score = 0
        long_reasons: list[str] = []
        short_reasons: list[str] = []

        # 1. Funding rate
        if funding is not None:
            if funding < -0.01:
                long_score += 3
                long_reasons.append("funding -1%")
            elif funding < -0.005:
                long_score += 2
                long_reasons.append("funding -0.5%")
            elif funding < -0.001:
                long_score += 1
                long_reasons.append("funding -0.1%")
            if funding > 0.01:
                short_score += 3
                short_reasons.append("funding +1%")
            elif funding > 0.005:
                short_score += 2
                short_reasons.append("funding +0.5%")
            elif funding > 0.001:
                short_score += 1
                short_reasons.append("funding +0.1%")

        # 2. RSI
        if rsi < 30:
            long_score += 4
            long_reasons.append("RSI перепродан")
        elif rsi < 35:
            long_score += 3
            long_reasons.append("RSI 30-35")
        elif rsi < 40:
            long_score += 2
            long_reasons.append("RSI 35-40")
        elif rsi < 45:
            long_score += 1
        elif rsi > 70:
            short_score += 4
            short_reasons.append("RSI перекуплен")
        elif rsi > 65:
            short_score += 3
            short_reasons.append("RSI 65-70")
        elif rsi > 60:
            short_score += 2
            short_reasons.append("RSI 60-65")
        elif rsi > 55:
            short_score += 1

        # 3. EMA alignment
        if last_close > ema9 and ema9 > ema21 and ema21 > ema50:
            long_score += 3
            long_reasons.append("тренд вверх")
        elif last_close > ema9 and ema9 > ema21:
            long_score += 2
        elif last_close > ema21:
            long_score += 1
        if last_close < ema9 and ema9 < ema21 and ema21 < ema50:
            short_score += 3
            short_reasons.append("тренд вниз")
        elif last_close < ema9 and ema9 < ema21:
            short_score += 2
        elif last_close < ema21:
            short_score += 1

        # 4. MACD
        if macd_line > macd_signal and macd_hist > macd_hist_prev:
            long_score += 2
            long_reasons.append("MACD +")
        elif macd_line > macd_signal:
            long_score += 1
        if macd_line < macd_signal and macd_hist < macd_hist_prev:
            short_score += 2
            short_reasons.append("MACD -")
        elif macd_line < macd_signal:
            short_score += 1

        # 5. Bollinger Bands
        if last_close <= bb_lower * 1.01:
            long_score += 2
            long_reasons.append("у нижней BB")
        elif last_close <= bb_lower * 1.02:
            long_score += 1
        if last_close >= bb_upper * 0.99:
            short_score += 2
            short_reasons.append("у верхней BB")
        elif last_close >= bb_upper * 0.98:
            short_score += 1

        # 6. ADX (тренд сильный)
        if adx > 30:
            if long_score > short_score:
                long_score += 1
                long_reasons.append("ADX сильный")
            elif short_score > long_score:
                short_score += 1
                short_reasons.append("ADX сильный")

        # 7. Stochastic
        if stoch_k < 15:
            long_score += 2
            long_reasons.append("Stoch перепродан")
        elif stoch_k < 25:
            long_score += 1
        if stoch_k > 85:
            short_score += 2
            short_reasons.append("Stoch перекуплен")
        elif stoch_k > 75:
            short_score += 1

        # 8. VWAP
        if last_close > vwap:
            long_score += 1
        elif last_close < vwap:
            short_score += 1

        # 9. Volume spike
        if vol_current > vol_avg * 1.5:
            if long_score > short_score:
                long_score += 1
            elif short_score > long_score:
                short_score += 1

        # 10. Open Interest (высокий OI = интерес)
        if oi is not None and oi > 0:
            if last_close > ema21:
                long_score += 1  # OI + uptrend = подтверждение
            elif last_close < ema21:
                short_score += 1

        # ── Final ──
        score = long_score - short_score

        # Build reasons
        reasons = (long_reasons if score > 0 else short_reasons) if abs(score) >= 4 else []

        # Confidence
        if score >= 10:
            label = "🔥 STRONG LONG"
            emoji = "🔥"
        elif score >= 7:
            label = "🟢 LONG"
            emoji = "🟢"
        elif score >= 4:
            label = "🟡 SLIGHT LONG"
            emoji = "🟡"
        elif score <= -10:
            label = "🔥 STRONG SHORT"
            emoji = "🔥"
        elif score <= -7:
            label = "🔴 SHORT"
            emoji = "🔴"
        elif score <= -4:
            label = "🟡 SLIGHT SHORT"
            emoji = "🟡"
        else:
            return None

        return {
            "coin": coin,
            "signal": label,
            "score": score,
            "price": price,
            "change": change,
            "rsi": round(rsi, 1),
            "funding": round(funding, 4) if funding is not None else None,
            "adx": round(adx, 1),
            "macd": round(macd_hist, 4),
            "volume_m": round(volume / 1e6, 1),
            "oi": round(oi / 1e6, 1) if oi else None,
            "reasons": reasons,
            "text": (
                f"{emoji} *{coin}* ${price:,.2f} ({change:+.2f}%) — {label}\n"
                f"   RSI {rsi:.0f} | "
                + (f"Funding {funding:+.3f}% | " if funding is not None else "")
                + f"ADX {adx:.0f} | MACD {macd_hist:.2f}"
                + (f" | OI {oi/1e6:.0f}M" if oi else "")
                + ("\n   " + " · ".join(reasons) if reasons else "")
            ),
        }
