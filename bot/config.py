from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    return {int(x.strip()) for x in raw.split(",") if x.strip()}


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    channel_link: str
    chat_link: str
    db_path: str
    tournament_day1: date
    tournament_day2: date

    def is_admin(self, telegram_id: int) -> bool:
        return telegram_id in self.admin_ids


def load_config() -> Config:
    return Config(
        bot_token=os.environ["BOT_TOKEN"],
        admin_ids=_parse_admin_ids(os.environ.get("ADMIN_IDS", "")),
        channel_link=os.environ.get("CHANNEL_LINK", ""),
        chat_link=os.environ.get("CHAT_LINK", ""),
        db_path=os.environ.get("DB_PATH", "bot.db"),
        tournament_day1=date.fromisoformat(os.environ["TOURNAMENT_DAY1"]),
        tournament_day2=date.fromisoformat(os.environ["TOURNAMENT_DAY2"]),
    )
