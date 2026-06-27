from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ..db.repo import Repo
from ..models import TeamStatus

PAYMENT_ALLOWED_STATUSES = {
    TeamStatus.MAIN_LIST.value,
    TeamStatus.PARTICIPATION_CONFIRMED.value,
    TeamStatus.PARTIALLY_PAID.value,
}


class StatusEngine:
    def __init__(self, repo: Repo):
        self.repo = repo

    async def try_complete_registration(self, team_id: int) -> bool:
        """FR-5.3.4 / UC-04: move to `registered` once both members confirmed."""
        team = await self.repo.get_team(team_id)
        if team is None or team["status"] != TeamStatus.PENDING_CONFIRMATION.value:
            return False
        if not await self.repo.both_members_confirmed(team_id):
            return False
        await self.repo.update_team_status(team_id, TeamStatus.REGISTERED.value)
        await self.repo.log_action(team_id, None, "registration_completed")
        return True

    async def set_list_assignment(
        self, team_id: int, status: TeamStatus, actor_telegram_id: Optional[int]
    ) -> None:
        """FR-5.6.1/5.6.2: admin manually assigns main_list / waitlist."""
        if status not in (TeamStatus.MAIN_LIST, TeamStatus.WAITLIST):
            raise ValueError("status must be main_list or waitlist")
        await self.repo.update_team_status(team_id, status.value)
        await self.repo.log_action(team_id, actor_telegram_id, f"list_assigned:{status.value}")

    async def confirm_participation(self, team_id: int, actor_telegram_id: int) -> bool:
        """UC-08 / FR-5.7.x: only main_list teams may confirm participation."""
        team = await self.repo.get_team(team_id)
        if team is None or team["status"] != TeamStatus.MAIN_LIST.value:
            return False
        await self.repo.db.execute(
            "UPDATE teams SET status = ?, participation_confirmed_at = ? WHERE id = ?",
            (
                TeamStatus.PARTICIPATION_CONFIRMED.value,
                datetime.now(timezone.utc).isoformat(),
                team_id,
            ),
        )
        await self.repo.log_action(team_id, actor_telegram_id, "participation_confirmed")
        return True

    async def submit_payment(
        self, team_id: int, member_id: int, file_id: str, actor_telegram_id: int
    ) -> Optional[str]:
        """UC-09/10/11, FR-5.8.2-5.8.5: record one member's payment confirmation and
        auto-advance team status. Returns the new team status, or None if payment
        is not allowed for this team right now (FR-5.6.3/5.8.1, waitlist blocked)."""
        team = await self.repo.get_team(team_id)
        if team is None or team["status"] not in PAYMENT_ALLOWED_STATUSES:
            return None

        await self.repo.record_payment(member_id, file_id)
        await self.repo.log_action(team_id, actor_telegram_id, "payment_submitted")

        paid_count = await self.repo.count_payments(team_id)
        new_status = (
            TeamStatus.PAYMENT_CONFIRMED if paid_count >= 2 else TeamStatus.PARTIALLY_PAID
        )
        await self.repo.update_team_status(team_id, new_status.value)
        if new_status == TeamStatus.PAYMENT_CONFIRMED:
            await self.repo.log_action(team_id, None, "payment_confirmed")
        return new_status.value
