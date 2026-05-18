import asyncio, logging, random
from datetime import datetime
from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError, UserAlreadyParticipantError, UserBannedInChannelError
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputPeerEmpty

from auto_promo.config import SEARCH_LIMIT, MIN_GROUP_MEMBERS, SCAN_KEYWORDS, \
    ACTION_DELAY_MIN, ACTION_DELAY_MAX, MAX_JOINS_PER_HOUR
from auto_promo.database import save_group, update_group_status, get_groups_by_status, \
    increment_daily_counter, get_daily_limits

log = logging.getLogger("promo.scanner")


async def collect_groups(client: TelegramClient) -> list[dict]:
    """Глобальный поиск групп по ключевым словам."""
    found = {}
    for keyword in SCAN_KEYWORDS:
        log.info(f"Searching: '{keyword}'")
        try:
            result = await client(SearchGlobalRequest(
                q=keyword,
                filter=None,
                min_date=None, max_date=None,
                offset_rate=0,
                offset_peer=InputPeerEmpty(),
                offset_id=0,
                limit=SEARCH_LIMIT,
            ))
            for msg in result.messages:
                peer_id = msg.peer_id
                if not isinstance(peer_id, (types.PeerChannel, types.PeerChat)):
                    continue

                try:
                    entity = await client.get_entity(peer_id)
                except Exception:
                    continue

                if not isinstance(entity, (types.Channel, types.Chat)):
                    continue
                if getattr(entity, "broadcast", False):
                    continue  # только группы, не каналы
                members = getattr(entity, "participants_count", 0) or 0
                if members < MIN_GROUP_MEMBERS:
                    continue

                key = entity.id
                if key not in found:
                    found[key] = {
                        "chat_id": entity.id,
                        "title": getattr(entity, "title", "Unnamed"),
                        "username": getattr(entity, "username", None),
                        "members": members,
                    }
                    log.info(f"  Found: {entity.title} ({members} members)")

            await asyncio.sleep(random.uniform(2, 5))
        except FloodWaitError as e:
            log.warning(f"FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            log.warning(f"Search error '{keyword}': {e}")

    groups = sorted(found.values(), key=lambda g: g["members"], reverse=True)
    log.info(f"Total unique groups: {len(groups)}")
    return groups


async def try_join(client: TelegramClient, group: dict) -> bool:
    """Вступление в группу."""
    username = group.get("username")
    if not username:
        log.debug(f"  Skip {group['title']}: no username")
        return False

    try:
        entity = await client.get_entity(username)
        await client(functions.channels.JoinChannelRequest(channel=entity))
        log.info(f"  ✅ Joined: {group['title']} (@{username})")
        return True
    except UserAlreadyParticipantError:
        log.info(f"  Already in: {group['title']}")
        return False
    except FloodWaitError as e:
        log.warning(f"  FloodWait: {e.seconds}s, waiting...")
        await asyncio.sleep(e.seconds + 5)
    except UserBannedInChannelError:
        log.warning(f"  Banned: {group['title']}")
    except Exception as e:
        log.warning(f"  Join error {group['title']}: {e}")
    return False


async def scan_and_join(client: TelegramClient):
    """Фаза 1: найти группы → сохранить → вступить."""
    groups = await collect_groups(client)
    for g in groups:
        await save_group(g["chat_id"], g["title"], g["username"], g["members"])

    # Вступаем только в новые группы (status = 'found')
    to_join = await get_groups_by_status("found")
    if not to_join:
        log.info("No new groups to join")
        return

    limits = await get_daily_limits()
    joins_today = limits["joins"]

    for group in to_join[:MAX_JOINS_PER_HOUR]:
        if joins_today >= MAX_JOINS_PER_HOUR:
            log.info("Daily join limit reached")
            break

        ok = await try_join(client, group)
        if ok:
            joins_today += 1
            await update_group_status(group["chat_id"], "joined")
            await increment_daily_counter("joins")

        delay = random.uniform(ACTION_DELAY_MIN, ACTION_DELAY_MAX)
        log.info(f"  Next action in {delay:.0f}s...")
        await asyncio.sleep(delay)
