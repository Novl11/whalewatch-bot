import math
from typing import Any


def _ema(values: list[float], period: int) -> list[float]:
    k = 2 / (period + 1)
    out: list[float] = []
    prev = values[0] if values else 0
    for i, v in enumerate(values):
        prev = values[0] if i == 0 else v * k + prev * (1 - k)
        out.append(prev)
    return out


def _sma(values: list[float], period: int, i: int) -> float:
    if i < period - 1:
        return values[i]
    return sum(values[i - period + 1:i + 1]) / period


def calc_rsi(closes: list[float], period: int = 14) -> list[float]:
    out: list[float] = []
    avg_gain = 0.0
    avg_loss = 0.0
    for i in range(len(closes)):
        if i == 0:
            out.append(50.0)
            continue
        change = closes[i] - closes[i - 1]
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0
        if i < period:
            avg_gain += gain
            avg_loss += loss
            out.append(50.0)
            continue
        if i == period:
            avg_gain /= period
            avg_loss /= period
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        rs = 100 if avg_loss == 0 else avg_gain / avg_loss
        out.append(100 - 100 / (1 + rs))
    return out


def calc_macd(closes: list[float]):
    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal = _ema(macd_line, 9)
    histogram = [a - b for a, b in zip(macd_line, signal)]
    return {"macdLine": macd_line, "signal": signal, "histogram": histogram}


def calc_bollinger(closes: list[float], period: int = 20, mult: int = 2):
    upper: list[float] = []
    lower: list[float] = []
    middle: list[float] = []
    for i in range(len(closes)):
        m = _sma(closes, period, i)
        middle.append(m)
        if i < period - 1:
            upper.append(m)
            lower.append(m)
            continue
        sl = closes[i - period + 1:i + 1]
        variance = sum((c - m) ** 2 for c in sl) / period
        std = math.sqrt(variance)
        upper.append(m + mult * std)
        lower.append(m - mult * std)
    return {"upper": upper, "middle": middle, "lower": lower}


def calc_atr(candles: list[dict], period: int = 14) -> list[float]:
    trs: list[float] = []
    for i in range(len(candles)):
        c = candles[i]
        if i == 0:
            tr = c["high"] - c["low"]
        else:
            prev = candles[i - 1]
            tr = max(
                c["high"] - c["low"],
                abs(c["high"] - prev["close"]),
                abs(c["low"] - prev["close"]),
            )
        trs.append(tr)
    out: list[float] = []
    for i in range(len(trs)):
        if i < period:
            out.append(sum(trs[:i + 1]) / (i + 1))
        else:
            out.append((out[i - 1] * (period - 1) + trs[i]) / period)
    return out


def calc_stochastic(candles: list[dict], k_period: int = 14, d_period: int = 3):
    k: list[float] = []
    for i in range(len(candles)):
        if i < k_period - 1:
            k.append(50.0)
            continue
        sl = candles[i - k_period + 1:i + 1]
        low = min(c["low"] for c in sl)
        high = max(c["high"] for c in sl)
        close = candles[i]["close"]
        k.append(50.0 if high == low else ((close - low) / (high - low)) * 100)
    d: list[float] = []
    for i in range(len(k)):
        if i < d_period - 1:
            d.append(k[i])
        else:
            d.append(sum(k[i - d_period + 1:i + 1]) / d_period)
    return {"k": k, "d": d}


def calc_adx(candles: list[dict], period: int = 14) -> list[float]:
    n = len(candles)
    plus_dm: list[float] = [0.0]
    minus_dm: list[float] = [0.0]
    tr: list[float] = [candles[0]["high"] - candles[0]["low"]]
    for i in range(1, n):
        up = candles[i]["high"] - candles[i - 1]["high"]
        down = candles[i - 1]["low"] - candles[i]["low"]
        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)
        c = candles[i]
        p = candles[i - 1]
        tr.append(max(c["high"] - c["low"], abs(c["high"] - p["close"]), abs(c["low"] - p["close"])))
    adx: list[float] = []
    for i in range(n):
        if i < period:
            adx.append(20.0)
            continue
        tr_sum = sum(tr[i - period + 1:i + 1])
        pdi = (sum(plus_dm[i - period + 1:i + 1]) / tr_sum) * 100
        mdi = (sum(minus_dm[i - period + 1:i + 1]) / tr_sum) * 100
        dx = 0 if pdi + mdi == 0 else (abs(pdi - mdi) / (pdi + mdi)) * 100
        adx.append(dx if i == period else (adx[i - 1] * (period - 1) + dx) / period)
    return adx


