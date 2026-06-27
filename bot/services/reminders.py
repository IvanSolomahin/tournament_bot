from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import Config
from ..db.repo import Repo
from ..keyboards import checkin_kb
from ..models import TeamStatus
from . import notifications

logger = logging.getLogger(__name__)


async def _daily_sweep(bot: Bot, repo: Repo) -> None:
    """FR-5.11.1-5.11.3: remind only those who haven't completed the relevant action."""
    await notifications.remind_incomplete_registration(bot, repo)
    await notifications.remind_unconfirmed_participation(bot, repo)
    await notifications.remind_missing_payment(bot, repo)


async def _send_checkin_prompt(bot: Bot, repo: Repo, day: int) -> None:
    """UC-14/UC-15: proactively prompt eligible members to check in on tournament day."""
    members = await repo.list_members_by_status(
        [
            TeamStatus.PARTICIPATION_CONFIRMED.value,
            TeamStatus.PARTIALLY_PAID.value,
            TeamStatus.PAYMENT_CONFIRMED.value,
        ]
    )
    column = "checkin_day1_at" if day == 1 else "checkin_day2_at"
    for m in members:
        if m[column] is None:
            try:
                await bot.send_message(
                    m["telegram_id"],
                    f"Подтвердите присутствие в день {day} турнира:",
                    reply_markup=checkin_kb(day),
                )
            except Exception:
                logger.warning("Failed to send checkin prompt to %s", m["telegram_id"], exc_info=True)


async def _remind_checkin(bot: Bot, repo: Repo, day: int) -> None:
    await notifications.remind_missing_checkin(bot, repo, day)


def build_scheduler(bot: Bot, repo: Repo, config: Config) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    now = datetime.now()

    scheduler.add_job(
        _daily_sweep,
        trigger=IntervalTrigger(hours=24),
        args=[bot, repo],
        id="daily_sweep",
        next_run_time=now + timedelta(minutes=1),
    )

    for tournament_day, day_number in (
        (config.tournament_day1, 1),
        (config.tournament_day2, 2),
    ):
        prompt_at = datetime.combine(tournament_day, time(9, 0))
        remind_at = datetime.combine(tournament_day, time(15, 0))
        if prompt_at > now:
            scheduler.add_job(
                _send_checkin_prompt,
                trigger=DateTrigger(run_date=prompt_at),
                args=[bot, repo, day_number],
                id=f"checkin_prompt_day{day_number}",
            )
        if remind_at > now:
            scheduler.add_job(
                _remind_checkin,
                trigger=DateTrigger(run_date=remind_at),
                args=[bot, repo, day_number],
                id=f"checkin_remind_day{day_number}",
            )

    return scheduler
