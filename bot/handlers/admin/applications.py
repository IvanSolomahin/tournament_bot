from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from ...config import Config
from ...db.repo import Repo
from ...keyboards import confirm_participation_kb
from ...models import TeamStatus
from ...services import notifications
from ...services.status_engine import StatusEngine
from ...handlers.status import STATUS_LABELS

router = Router(name="admin_applications")

NO_ACCESS = "У вас нет доступа к этой команде."
PAGE_SIZE = 8


def _teams_list_kb(teams, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    total_pages = max(1, (len(teams) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    page_teams = teams[start : start + PAGE_SIZE]

    for team in page_teams:
        label = f"{team['title']} ({STATUS_LABELS.get(team['status'], team['status'])})"
        builder.row(
            InlineKeyboardButton(
                text=label, callback_data=f"admin_card:{team['id']}:{page}"
            )
        )

    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    text="« Назад", callback_data=f"admin_applications_page:{page - 1}"
                )
            )
        nav_row.append(
            InlineKeyboardButton(
                text=f"{page + 1}/{total_pages}", callback_data="admin_noop"
            )
        )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="Далее »", callback_data=f"admin_applications_page:{page + 1}"
                )
            )
        builder.row(*nav_row)

    return builder.as_markup()


def _card_kb(
    team_id: int, status: str, back_page: int, has_receipts: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if status == TeamStatus.REGISTERED.value:
        builder.row(
            InlineKeyboardButton(
                text="В основной список",
                callback_data=f"admin_set_status:{team_id}:{TeamStatus.MAIN_LIST.value}:{back_page}",
            ),
            InlineKeyboardButton(
                text="В вейтлист",
                callback_data=f"admin_set_status:{team_id}:{TeamStatus.WAITLIST.value}:{back_page}",
            ),
        )
    if has_receipts:
        builder.row(
            InlineKeyboardButton(
                text="Показать чеки оплаты",
                callback_data=f"admin_show_receipts:{team_id}:{back_page}",
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="Написать команде",
            callback_data=f"broadcast_team:{team_id}:{back_page}",
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="« Назад к списку",
            callback_data=f"admin_applications_page:{back_page}",
        )
    )
    return builder.as_markup()


async def _render_card(team_id: int, repo: Repo) -> str:
    team = await repo.get_team(team_id)
    members = await repo.get_members(team_id)
    log = await repo.get_action_log(team_id)

    lines = [
        f"Команда: {team['title']}",
        f"Статус заявки: {STATUS_LABELS.get(team['status'], team['status'])}",
        "",
        "Участники:",
    ]
    for m in members:
        payment = "оплата получена" if m["payment_confirmed_at"] else "оплата не получена"
        lines.append(
            f"  {m['slot']}. {m['name']} | контакт: {m['contact']} | клуб: {m['club'] or '-'} | "
            f"достижения: {m['achievements'] or '-'} | {payment}"
        )

    lines.append("")
    lines.append("История действий:")
    if not log:
        lines.append("  нет записей")
    else:
        for entry in log:
            lines.append(f"  {entry['created_at']} — {entry['action']}")

    return "\n".join(lines)


@router.message(Command("admin_applications"))
async def list_applications(message: Message, repo: Repo, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        await message.answer(NO_ACCESS)
        return
    teams = await repo.list_teams()
    if not teams:
        await message.answer("Заявок пока нет.")
        return
    await message.answer("Заявки команд:", reply_markup=_teams_list_kb(teams, page=0))


@router.callback_query(F.data == "admin_noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data.startswith("admin_applications_page:"))
async def show_page(callback: CallbackQuery, repo: Repo, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    page = int(callback.data.split(":", 1)[1])
    teams = await repo.list_teams()
    await callback.message.edit_text(
        "Заявки команд:", reply_markup=_teams_list_kb(teams, page=page)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_card:"))
async def show_card(callback: CallbackQuery, repo: Repo, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    _, team_id_str, back_page_str = callback.data.split(":", 2)
    team_id = int(team_id_str)
    back_page = int(back_page_str)
    team = await repo.get_team(team_id)
    if team is None:
        await callback.answer("Команда не найдена.", show_alert=True)
        return
    members = await repo.get_members(team_id)
    has_receipts = any(m["payment_file_id"] for m in members)
    text = await _render_card(team_id, repo)
    await callback.message.edit_text(
        text, reply_markup=_card_kb(team_id, team["status"], back_page, has_receipts)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_show_receipts:"))
async def show_receipts(callback: CallbackQuery, repo: Repo, config: Config) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    _, team_id_str, back_page_str = callback.data.split(":", 2)
    team_id = int(team_id_str)
    members = await repo.get_members(team_id)
    sent = 0
    for m in members:
        if m["payment_file_id"]:
            await callback.message.answer_photo(
                m["payment_file_id"],
                caption=f"Чек оплаты — участник {m['slot']}: {m['name']}",
            )
            sent += 1
    if sent == 0:
        await callback.answer("Чеков пока нет.", show_alert=True)
    else:
        await callback.answer()


@router.callback_query(F.data.startswith("admin_set_status:"))
async def set_status(
    callback: CallbackQuery, repo: Repo, status_engine: StatusEngine, config: Config
) -> None:
    if not config.is_admin(callback.from_user.id):
        await callback.answer(NO_ACCESS, show_alert=True)
        return
    _, team_id_str, status_value, back_page_str = callback.data.split(":", 3)
    team_id = int(team_id_str)
    status = TeamStatus(status_value)
    back_page = int(back_page_str)

    await status_engine.set_list_assignment(team_id, status, callback.from_user.id)

    team = await repo.get_team(team_id)
    if status == TeamStatus.MAIN_LIST:
        await notifications.notify_team(
            callback.bot,
            repo,
            team_id,
            f"Команда «{team['title']}» включена в основной список турнира. "
            f"Подтвердите участие:",
            reply_markup=confirm_participation_kb(team_id),
        )
    elif status == TeamStatus.WAITLIST:
        await notifications.notify_team(
            callback.bot,
            repo,
            team_id,
            f"Команда «{team['title']}» помещена в лист ожидания (вейтлист). "
            f"Мы сообщим, если появится место в основном списке.",
        )

    members = await repo.get_members(team_id)
    has_receipts = any(m["payment_file_id"] for m in members)
    text = await _render_card(team_id, repo)
    await callback.message.edit_text(
        text, reply_markup=_card_kb(team_id, status.value, back_page, has_receipts)
    )
    await callback.answer("Статус обновлён.")
