from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hbold

from ..db.repo import Repo
from ..services import notifications
from ..services.status_engine import StatusEngine

router = Router(name="participation")


@router.callback_query(F.data.startswith("confirm_participation:"))
async def handle_confirm_participation(
    callback: CallbackQuery, repo: Repo, status_engine: StatusEngine
) -> None:
    team_id = int(callback.data.split(":", 1)[1])
    member = await repo.get_member_by_telegram_id(callback.from_user.id)
    if member is None or member["team_id"] != team_id:
        await callback.answer("Это действие недоступно.", show_alert=True)
        return

    ok = await status_engine.confirm_participation(team_id, callback.from_user.id)
    if not ok:
        await callback.answer(
            "Подтверждение участия недоступно для текущего статуса команды.",
            show_alert=True,
        )
        return

    team = await repo.get_team(team_id)
    await callback.message.edit_text(
        f"Участие команды {hbold(team['title'])} в турнире подтверждено."
    )
    await notifications.notify_team(
        callback.bot,
        repo,
        team_id,
        f"Напарник подтвердил участие команды «{team['title']}» в турнире.",
        exclude_telegram_id=callback.from_user.id,
    )
    await callback.answer()
