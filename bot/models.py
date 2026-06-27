from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TeamStatus(str, Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    REGISTERED = "registered"
    MAIN_LIST = "main_list"
    WAITLIST = "waitlist"
    PARTICIPATION_CONFIRMED = "participation_confirmed"
    PARTIALLY_PAID = "partially_paid"
    PAYMENT_CONFIRMED = "payment_confirmed"
    WITHDRAWN = "withdrawn"


@dataclass
class Member:
    id: int
    team_id: int
    slot: int
    name: str
    contact: str
    club: Optional[str]
    achievements: Optional[str]
    username: Optional[str]
    telegram_id: Optional[int]
    confirmed_at: Optional[str]
    payment_file_id: Optional[str]
    payment_confirmed_at: Optional[str]
    checkin_day1_at: Optional[str]
    checkin_day2_at: Optional[str]


@dataclass
class Team:
    id: int
    title: str
    status: str
    created_at: str
    participation_confirmed_at: Optional[str]
