from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from ..db.repo import Repo, normalize_username
from ..keyboards import SKIP, skip_hint
from ..states import TeamCreation

router = Router(name="registration")


def _clean_optional(text: str) -> str | None:
    return None if text.strip() == SKIP else text.strip()


@router.message(Command("create_team"))
async def start_team_creation(message: Message, state: FSMContext, repo: Repo) -> None:
    existing_team = await repo.get_team_by_member_telegram_id(message.from_user.id)
    if existing_team is not None:
        await message.answer(
            "Вы уже состоите в заявке команды. Используйте /status для просмотра."
        )
        return
    await state.set_state(TeamCreation.title)
    await message.answer("Введите название команды:")


@router.message(TeamCreation.title)
async def process_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if not title:
        await message.answer("Название команды не может быть пустым. Попробуйте снова:")
        return
    await state.update_data(title=title)
    await state.set_state(TeamCreation.member1_name)
    await message.answer("Имя первого участника (вас):")


@router.message(TeamCreation.member1_name)
async def process_member1_name(message: Message, state: FSMContext) -> None:
    await state.update_data(member1_name=message.text.strip())
    await state.set_state(TeamCreation.member1_contact)
    await message.answer("Контакт первого участника (телефон/телеграм):")


@router.message(TeamCreation.member1_contact)
async def process_member1_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(member1_contact=message.text.strip())
    await state.set_state(TeamCreation.member1_club)
    await message.answer("Клуб первого участника:" + skip_hint())


@router.message(TeamCreation.member1_club)
async def process_member1_club(message: Message, state: FSMContext) -> None:
    await state.update_data(member1_club=_clean_optional(message.text))
    await state.set_state(TeamCreation.member1_achievements)
    await message.answer("Достижения первого участника:" + skip_hint())


@router.message(TeamCreation.member1_achievements)
async def process_member1_achievements(message: Message, state: FSMContext) -> None:
    await state.update_data(member1_achievements=_clean_optional(message.text))
    await state.set_state(TeamCreation.member2_name)
    await message.answer("Имя второго участника:")


@router.message(TeamCreation.member2_name)
async def process_member2_name(message: Message, state: FSMContext) -> None:
    await state.update_data(member2_name=message.text.strip())
    await state.set_state(TeamCreation.member2_contact)
    await message.answer("Контакт второго участника:")


@router.message(TeamCreation.member2_contact)
async def process_member2_contact(message: Message, state: FSMContext) -> None:
    await state.update_data(member2_contact=message.text.strip())
    await state.set_state(TeamCreation.member2_club)
    await message.answer("Клуб второго участника:" + skip_hint())


@router.message(TeamCreation.member2_club)
async def process_member2_club(message: Message, state: FSMContext) -> None:
    await state.update_data(member2_club=_clean_optional(message.text))
    await state.set_state(TeamCreation.member2_achievements)
    await message.answer("Достижения второго участника:" + skip_hint())


@router.message(TeamCreation.member2_achievements)
async def process_member2_achievements(message: Message, state: FSMContext) -> None:
    await state.update_data(member2_achievements=_clean_optional(message.text))
    await state.set_state(TeamCreation.member2_username)
    await message.answer(
        "Username второго участника в Telegram (например, @username):"
    )


@router.message(TeamCreation.member2_username)
async def process_member2_username(message: Message, state: FSMContext, repo: Repo) -> None:
    raw_username = message.text.strip()
    if not raw_username.lstrip("@"):
        await message.answer("Укажите корректный username, например @username:")
        return
    username = normalize_username(raw_username)
    if username == normalize_username(message.from_user.username or ""):
        await message.answer(
            "Username второго участника не может совпадать с вашим. Укажите другой:"
        )
        return

    data = await state.get_data()
    member1 = {
        "name": data["member1_name"],
        "contact": data["member1_contact"],
        "club": data.get("member1_club"),
        "achievements": data.get("member1_achievements"),
        "telegram_id": message.from_user.id,
        "username": normalize_username(message.from_user.username or "") or None,
    }
    member2 = {
        "name": data["member2_name"],
        "contact": data["member2_contact"],
        "club": data.get("member2_club"),
        "achievements": data.get("member2_achievements"),
        "username": username,
    }

    team_id = await repo.create_team(data["title"], member1, member2)
    await state.clear()
    await message.answer(
        f"Заявка команды «{data['title']}» создана и ожидает подтверждения от @{username}.\n\n"
        f"Важно: попросите второго участника открыть этого бота и нажать /start — "
        f"бот сам предложит ему подтвердить участие. Telegram не позволяет написать "
        f"человеку первым, пока он не запустил бота.\n\n"
        f"Статус заявки можно посмотреть командой /status."
    )
