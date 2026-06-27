from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...config import Config
from ...db.repo import Repo
from ...models import TeamStatus
from ...services import notifications
from ...states import BroadcastFlow
from ..status import STATUS_LABELS

router = Router(name="admin_broadcast")

NO_ACCESS = "У вас нет доступа к этой команде."


@router.message(Command("admin_org_message"))
async def start_org_message(message: Message, state: FSMContext, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        await message.answer(NO_ACCESS)
        return
    await state.set_state(BroadcastFlow.message_text)
    await state.update_data(target_type="all")
    await message.answer(
        "Введите текст организационного сообщения для отправки всем участникам:"
    )


@router.message(Command("admin_remind"))
async def show_remind_menu(message: Message, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        await message.answer(NO_ACCESS)
        return
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Не завершили регистрацию", callback_data="remind:registration")
    )
    builder.row(
        InlineKeyboardButton(text="Не подтвердили участие", callback_data="remind:participation")
    )
    builder.row(
        InlineKeyboardButton(text="Не отправили оплату", callback_data="remind:payment")
    )
    builder.row(
        InlineKeyboardButton(text="Не прошли check-in (день 1)", callback_data="remind:checkin1")
    )
    builder.row(
        InlineKeyboardButton(text="Не прошли check-in (день 2)", callback_data="remind:checkin2")
    )
    await message.answer(
        "FR-5.9.3: выберите этап, по которому нужно напомнить участникам, "
        "не выполнившим текущее условие:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("remind:"))
async def trigger_reminder(callback: CallbackQuery, repo: Repo, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    stage = callback.data.split(":", 1)[1]
    if stage == "registration":
        count = await notifications.remind_incomplete_registration(callback.bot, repo)
    elif stage == "participation":
        count = await notifications.remind_unconfirmed_participation(callback.bot, repo)
    elif stage == "payment":
        count = await notifications.remind_missing_payment(callback.bot, repo)
    elif stage == "checkin1":
        count = await notifications.remind_missing_checkin(callback.bot, repo, 1)
    else:
        count = await notifications.remind_missing_checkin(callback.bot, repo, 2)
    await callback.answer(f"Напоминания отправлены: {count}", show_alert=True)


@router.message(Command("admin_broadcast"))
async def start_broadcast(message: Message, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        await message.answer(NO_ACCESS)
        return
    builder = InlineKeyboardBuilder()
    for status in TeamStatus:
        builder.row(
            InlineKeyboardButton(
                text=STATUS_LABELS.get(status.value, status.value),
                callback_data=f"broadcast_status:{status.value}",
            )
        )
    await message.answer(
        "Выберите группу команд по статусу заявки для рассылки:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("broadcast_status:"))
async def choose_status_target(
    callback: CallbackQuery, state: FSMContext, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    status = callback.data.split(":", 1)[1]
    await state.set_state(BroadcastFlow.message_text)
    await state.update_data(target_type="status", target_value=status)
    await callback.message.edit_text(
        f"Группа: {STATUS_LABELS.get(status, status)}.\nВведите текст сообщения для отправки:"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("broadcast_team:"))
async def choose_team_target(
    callback: CallbackQuery, state: FSMContext, repo: Repo, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    _, team_id_str, back_page_str = callback.data.split(":", 2)
    team_id = int(team_id_str)
    team = await repo.get_team(team_id)
    if team is None:
        await callback.answer("Команда не найдена.", show_alert=True)
        return
    await state.set_state(BroadcastFlow.message_text)
    await state.update_data(
        target_type="team", target_value=team_id, back_page=int(back_page_str)
    )
    await callback.message.edit_text(
        f"Команда: «{team['title']}».\nВведите текст сообщения для отправки:"
    )
    await callback.answer()


@router.message(BroadcastFlow.message_text)
async def send_broadcast(message: Message, state: FSMContext, repo: Repo) -> None:
    data = await state.get_data()
    text = message.text.strip()
    if not text:
        await message.answer("Текст сообщения не может быть пустым. Попробуйте снова:")
        return

    if data["target_type"] == "team":
        count = await notifications.send_text_to_team(
            message.bot, repo, data["target_value"], text
        )
    elif data["target_type"] == "all":
        count = await notifications.send_text_to_all(message.bot, repo, text)
    else:
        count = await notifications.send_text_to_status_group(
            message.bot, repo, data["target_value"], text
        )

    await state.clear()
    await message.answer(f"Сообщение отправлено {count} участникам.")
