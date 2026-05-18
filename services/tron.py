import asyncio
import aiohttp
import ssl
import certifi
from config import TRONGRID_API_KEY, USDT_WALLET

USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
TRONGRID_API = "https://api.trongrid.io"
_SSL_CTX = ssl.create_default_context(cafile=certifi.where())

_checked_txids: set[str] = set()


async def _fetch(url: str) -> dict | None:
    try:
        headers = {"Accept": "application/json"}
        if TRONGRID_API_KEY:
            headers["TRON-PRO-API-KEY"] = TRONGRID_API_KEY
        connector = aiohttp.TCPConnector(ssl=_SSL_CTX)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


async def check_incoming_usdt(min_amount: float = 9.0, max_amount: float = 11.0) -> list[dict]:
    url = f"{TRONGRID_API}/v1/accounts/{USDT_WALLET}/transactions/trc20?limit=50&only_confirmed=true&contract_address={USDT_CONTRACT}"
    data = await _fetch(url)
    if not data or not isinstance(data, dict):
        return []

    txs = data.get("data", []) if isinstance(data.get("data"), list) else []
    found: list[dict] = []

    for tx in txs:
        tx_id = tx.get("transaction_id", "")
        if tx_id in _checked_txids:
            continue
        _checked_txids.add(tx_id)

        token_info = tx.get("token_info", {})
        decimals = int(token_info.get("decimals", 6))
        symbol = token_info.get("symbol", "")
        if symbol != "USDT":
            continue

        value_str = tx.get("value", "0")
        raw = int(value_str) if value_str else 0
        amount = raw / (10 ** decimals)

        to_addr = tx.get("to", "")
        if to_addr != USDT_WALLET:
            continue

        if min_amount <= amount <= max_amount:
            found.append({
                "tx_id": tx_id,
                "amount": amount,
                "from_addr": tx.get("from", ""),
                "timestamp": tx.get("block_timestamp", 0),
            })

    return found
