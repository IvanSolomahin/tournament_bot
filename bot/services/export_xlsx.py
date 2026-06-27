from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from ..db.repo import Repo
from ..handlers.status import STATUS_LABELS

HEADERS = [
    "Команда",
    "Статус заявки",
    "Слот",
    "Имя участника",
    "Контакт",
    "Клуб",
    "Достижения",
    "Подтверждён в Telegram",
    "Оплата получена",
    "Check-in день 1",
    "Check-in день 2",
]


async def build_export_workbook(repo: Repo) -> BytesIO:
    """UC-17 / FR-5.14.1-5.14.8: build an in-memory XLSX with one row per member."""
    teams = await repo.list_teams()

    wb = Workbook()
    ws = wb.active
    ws.title = "Заявки"
    ws.append(HEADERS)

    for team in teams:
        members = await repo.get_members(team["id"])
        status_label = STATUS_LABELS.get(team["status"], team["status"])
        for m in members:
            ws.append(
                [
                    team["title"],
                    status_label,
                    m["slot"],
                    m["name"],
                    m["contact"],
                    m["club"] or "",
                    m["achievements"] or "",
                    "да" if m["telegram_id"] else "нет",
                    "да" if m["payment_confirmed_at"] else "нет",
                    "да" if m["checkin_day1_at"] else "нет",
                    "да" if m["checkin_day2_at"] else "нет",
                ]
            )

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
