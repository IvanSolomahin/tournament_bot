from aiogram import Router

from .common import router as common_router
from .start import router as start_router
from .registration import router as registration_router
from .confirmation import router as confirmation_router
from .status import router as status_router
from .team_edit import router as team_edit_router
from .participation import router as participation_router
from .payment import router as payment_router
from .checkin import router as checkin_router
from .admin import get_admin_router


def get_root_router() -> Router:
    root = Router(name="root")
    root.include_router(common_router)
    root.include_router(start_router)
    root.include_router(registration_router)
    root.include_router(confirmation_router)
    root.include_router(status_router)
    root.include_router(team_edit_router)
    root.include_router(participation_router)
    root.include_router(payment_router)
    root.include_router(checkin_router)
    root.include_router(get_admin_router())
    return root
