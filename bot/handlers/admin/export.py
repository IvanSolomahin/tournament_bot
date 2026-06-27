from __future__ import annotations

from datetime import datetime, timezone

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from ...config import Config
from ...db.repo import Repo
from ...services.export_xlsx import build_export_workbook

router = Router(name="admin_export")

NO_ACCESS = "У вас нет доступа к этой команде."


@router.message(Command("admin_export"))
async def export_teams(message: Message, repo: Repo, config: Config) -> None:
    if not config.is_admin(message.from_user.id):
        await message.answer(NO_ACCESS)
        return

    buffer = await build_export_workbook(repo)
    filename = f"teams_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.xlsx"
    await message.answer_document(
        BufferedInputFile(buffer.read(), filename=filename),
        caption="Экспорт заявок команд.",
    )
