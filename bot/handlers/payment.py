from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from ..db.repo import Repo
from ..models import TeamStatus
from ..services import notifications
from ..services.status_engine import StatusEngine

router = Router(name="payment")


@router.message(F.photo)
async def handle_payment_photo(
    message: Message, repo: Repo, status_engine: StatusEngine
) -> None:
    member = await repo.get_member_by_telegram_id(message.from_user.id)
    if member is None:
        return  # not a registered, confirmed team member — ignore stray photos

    file_id = message.photo[-1].file_id
    new_status = await status_engine.submit_payment(
        member["team_id"], member["id"], file_id, message.from_user.id
    )

    if new_status is None:
        await message.answer(
            "Отправка подтверждения оплаты сейчас недоступна для вашей команды."
        )
        return

    team = await repo.get_team(member["team_id"])

    if new_status == TeamStatus.PAYMENT_CONFIRMED.value:
        await message.answer(
            "Подтверждение оплаты получено. Оплата от обоих участников получена — "
            "оплата команды подтверждена."
        )
        await notifications.notify_team(
            message.bot,
            repo,
            member["team_id"],
            f"Оплата от обоих участников получена. Оплата команды «{team['title']}» подтверждена.",
            exclude_telegram_id=message.from_user.id,
        )
    else:
        await message.answer(
            "Подтверждение оплаты получено. Ждём оплату от второго участника."
        )
        await notifications.notify_team(
            message.bot,
            repo,
            member["team_id"],
            f"Напарник отправил подтверждение оплаты по команде «{team['title']}». "
            f"Осталось отправить вашу часть — пришлите фото подтверждения оплаты.",
            exclude_telegram_id=message.from_user.id,
        )
