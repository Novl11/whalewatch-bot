"""
UserBot — автоматический поиск крипто-групп и продвижение бота.
Запускается отдельно от основного бота.

Использование:
  python -m userbot.runner

Перед запуском установи:
  USERBOT_API_ID, USERBOT_API_HASH, USERBOT_PHONE в .env
"""
import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from telethon import TelegramClient, functions, types
from telethon.errors import (
    FloodWaitError,
    UserAlreadyParticipantError,
    InviteHashInvalidError,
    InviteHashExpiredError,
    UserBannedInChannelError,
)
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty

from userbot.config import (
    API_HASH,
    API_ID,
    PHONE,
    ACTION_DELAY_MIN,
    ACTION_DELAY_MAX,
    FIRST_MSG_DELAY_MIN,
    FIRST_MSG_DELAY_MAX,
    GROUP_COOLDOWN_HOURS,
    MAX_JOINS_PER_HOUR,
    MAX_MSGS_PER_DAY,
    SEARCH_KEYWORDS,
)
from userbot.messages import random_promo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("userbot.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("userbot")

SESSION_DIR = Path(__file__).parent / "sessions"
STATE_FILE = Path(__file__).parent / "state.json"
SESSION_DIR.mkdir(exist_ok=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"joined": [], "messaged": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def random_delay(min_s: int, max_s: int):
    return random.uniform(min_s, max_s)


async def collect_groups(client: TelegramClient) -> list[dict]:
    """Search for public crypto groups via global search."""
    found = {}

    for keyword in SEARCH_KEYWORDS:
        log.info(f"Searching: '{keyword}'")
        try:
            result = await client(
                SearchGlobalRequest(
                    q=keyword,
                    filter=None,
                    min_date=None,
                    max_date=None,
                    offset_rate=0,
                    offset_peer=InputPeerEmpty(),
                    offset_id=0,
                    limit=100,
                )
            )
            for msg in result.messages:
                if not msg.peer_id:
                    continue
                peer_id = msg.peer_id
                chat_id = None
                if isinstance(peer_id, types.PeerChannel):
                    chat_id = -1000000000000 - peer_id.channel_id
                elif isinstance(peer_id, types.PeerChat):
                    chat_id = -peer_id.chat_id
                else:
                    continue

                try:
                    entity = await client.get_entity(peer_id)
                except Exception:
                    continue

                if not isinstance(entity, (types.Channel, types.Chat)):
                    continue
                if entity.broadcast:
                    continue  # skip channels, only groups
                if getattr(entity, "participants_count", 0) or 0 < 50:
                    continue  # skip tiny groups

                username = getattr(entity, "username", None)
                title = getattr(entity, "title", "Unnamed")

                key = entity.id
                if key not in found:
                    found[key] = {
                        "id": entity.id,
                        "title": title,
                        "username": username,
                        "members": getattr(entity, "participants_count", 0) or 0,
                    }
                    log.info(f"  Found: {title} ({username or 'no username'}) — {found[key]['members']} members")

            await asyncio.sleep(random_delay(2, 5))
        except FloodWaitError as e:
            log.warning(f"Flood wait {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            log.warning(f"Search error: {e}")

    groups = sorted(found.values(), key=lambda g: g["members"], reverse=True)
    log.info(f"Total unique groups found: {len(groups)}")
    return groups


async def try_join(client: TelegramClient, group: dict) -> bool:
    """Try to join a group."""
    username = group.get("username")
    group_id = group["id"]

    if not username:
        log.info(f"  Skip {group['title']}: no username")
        return False

    try:
        entity = await client.get_entity(username)
        if isinstance(entity, (types.Channel, types.Chat)):
            await client(functions.channels.JoinChannelRequest(channel=entity))
            log.info(f"  ✅ Joined: {group['title']} (@{username})")
            return True
    except UserAlreadyParticipantError:
        log.info(f"  Already in: {group['title']}")
        return False
    except FloodWaitError as e:
        log.warning(f"  Flood: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 5)
    except UserBannedInChannelError:
        log.warning(f"  Banned from: {group['title']}")
    except Exception as e:
        log.warning(f"  Join error {group['title']}: {e}")

    return False


async def try_message(client: TelegramClient, group: dict) -> bool:
    """Send a promo message to a group."""
    username = group.get("username")
    group_id = group["id"]

    try:
        entity = await client.get_entity(username or group_id)
        text = random_promo()
        await client.send_message(entity, text)
        log.info(f"  📤 Messaged: {group['title']}")
        return True
    except FloodWaitError as e:
        log.warning(f"  Flood: wait {e.seconds}s")
        await asyncio.sleep(e.seconds + 5)
    except Exception as e:
        log.warning(f"  Message error {group['title']}: {e}")

    return False


async def main():
    if not all([API_ID, API_HASH, PHONE]):
        log.error("Set USERBOT_API_ID, USERBOT_API_HASH, USERBOT_PHONE in .env")
        return

    session_path = str(SESSION_DIR / "user")
    client = TelegramClient(session_path, API_ID, API_HASH)

    await client.start(phone=PHONE)
    log.info(f"Logged in as: {(await client.get_me()).first_name}")

    state = load_state()
    joined = {g["id"] for g in state.get("joined", [])}
    messaged = {g["id"] for g in state.get("messaged", [])}

    log.info("Scanning for crypto groups...")
    groups = await collect_groups(client)

    # Filter out already joined
    new_groups = [g for g in groups if g["id"] not in joined]
    if not new_groups:
        log.info("No new groups found. Refreshing state.")
        new_groups = groups

    joins_today = 0
    msgs_today = 0
    hour_start = time.time()

    for idx, group in enumerate(new_groups):
        now_hour = time.time()
        if now_hour - hour_start > 3600:
            joins_today = 0
            hour_start = now_hour

        if joins_today >= MAX_JOINS_PER_HOUR:
            cooldown = 3600 - (now_hour - hour_start)
            log.info(f"Join limit for this hour, waiting {cooldown:.0f}s")
            await asyncio.sleep(cooldown)

        # Join
        ok = await try_join(client, group)
        if ok:
            joins_today += 1
            state.setdefault("joined", []).append({
                "id": group["id"],
                "title": group["title"],
                "time": datetime.utcnow().isoformat(),
            })
            save_state(state)
            joined.add(group["id"])

        delay = random_delay(ACTION_DELAY_MIN, ACTION_DELAY_MAX)
        log.info(f"  Waiting {delay:.0f}s...")
        await asyncio.sleep(delay)

        # Message (only if just joined and not messaged recently)
        if ok and group["id"] not in messaged and msgs_today < MAX_MSGS_PER_DAY:
            wait = random_delay(FIRST_MSG_DELAY_MIN, FIRST_MSG_DELAY_MAX)
            log.info(f"  Waiting {wait:.0f}s before first message...")
            await asyncio.sleep(wait)

            ok_msg = await try_message(client, group)
            if ok_msg:
                msgs_today += 1
                state.setdefault("messaged", []).append({
                    "id": group["id"],
                    "title": group["title"],
                    "time": datetime.utcnow().isoformat(),
                })
                save_state(state)
                messaged.add(group["id"])

        if msgs_today >= MAX_MSGS_PER_DAY:
            log.info("Daily message limit reached.")
            break

    log.info(f"Done. Stats: joins={joins_today}, messages={msgs_today}")

    # Cleanup old state
    cutoff = datetime.utcnow() - timedelta(hours=GROUP_COOLDOWN_HOURS)
    for key in ["joined", "messaged"]:
        state[key] = [e for e in state.get(key, []) if datetime.fromisoformat(e["time"]) > cutoff]
    save_state(state)

    await client.disconnect()
    log.info("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
