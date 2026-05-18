import json
from services.binance import fetch_klines, fetch_ticker_24h

QUICKCHART_URL = "https://quickchart.io/chart"


def _chart_url(coin: str, klines: list) -> str:
    if not klines:
        return None
    closes = [k["close"] for k in klines]
    times = [k["time"] for k in klines]
    labels = [t // 1000 for t in times[::20]]  # every 20th for label

    min_p = min(closes)
    max_p = max(closes)
    pad = (max_p - min_p) * 0.05 or max_p * 0.01

    chart = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": f"{coin}USDT",
                "data": closes,
                "borderColor": "#00c853",
                "backgroundColor": "rgba(0,200,83,0.1)",
                "fill": True,
                "pointRadius": 0,
                "borderWidth": 2,
            }],
        },
        "options": {
            "title": {"display": True, "text": f"{coin}USDT — Binance", "fontSize": 16, "fontColor": "#ffffff"},
            "legend": {"display": False},
            "scales": {
                "xAxes": [{"display": True, "ticks": {"fontColor": "#aaaaaa", "maxTicksLimit": 6}}],
                "yAxes": [{
                    "display": True,
                    "ticks": {"fontColor": "#aaaaaa", "callback": "function(v){return '$'+v.toFixed(2)}"},
                    "gridLines": {"color": "rgba(255,255,255,0.05)"},
                }],
            },
            "plugins": {
                "datalabels": {"display": False},
            },
        },
    }

    params = {
        "c": json.dumps(chart),
        "width": 600,
        "height": 350,
        "backgroundColor": "#1a1a2e",
        "bkg": "#1a1a2e",
        "devicePixelRatio": 2,
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{QUICKCHART_URL}?{qs}"


def _branded_chart_url(coin: str, klines: list, verdict: str = None) -> str:
    base = _chart_url(coin, klines)
    if not base:
        return None
    # Add footer watermark
    from urllib.parse import quote
    footer = quote(f"⚡ @WhaleAnalyst_bot")
    return f"{base}&footer={footer}"
