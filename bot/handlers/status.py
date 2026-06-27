from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..db.repo import Repo
from ..models import TeamStatus

router = Router(name="status")

STATUS_LABELS = {
    TeamStatus.PENDING_CONFIRMATION.value: "ожидает подтверждения участников",
    TeamStatus.REGISTERED.value: "зарегистрирована",
    TeamStatus.MAIN_LIST.value: "основной список",
    TeamStatus.WAITLIST.value: "вейтлист",
    TeamStatus.PARTICIPATION_CONFIRMED.value: "участие подтверждено",
    TeamStatus.PARTIALLY_PAID.value: "частично оплачена",
    TeamStatus.PAYMENT_CONFIRMED.value: "оплата подтверждена",
    TeamStatus.WITHDRAWN.value: "снята",
}


@router.message(Command("status"))
async def handle_status(message: Message, repo: Repo) -> None:
    team = await repo.get_team_by_member_telegram_id(message.from_user.id)
    if team is None:
        await message.answer(
            "Вы пока не привязаны ни к одной команде. Используйте /create_team, чтобы создать заявку."
        )
        return

    members = await repo.get_members(team["id"])
    lines = [
        f"Команда: {team['title']}",
        f"Статус заявки: {STATUS_LABELS.get(team['status'], team['status'])}",
        "",
    ]
    for m in members:
        confirmed = "подтверждён" if m["telegram_id"] else "ожидает подтверждения"
        lines.append(f"Участник {m['slot']}: {m['name']} — {confirmed}")

    await message.answer("\n".join(lines))