def calc_cci(candles: list[dict], period: int = 20) -> list[float]:
    tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles]
    out: list[float] = []
    for i in range(len(tp)):
        if i < period - 1:
            out.append(0.0)
            continue
        sl = tp[i - period + 1:i + 1]
        mean = sum(sl) / period
        md = sum(abs(v - mean) for v in sl) / period
        out.append(0.0 if md == 0 else (tp[i] - mean) / (0.015 * md))
    return out


def calc_williams_r(candles: list[dict], period: int = 14) -> list[float]:
    out: list[float] = []
    for i in range(len(candles)):
        if i < period - 1:
            out.append(-50.0)
            continue
        sl = candles[i - period + 1:i + 1]
        high = max(c["high"] for c in sl)
        low = min(c["low"] for c in sl)
        close = candles[i]["close"]
        out.append(-50.0 if high == low else ((high - close) / (high - low)) * -100)
    return out


def calc_mfi(candles: list[dict], period: int = 14) -> list[float]:
    tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in candles]
    raw_mf = [t * candles[i]["volume"] for i, t in enumerate(tp)]
    out: list[float] = []
    for i in range(len(candles)):
        if i < period:
            out.append(50.0)
            continue
        pos = 0.0
        neg = 0.0
        for j in range(i - period + 1, i + 1):
            if tp[j] > tp[j - 1]:
                pos += raw_mf[j]
            else:
                neg += raw_mf[j]
        ratio = 100 if neg == 0 else pos / neg
        out.append(100 - 100 / (1 + ratio))
    return out


def calc_obv(candles: list[dict]) -> list[float]:
    out: list[float] = [0.0]
    for i in range(1, len(candles)):
        prev = out[i - 1]
        if candles[i]["close"] > candles[i - 1]["close"]:
            out.append(prev + candles[i]["volume"])
        elif candles[i]["close"] < candles[i - 1]["close"]:
            out.append(prev - candles[i]["volume"])
        else:
            out.append(prev)
    return out


def calc_vwap(candles: list[dict]) -> list[float]:
    cum_vol = 0.0
    cum_tp = 0.0
    out: list[float] = []
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3
        cum_vol += c["volume"]
        cum_tp += tp * c["volume"]
        out.append(c["close"] if cum_vol == 0 else cum_tp / cum_vol)
    return out


def _signal(price: float, sma_val: float, high: float) -> str:
    return "bullish" if sma_val >= high else "bearish" if sma_val <= price else "neutral"


