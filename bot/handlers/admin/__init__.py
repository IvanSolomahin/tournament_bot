from aiogram import Router

from .applications import router as applications_router
from .broadcast import router as broadcast_router
from .export import router as export_router


def get_admin_router() -> Router:
    admin_root = Router(name="admin")
    admin_root.include_router(applications_router)
    admin_root.include_router(broadcast_router)
    admin_root.include_router(export_router)
    return admin_root
