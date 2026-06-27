from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.markdown import hbold

from ..db.repo import Repo, normalize_username
from ..services import notifications
from ..services.status_engine import StatusEngine

router = Router(name="confirmation")


@router.callback_query(lambda c: c.data and c.data.startswith("confirm_member:"))
async def handle_confirm_member(
    callback: CallbackQuery, repo: Repo, status_engine: StatusEngine
) -> None:
    team_id = int(callback.data.split(":", 1)[1])
    username = normalize_username(callback.from_user.username or "")
    pending_member = await repo.get_unconfirmed_member_by_username(username)

    if pending_member is None or pending_member["team_id"] != team_id:
        await callback.answer("Это приглашение уже неактуально.", show_alert=True)
        return

    await repo.confirm_member(pending_member["id"], callback.from_user.id)
    await repo.log_action(team_id, callback.from_user.id, "member_confirmed")

    completed = await status_engine.try_complete_registration(team_id)
    team = await repo.get_team(team_id)

    await callback.message.edit_text(
        f"Участие в команде {hbold(team['title'])} подтверждено."
    )
    if completed:
        await callback.message.answer(
            "Оба участника подтвердили участие. Заявка зарегистрирована и передана организаторам."
        )
        await notifications.notify_team(
            callback.bot,
            repo,
            team_id,
            f"Второй участник подтвердил участие. Команда «{team['title']}» "
            f"зарегистрирована и передана организаторам.",
            exclude_telegram_id=callback.from_user.id,
        )
    await callback.answer()
