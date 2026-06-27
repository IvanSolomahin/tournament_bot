from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_username(username: str) -> str:
    return username.lstrip("@").lower()


class Repo:
    def __init__(self, db: Database):
        self.db = db

    async def activate_user(self, telegram_id: int, username: Optional[str]) -> None:
        existing = await self.db.fetchone(
            "SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        if existing is None:
            await self.db.execute(
                "INSERT INTO users (telegram_id, username, activated_at) VALUES (?, ?, ?)",
                (telegram_id, username, _now()),
            )
        else:
            await self.db.execute(
                "UPDATE users SET username = ? WHERE telegram_id = ?",
                (username, telegram_id),
            )

    async def create_team(
        self,
        title: str,
        member1: dict,
        member2: dict,
    ) -> int:
        cur = await self.db.execute(
            "INSERT INTO teams (title, status, created_at) VALUES (?, ?, ?)",
            (title, "pending_confirmation", _now()),
        )
        team_id = cur.lastrowid
        await self.db.execute(
            """INSERT INTO members
               (team_id, slot, name, contact, club, achievements, username, telegram_id, confirmed_at)
               VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)""",
            (
                team_id,
                member1["name"],
                member1["contact"],
                member1.get("club"),
                member1.get("achievements"),
                member1.get("username"),
                member1.get("telegram_id"),
                _now() if member1.get("telegram_id") else None,
            ),
        )
        await self.db.execute(
            """INSERT INTO members
               (team_id, slot, name, contact, club, achievements, username)
               VALUES (?, 2, ?, ?, ?, ?, ?)""",
            (
                team_id,
                member2["name"],
                member2["contact"],
                member2.get("club"),
                member2.get("achievements"),
                normalize_username(member2["username"]),
            ),
        )
        await self.log_action(team_id, member1.get("telegram_id"), "team_created")
        return team_id

    async def get_team(self, team_id: int):
        return await self.db.fetchone("SELECT * FROM teams WHERE id = ?", (team_id,))

    async def get_members(self, team_id: int):
        return await self.db.fetchall(
            "SELECT * FROM members WHERE team_id = ? ORDER BY slot", (team_id,)
        )

    async def get_team_by_member_telegram_id(self, telegram_id: int):
        row = await self.db.fetchone(
            "SELECT team_id FROM members WHERE telegram_id = ?", (telegram_id,)
        )
        if row is None:
            return None
        return await self.get_team(row["team_id"])

    async def get_unconfirmed_member_by_username(self, username: str):
        return await self.db.fetchone(
            """SELECT * FROM members
               WHERE username = ? AND telegram_id IS NULL""",
            (normalize_username(username),),
        )

    async def confirm_member(self, member_id: int, telegram_id: int) -> None:
        await self.db.execute(
            "UPDATE members SET telegram_id = ?, confirmed_at = ? WHERE id = ?",
            (telegram_id, _now(), member_id),
        )

    async def both_members_confirmed(self, team_id: int) -> bool:
        members = await self.get_members(team_id)
        return len(members) == 2 and all(m["telegram_id"] is not None for m in members)

    async def update_team_status(self, team_id: int, status: str) -> None:
        await self.db.execute(
            "UPDATE teams SET status = ? WHERE id = ?", (status, team_id)
        )

    async def update_team_title(self, team_id: int, title: str) -> None:
        await self.db.execute(
            "UPDATE teams SET title = ? WHERE id = ?", (title, team_id)
        )

    async def log_action(
        self, team_id: int, actor_telegram_id: Optional[int], action: str
    ) -> None:
        await self.db.execute(
            "INSERT INTO action_log (team_id, actor_telegram_id, action, created_at) VALUES (?, ?, ?, ?)",
            (team_id, actor_telegram_id, action, _now()),
        )

    async def list_teams(self):
        return await self.db.fetchall("SELECT * FROM teams ORDER BY created_at DESC")

    async def get_action_log(self, team_id: int):
        return await self.db.fetchall(
            "SELECT * FROM action_log WHERE team_id = ? ORDER BY created_at", (team_id,)
        )

    async def get_member_by_telegram_id(self, telegram_id: int):
        return await self.db.fetchone(
            "SELECT * FROM members WHERE telegram_id = ?", (telegram_id,)
        )

    async def record_payment(self, member_id: int, file_id: str) -> None:
        await self.db.execute(
            "UPDATE members SET payment_file_id = ?, payment_confirmed_at = ? WHERE id = ?",
            (file_id, _now(), member_id),
        )

    async def count_payments(self, team_id: int) -> int:
        members = await self.get_members(team_id)
        return sum(1 for m in members if m["payment_confirmed_at"] is not None)

    async def record_checkin(self, member_id: int, day: int) -> None:
        column = "checkin_day1_at" if day == 1 else "checkin_day2_at"
        await self.db.execute(
            f"UPDATE members SET {column} = ? WHERE id = ?", (_now(), member_id)
        )

    async def list_members_by_status(self, statuses: list):
        placeholders = ",".join("?" for _ in statuses)
        return await self.db.fetchall(
            f"""SELECT members.*, teams.title AS team_title, teams.status AS team_status
                FROM members JOIN teams ON teams.id = members.team_id
                WHERE teams.status IN ({placeholders}) AND members.telegram_id IS NOT NULL""",
            tuple(statuses),
        )

    async def list_pending_creators(self):
        """Creators (slot 1) of teams still waiting for the second member to confirm."""
        return await self.db.fetchall(
            """SELECT members.*, teams.title AS team_title
               FROM members JOIN teams ON teams.id = members.team_id
               WHERE teams.status = 'pending_confirmation' AND members.slot = 1"""
        )
