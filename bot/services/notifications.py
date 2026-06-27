from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramNetworkError, TelegramRetryAfter

from ..db.repo import Repo
from ..models import TeamStatus

logger = logging.getLogger(__name__)

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.0


async def safe_send(bot: Bot, telegram_id: int, text: str, **kwargs) -> None:
    """Send a message, retrying on transient network errors / flood control.
    Gives up silently on permanent failures (user blocked the bot, bad chat, etc.)."""
    for attempt in range(RETRY_ATTEMPTS):
        try:
            await bot.send_message(telegram_id, text, **kwargs)
            return
        except TelegramForbiddenError:
            logger.warning("User %s blocked the bot or chat unavailable", telegram_id)
            return
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except TelegramNetworkError:
            if attempt == RETRY_ATTEMPTS - 1:
                logger.warning(
                    "Failed to send message to %s after %d attempts",
                    telegram_id,
                    RETRY_ATTEMPTS,
                    exc_info=True,
                )
                return
            await asyncio.sleep(RETRY_BACKOFF_SECONDS * (2 ** attempt))
        except Exception:
            logger.warning("Failed to send message to %s", telegram_id, exc_info=True)
            return


async def notify_team(
    bot: Bot,
    repo: Repo,
    team_id: int,
    text: str,
    exclude_telegram_id: int | None = None,
    reply_markup=None,
) -> int:
    """Notify all confirmed members of a team, optionally skipping one (the actor)."""
    members = await repo.get_members(team_id)
    count = 0
    for m in members:
        if not m["telegram_id"] or m["telegram_id"] == exclude_telegram_id:
            continue
        await safe_send(bot, m["telegram_id"], text, reply_markup=reply_markup)
        count += 1
    return count


ALL_ACTIVE_STATUSES = [
    TeamStatus.REGISTERED.value,
    TeamStatus.MAIN_LIST.value,
    TeamStatus.WAITLIST.value,
    TeamStatus.PARTICIPATION_CONFIRMED.value,
    TeamStatus.PARTIALLY_PAID.value,
    TeamStatus.PAYMENT_CONFIRMED.value,
]


async def send_text_to_all(bot: Bot, repo: Repo, text: str) -> int:
    """UC-13 / FR-5.9.2: admin sends a custom org message to all confirmed members."""
    members = await repo.list_members_by_status(ALL_ACTIVE_STATUSES)
    for m in members:
        await safe_send(bot, m["telegram_id"], text)
    return len(members)


async def send_text_to_team(bot: Bot, repo: Repo, team_id: int, text: str) -> int:
    """UC-16: admin sends arbitrary message to one team."""
    members = await repo.get_members(team_id)
    count = 0
    for m in members:
        if m["telegram_id"]:
            await safe_send(bot, m["telegram_id"], text)
            count += 1
    return count


async def send_text_to_status_group(
    bot: Bot, repo: Repo, status: str, text: str
) -> int:
    """UC-16 / FR-5.12.2-5.12.3: admin sends arbitrary message to a status group."""
    members = await repo.list_members_by_status([status])
    for m in members:
        await safe_send(bot, m["telegram_id"], text)
    return len(members)


async def remind_incomplete_registration(bot: Bot, repo: Repo) -> int:
    """FR-5.11.1: remind team creators whose teammate hasn't confirmed yet."""
    creators = await repo.list_pending_creators()
    for m in creators:
        await safe_send(
            bot,
            m["telegram_id"],
            f"Напоминание: команда «{m['team_title']}» ещё не зарегистрирована — "
            f"второй участник не подтвердил участие.",
        )
    return len(creators)


async def remind_unconfirmed_participation(bot: Bot, repo: Repo) -> int:
    """FR-5.11.2: remind members of main_list teams that haven't confirmed participation."""
    members = await repo.list_members_by_status([TeamStatus.MAIN_LIST.value])
    for m in members:
        await safe_send(
            bot,
            m["telegram_id"],
            f"Напоминание: подтвердите участие команды «{m['team_title']}» в турнире.",
        )
    return len(members)


async def remind_missing_payment(bot: Bot, repo: Repo) -> int:
    """FR-5.11.3: remind members who personally haven't sent payment confirmation."""
    members = await repo.list_members_by_status(
        [
            TeamStatus.MAIN_LIST.value,
            TeamStatus.PARTICIPATION_CONFIRMED.value,
            TeamStatus.PARTIALLY_PAID.value,
        ]
    )
    count = 0
    for m in members:
        if m["payment_confirmed_at"] is None:
            await safe_send(
                bot,
                m["telegram_id"],
                f"Напоминание: отправьте подтверждение оплаты для команды «{m['team_title']}».",
            )
            count += 1
    return count


async def remind_missing_checkin(bot: Bot, repo: Repo, day: int) -> int:
    """FR-5.11.4: remind members who haven't checked in on the given tournament day."""
    members = await repo.list_members_by_status(
        [
            TeamStatus.PARTICIPATION_CONFIRMED.value,
            TeamStatus.PARTIALLY_PAID.value,
            TeamStatus.PAYMENT_CONFIRMED.value,
        ]
    )
    column = "checkin_day1_at" if day == 1 else "checkin_day2_at"
    count = 0
    for m in members:
        if m[column] is None:
            await safe_send(
                bot,
                m["telegram_id"],
                f"Напоминание: подтвердите присутствие в день {day} турнира (/checkin), "
                f"команда «{m['team_title']}».",
            )
            count += 1
    return count
