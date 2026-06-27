from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

SKIP = "-"


def skip_hint() -> str:
    return "\n\nЕсли поле не применимо, отправьте «-»."


def confirm_membership_kb(team_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Подтвердить участие в команде",
            callback_data=f"confirm_member:{team_id}",
        )
    )
    return builder.as_markup()


def confirm_participation_kb(team_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Подтвердить участие в турнире",
            callback_data=f"confirm_participation:{team_id}",
        )
    )
    return builder.as_markup()


def checkin_kb(day: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text=f"Подтвердить присутствие (день {day})",
            callback_data=f"checkin:{day}",
        )
    )
    return builder.as_markup()
