"""
BioOps Platform API Routers Package
"""

from .auth import router as auth_router
from .users import router as users_router
from .clients import router as clients_router
from .leads import router as leads_router
from .projects import router as projects_router
from .files import router as files_router
from .tasks import router as tasks_router
from .proposals import router as proposals_router
from .reports import router as reports_router
from .invoices import router as invoices_router
from .notifications import router as notifications_router
from .dashboard import router as dashboard_router
from .portal import router as portal_router
from .monitoring import router as monitoring_router

__all__ = [
    "auth_router",
    "users_router",
    "clients_router",
    "leads_router",
    "projects_router",
    "files_router",
    "tasks_router",
    "proposals_router",
    "reports_router",
    "invoices_router",
    "notifications_router",
    "dashboard_router",
    "portal_router",
    "monitoring_router",
]