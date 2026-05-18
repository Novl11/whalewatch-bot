import asyncio
from services.binance import (
    fetch_futures_ticker,
    fetch_funding_rate,
    fetch_funding_rate_history,
    fetch_open_interest,
    fetch_oi_24h_ago,
    fetch_long_short_ratio,
    fetch_top_trader_ls_ratio,
    fetch_top_trader_position_ratio,
    fetch_futures_klines,
    fetch_futures_24h_agg,
    fetch_taker_volume,
)
from services.indicators import calc_rsi, calc_macd, calc_bollinger


def _trend_label(diff_pct: float) -> str:
    if diff_pct > 2:
        return "🟢 Сильный восходящий"
    if diff_pct > 0.5:
        return "🟢 Восходящий"
    if diff_pct < -2:
        return "🔴 Сильный нисходящий"
    if diff_pct < -0.5:
        return "🔴 Нисходящий"
    return "⚪ Боковой"


def _signal_verdict(
    ls_ratio: float | None, top_ls: float | None, funding: float | None
) -> list[str]:
    args = []
    if ls_ratio is not None:
        if ls_ratio > 1.5:
            args.append("🔴 Толпа сильно в лонг — возможен откат")
        elif ls_ratio > 1.2:
            args.append("🟡 Перевес лонгов — осторожно")
        elif ls_ratio < 0.7:
            args.append("🟢 Толпа в шорте — возможен рост")
        elif ls_ratio < 0.85:
            args.append("🟡 Перевес шортов — жди отскока")
        else:
            args.append("⚪ L/S сбалансирован")

    if top_ls is not None:
        if top_ls > 1.5:
            args.append("🐳 Крупные игроки в лонг — бычий сигнал")
        elif top_ls < 0.7:
            args.append("🐳 Крупные игроки в шорт — медвежий сигнал")

    if funding is not None:
        fr_pct = funding * 100
        if fr_pct > 0.01:
            args.append(f"💸 Фандинг высокий ({fr_pct:.4f}%) — лонг дорогой, жди шорта")
        elif fr_pct < -0.01:
            args.append(f"💸 Фандинг отрицательный ({fr_pct:.4f}%) — шорт дорогой, жди лонга")
        elif -0.005 < fr_pct < 0.005:
            args.append("💸 Фандинг нейтральный — держать позицию ок")

    return args


def _oi_analysis(oi: float | None, oi_24h: float | None) -> list[str]:
    args = []
    if oi is not None and oi_24h is not None and oi_24h > 0:
        oi_change = ((oi - oi_24h) / oi_24h) * 100
        if oi_change > 10:
            args.append(f"📊 OI вырос на {oi_change:.1f}% — деньги заходят, тренд усиливается")
        elif oi_change > 3:
            args.append(f"📊 OI растёт ({oi_change:.1f}%) — интерес растёт")
        elif oi_change < -10:
            args.append(f"📊 OI упал на {oi_change:.1f}% — деньги уходят, тренд слабеет")
        elif oi_change < -3:
            args.append(f"📊 OI снижается ({oi_change:.1f}%) — интерес падает")
        else:
            args.append(f"📊 OI стабилен ({oi_change:.1f}%)")
    return args


def _technical_analysis(closes: list[float]) -> list[str]:
    if len(closes) < 30:
        return ["⚠️ Недостаточно данных для тех. анализа"]
    args = []
    rsi = calc_rsi(closes)
    macd = calc_macd(closes)
    bb = calc_bollinger(closes)
    last = len(closes) - 1
    price = closes[last]

    rsi_v = rsi[last]
    if rsi_v > 70:
        args.append(f"📈 RSI {rsi_v:.0f} — перекупленность, возможен откат")
    elif rsi_v < 30:
        args.append(f"📉 RSI {rsi_v:.0f} — перепроданность, возможен отскок")
    elif rsi_v > 60:
        args.append(f"📈 RSI {rsi_v:.0f} — бычий импульс")
    elif rsi_v < 40:
        args.append(f"📉 RSI {rsi_v:.0f} — медвежий импульс")
    else:
        args.append(f"⚪ RSI {rsi_v:.0f} — нейтрален")

    hist = macd["histogram"][last]
    prev_hist = macd["histogram"][last - 1] if last > 0 else 0
    if hist > 0 and hist > prev_hist:
        args.append("🟢 MACD гистограмма растёт — бычий момент")
    elif hist < 0 and hist < prev_hist:
        args.append("🔴 MACD гистограмма падает — медвежий момент")
    elif hist > 0:
        args.append("🟢 MACD положительный — бычий")
    elif hist < 0:
        args.append("🔴 MACD отрицательный — медвежий")
    else:
        args.append("⚪ MACD нейтрален")

    bb_up = bb["upper"][last]
    bb_low = bb["lower"][last]
    if price > bb_up:
        args.append("📊 Цена выше Bollinger — экстремум, возможен откат")
    elif price < bb_low:
        args.append("📊 Цена ниже Bollinger — экстремум, возможен отскок")
    elif price > bb["middle"][last] * 1.01:
        args.append("📊 Цена выше средней BB — бычий настрой")
    elif price < bb["middle"][last] * 0.99:
        args.append("📊 Цена ниже средней BB — медвежий настрой")

    return args