def build_snapshots(candles: list[dict], pro: bool = False, allowed: set | None = None) -> list[dict[str, Any]]:
    if len(candles) < 30:
        return []
    closes = [c["close"] for c in candles]
    last = len(closes) - 1
    price = closes[last]

    rsi = calc_rsi(closes)
    macd = calc_macd(closes)
    bb = calc_bollinger(closes)
    atr = calc_atr(candles)
    stoch = calc_stochastic(candles)
    adx_vals = calc_adx(candles)
    cci_vals = calc_cci(candles)
    wr = calc_williams_r(candles)
    mfi_vals = calc_mfi(candles)
    obv_vals = calc_obv(candles)
    vwap_vals = calc_vwap(candles)
    ema9 = _ema(closes, 9)
    ema21 = _ema(closes, 21)
    ema50 = _ema(closes, 50)
    ema200 = _ema(closes, 200)

    def _p(id_: str, label: str, value: str | float, signal: str = "neutral", detail: str = "") -> dict:
        return {"id": id_, "label": label, "value": value, "signal": signal, "detail": detail}

    rsi_v = rsi[last]
    snaps = []
    if not allowed or "rsi" in allowed:
        snaps.append(_p("rsi", "RSI (14)", f"{rsi_v:.1f}",
                       "bullish" if rsi_v >= 55 else "bearish" if rsi_v <= 45 else "neutral",
                       "Перекуплен" if rsi_v > 70 else "Перепродан" if rsi_v < 30 else ""))
    if not allowed or "macd" in allowed:
        hist = macd["histogram"][last]
        snaps.append(_p("macd", "MACD", f"{macd['macdLine'][last]:.2f}",
                       "bullish" if hist > 0 else "bearish" if hist < 0 else "neutral",
                       f"Signal {macd['signal'][last]:.2f} · Hist {hist:.2f}"))
    if not allowed or "ema9" in allowed:
        snaps.append(_p("ema9", "EMA 9", f"{ema9[last]:.2f}",
                       "bullish" if price > ema9[last] else "bearish"))
    if not allowed or "ema21" in allowed:
        snaps.append(_p("ema21", "EMA 21", f"{ema21[last]:.2f}",
                       "bullish" if price > ema21[last] else "bearish"))
    if not allowed or "ema50" in allowed:
        snaps.append(_p("ema50", "EMA 50", f"{ema50[last]:.2f}",
                       "bullish" if price > ema50[last] else "bearish"))
    if not allowed or "ema200" in allowed:
        snaps.append(_p("ema200", "EMA 200", f"{ema200[last]:.2f}",
                       "bullish" if price > ema200[last] else "bearish"))
    if not allowed or "sma20" in allowed:
        s20 = _sma(closes, 20, last)
        snaps.append(_p("sma20", "SMA 20", f"{s20:.2f}",
                       "bullish" if price > s20 else "bearish"))
    if not allowed or "sma50" in allowed:
        s50 = _sma(closes, 50, last)
        snaps.append(_p("sma50", "SMA 50", f"{s50:.2f}",
                       "bullish" if price > s50 else "bearish"))
    if not allowed or "sma200" in allowed:
        s200 = _sma(closes, 200, last)
        snaps.append(_p("sma200", "SMA 200", f"{s200:.2f}",
                       "bullish" if price > s200 else "bearish"))
    if not allowed or "bb" in allowed:
        b_up = bb["upper"][last]
        b_low = bb["lower"][last]
        snaps.append(_p("bb", "Bollinger", f"{price:.2f}",
                       "bearish" if price > b_up else "bullish" if price < b_low else "neutral",
                       f"U {b_up:.0f} · L {b_low:.0f}"))
    if not allowed or "atr" in allowed:
                        snaps.append(_p("atr", "ATR (14)", f"{atr[last]:.2f}", "neutral", "Волатильность"))
    if not allowed or "stoch" in allowed:
        sk = stoch["k"][last]
        snaps.append(_p("stoch", "Stochastic", f"{sk:.0f} / {stoch['d'][last]:.0f}",
                       "bullish" if sk >= 55 else "bearish" if sk <= 45 else "neutral"))
    if not allowed or "adx" in allowed:
        a = adx_vals[last]
        snaps.append(_p("adx", f"ADX (14)", f"{a:.1f}",
                       "bullish" if a > 25 else "neutral",
                                               "Сильный тренд" if a > 25 else "Слабый тренд"))
    if not allowed or "cci" in allowed:
        c = cci_vals[last]
        snaps.append(_p("cci", "CCI (20)", f"{c:.0f}",
                       "bullish" if c >= 100 else "bearish" if c <= -100 else "neutral"))
    if not allowed or "willr" in allowed:
        w = wr[last]
        snaps.append(_p("willr", "Williams %R", f"{w:.1f}",
                       "bearish" if w > -20 else "bullish" if w < -80 else "neutral"))
    if not allowed or "mfi" in allowed:
        m = mfi_vals[last]
        snaps.append(_p("mfi", "MFI (14)", f"{m:.1f}",
                       "bullish" if m >= 55 else "bearish" if m <= 45 else "neutral"))
    if not allowed or "obv" in allowed:
        ob = obv_vals[last]
        snaps.append(_p("obv", "OBV", f"{ob / 1e6:.2f}M",
                       "bullish" if ob > obv_vals[last - 5] else "bearish"))
    if not allowed or "vwap" in allowed:
        v = vwap_vals[last]
        snaps.append(_p("vwap", "VWAP", f"{v:.2f}",
                       "bullish" if price > v else "bearish"))

    return snaps
