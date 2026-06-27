from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import load_config
from .db.database import Database
from .db.repo import Repo
from .handlers import get_root_router
from .services.reminders import build_scheduler
from .services.status_engine import StatusEngine


async def run() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()
    db = Database(config.db_path)
    db.init_schema()
    repo = Repo(db)
    status_engine = StatusEngine(repo)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["config"] = config
    dp["db"] = db
    dp["repo"] = repo
    dp["status_engine"] = status_engine
    dp.include_router(get_root_router())

    scheduler = build_scheduler(bot, repo, config)
    scheduler.start()

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        db.close()


def main() -> None:
    asyncio.run(run())
