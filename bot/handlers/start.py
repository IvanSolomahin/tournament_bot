from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ..db.repo import Repo, normalize_username
from ..keyboards import confirm_membership_kb

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, repo: Repo) -> None:
    await repo.activate_user(message.from_user.id, message.from_user.username)

    existing_team = await repo.get_team_by_member_telegram_id(message.from_user.id)
    if existing_team is not None:
        await message.answer(
            "Вы уже привязаны к команде. Используйте /status для просмотра заявки."
        )
        return

    username = normalize_username(message.from_user.username or "")
    pending_member = (
        await repo.get_unconfirmed_member_by_username(username) if username else None
    )
    if pending_member is not None:
        team = await repo.get_team(pending_member["team_id"])
        await message.answer(
            f"Вас указали как второго участника команды «{team['title']}». "
            f"Подтвердите участие, чтобы завершить регистрацию:",
            reply_markup=confirm_membership_kb(team["id"]),
        )
        return

    await message.answer(
        "Привет! Это бот регистрации команд на турнир по парламентским дебатам.\n\n"
        "Чтобы создать заявку команды, используйте /create_team.\n"
        "Чтобы посмотреть статус заявки — /status.\n"
        "Список всех команд — /help."
    )