def _recommendation(
    ls_ratio: float | None,
    top_ls: float | None,
    oi: float | None,
    oi_24h: float | None,
    funding: float | None,
    rsi_v: float | None,
    trend_pct: float | None,
) -> tuple[str, list[str]]:
    score = 0
    reasons_for: list[str] = []
    reasons_against: list[str] = []

    if trend_pct is not None:
        if trend_pct > 1:
            score += 2
            reasons_for.append("Цена растёт")
        elif trend_pct < -1:
            score -= 2
            reasons_against.append("Цена падает")

    if rsi_v is not None:
        if rsi_v < 30:
            score += 2
            reasons_for.append("RSI в зоне перепроданности")
        elif rsi_v > 70:
            score -= 2
            reasons_against.append("RSI в зоне перекупленности")
        elif rsi_v > 60:
            score += 1
            reasons_for.append("RSI показывает бычий импульс")
        elif rsi_v < 40:
            score -= 1
            reasons_against.append("RSI показывает медвежий импульс")

    if funding is not None:
        fr_pct = funding * 100
        if fr_pct < -0.005:
            score += 1
            reasons_for.append("Отрицательный фандинг — шорт дорогой")
        elif fr_pct > 0.01:
            score -= 1
            reasons_against.append("Фандинг высокий — лонг перегрет")

    if ls_ratio is not None:
        if ls_ratio > 1.5:
            score -= 1
            reasons_against.append("Толпа в лонге — риск отката")
        elif ls_ratio < 0.7:
            score += 1
            reasons_for.append("Толпа в шорте — потенциал роста")

    if top_ls is not None:
        if top_ls > 1.3:
            score += 1
            reasons_for.append("Крупные игроки в лонге")
        elif top_ls < 0.7:
            score -= 1
            reasons_against.append("Крупные игроки в шорте")

    if oi is not None and oi_24h is not None and oi_24h > 0:
        oi_change = ((oi - oi_24h) / oi_24h) * 100
        if oi_change > 5:
            score += 1
            reasons_for.append("OI растёт — деньги заходят")
        elif oi_change < -5:
            score -= 1
            reasons_against.append("OI падает — деньги уходят")

    if score >= 3:
        verdict = "🟢 LONG"
    elif score >= 1:
        verdict = "🟡 СКОРЕЕ LONG"
    elif score <= -3:
        verdict = "🔴 SHORT"
    elif score <= -1:
        verdict = "🟡 СКОРЕЕ SHORT"
    else:
        verdict = "⚪ НЕЙТРАЛЬНО"

    return verdict, reasons_for, reasons_against


async def analyze_futures(coin: str) -> dict:
    coin = coin.upper()

    (
        agg,
        funding,
        funding_hist,
        oi,
        oi_24h,
        ls_ratio,
        top_ls,
        top_pos,
        klines,
        taker,
    ) = await asyncio.gather(
        fetch_futures_24h_agg(coin),
        fetch_funding_rate(coin),
        fetch_funding_rate_history(coin, 50),
        fetch_open_interest(coin),
        fetch_oi_24h_ago(coin),
        fetch_long_short_ratio(coin),
        fetch_top_trader_ls_ratio(coin),
        fetch_top_trader_position_ratio(coin),
        fetch_futures_klines(coin, "15m", 100),
        fetch_taker_volume(coin),
    )

    price = agg.get("last", 0)
    change = agg.get("change", 0)
    high = agg.get("high", 0)
    low = agg.get("low", 0)
    vol = agg.get("quote_volume", 0)
    trades = agg.get("count", 0)
    funding_rate = float(funding.get("lastFundingRate", 0)) if funding else 0

    closes = [k["close"] for k in klines] if klines else []
    rsi_v = calc_rsi(closes)[-1] if len(closes) > 14 else None

    verdict, reasons_for, reasons_against = _recommendation(
        ls_ratio, top_ls, oi, oi_24h, funding_rate, rsi_v, change
    )

    signal_args = _signal_verdict(ls_ratio, top_ls, funding_rate)
    oi_args = _oi_analysis(oi, oi_24h)
    tech_args = _technical_analysis(closes)

    if funding_hist:
        rates = [float(f.get("fundingRate", 0)) for f in funding_hist if f.get("fundingRate")]
        avg_funding = sum(rates) / len(rates) if rates else 0
    else:
        rates = []
        avg_funding = 0

    # format funding rate trend
    fr_hist_8 = rates[-8:] if len(rates) >= 8 else rates
    fr_trend_text = (
        f"{'🟢' if fr_hist_8[-1] > fr_hist_8[0] else '🔴' if fr_hist_8[-1] < fr_hist_8[0] else '⚪'}"
        if len(fr_hist_8) >= 2
        else "⚪"
    )

    return {
        "coin": coin,
        "price": price,
        "change_24h": change,
        "high_24h": high,
        "low_24h": low,
        "volume_24h": vol,
        "trades_24h": trades,
        "funding_rate": funding_rate,
        "avg_funding_8h": avg_funding,
        "funding_trend": fr_trend_text,
        "oi": oi,
        "oi_24h_ago": oi_24h,
        "oi_change_pct": ((oi - oi_24h) / oi_24h * 100) if oi is not None and oi_24h and oi_24h > 0 else None,
        "ls_ratio": ls_ratio,
        "top_trader_ls": top_ls,
        "top_trader_pos": top_pos,
        "rsi": rsi_v,
        "taker_buy_ratio": taker.get("buy_ratio", 0.5),
        "trend_label": _trend_label(change),
        "signals": signal_args,
        "oi_analysis": oi_args,
        "technical": tech_args,
        "verdict": verdict,
        "reasons_for": reasons_for,
        "reasons_against": reasons_against,
    }
