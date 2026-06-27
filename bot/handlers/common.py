from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..config import Config

router = Router(name="common")

PARTICIPANT_HELP = (
    "Доступные команды:\n"
    "/create_team — создать заявку команды\n"
    "/status — статус вашей заявки\n"
    "/rename_team — изменить название команды (до распределения)\n"
    "/checkin — подтвердить присутствие в день турнира\n"
    "/cancel — отменить текущее действие\n"
    "/help — эта справка\n\n"
    "Подтверждение оплаты отправляется фотографией прямо в этот чат."
)

ADMIN_HELP = (
    "\n\nКоманды организатора:\n"
    "/admin_applications — список заявок и карточки команд\n"
    "/admin_broadcast — рассылка команде/группе по статусу\n"
    "/admin_org_message — организационное сообщение всем участникам\n"
    "/admin_remind — напоминания по невыполненному этапу\n"
    "/admin_export — выгрузка заявок в XLSX"
)


@router.message(Command("help"))
async def handle_help(message: Message, config: Config) -> None:
    text = PARTICIPANT_HELP
    if config.is_admin(message.from_user.id):
        text += ADMIN_HELP
    await message.answer(text)


@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        await message.answer("Нет активного действия для отмены.")
        return
    await state.clear()
    await message.answer("Действие отменено.")
