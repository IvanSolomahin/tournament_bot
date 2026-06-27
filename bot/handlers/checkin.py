from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..config import Config
from ..db.repo import Repo
from ..keyboards import checkin_kb

router = Router(name="checkin")


def _current_tournament_day(config: Config) -> int | None:
    today = date.today()
    if today == config.tournament_day1:
        return 1
    if today == config.tournament_day2:
        return 2
    return None


@router.message(Command("checkin"))
async def handle_checkin_command(message: Message, repo: Repo, config: Config) -> None:
    member = await repo.get_member_by_telegram_id(message.from_user.id)
    if member is None:
        await message.answer("Вы не привязаны ни к одной команде.")
        return

    day = _current_tournament_day(config)
    if day is None:
        await message.answer("Сегодня не день check-in турнира.")
        return

    already_at = member["checkin_day1_at"] if day == 1 else member["checkin_day2_at"]
    if already_at:
        await message.answer(f"Присутствие в день {day} уже подтверждено.")
        return

    await message.answer(
        f"Подтвердите присутствие в день {day} турнира:", reply_markup=checkin_kb(day)
    )


@router.callback_query(F.data.startswith("checkin:"))
async def handle_checkin_confirm(callback: CallbackQuery, repo: Repo, config: Config) -> None:
    day = int(callback.data.split(":", 1)[1])
    member = await repo.get_member_by_telegram_id(callback.from_user.id)
    if member is None:
        await callback.answer("Вы не привязаны ни к одной команде.", show_alert=True)
        return

    current_day = _current_tournament_day(config)
    if current_day != day:
        await callback.answer("Это подтверждение больше не актуально.", show_alert=True)
        return

    await repo.record_checkin(member["id"], day)
    await repo.log_action(member["team_id"], callback.from_user.id, f"checkin_day{day}")
    await callback.message.edit_text(f"Присутствие в день {day} подтверждено.")
    await callback.answer()
