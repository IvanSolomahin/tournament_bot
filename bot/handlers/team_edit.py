from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..db.repo import Repo
from ..models import TeamStatus
from ..states import TitleEdit

router = Router(name="team_edit")

EDITABLE_STATUSES = {TeamStatus.PENDING_CONFIRMATION.value, TeamStatus.REGISTERED.value}


@router.message(Command("rename_team"))
async def start_rename(message: Message, state: FSMContext, repo: Repo) -> None:
    team = await repo.get_team_by_member_telegram_id(message.from_user.id)
    if team is None:
        await message.answer("Вы не привязаны ни к одной команде.")
        return
    if team["status"] not in EDITABLE_STATUSES:
        await message.answer(
            "Изменение названия команды больше не доступно: заявка уже распределена "
            "в основной список или вейтлист."
        )
        return
    await state.set_state(TitleEdit.new_title)
    await state.update_data(team_id=team["id"])
    await message.answer(f"Текущее название: «{team['title']}». Введите новое название команды:")


@router.message(TitleEdit.new_title)
async def process_rename(message: Message, state: FSMContext, repo: Repo) -> None:
    data = await state.get_data()
    team_id = data["team_id"]
    team = await repo.get_team(team_id)
    if team is None or team["status"] not in EDITABLE_STATUSES:
        await state.clear()
        await message.answer(
            "Изменение названия команды больше не доступно: заявка уже распределена."
        )
        return

    new_title = message.text.strip()
    if not new_title:
        await message.answer("Название не может быть пустым. Попробуйте снова:")
        return

    await repo.update_team_title(team_id, new_title)
    await repo.log_action(team_id, message.from_user.id, f"title_changed:{new_title}")
    await state.clear()
    await message.answer(f"Название команды обновлено: «{new_title}».")
