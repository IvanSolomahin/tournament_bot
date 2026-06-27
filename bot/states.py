from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class TeamCreation(StatesGroup):
    title = State()
    member1_name = State()
    member1_contact = State()
    member1_club = State()
    member1_achievements = State()
    member2_name = State()
    member2_contact = State()
    member2_club = State()
    member2_achievements = State()
    member2_username = State()


class TitleEdit(StatesGroup):
    new_title = State()


class BroadcastFlow(StatesGroup):
    message_text = State()
