"""FastAPI dependency injection for the Workspace Service."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.database import create_db_engine, create_session_factory

from app.config import get_settings
from app.repositories.member_repository import MemberRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.template_repository import TemplateRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.member_service import MemberService
from app.services.permission_service import WorkspacePermissionService
from app.services.session_service import SessionService
from app.services.workspace_service import WorkspaceService

settings = get_settings()

engine = create_db_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)
async_session_factory = create_session_factory(engine)

# Shared repository instances
workspace_repo = WorkspaceRepository()
member_repo = MemberRepository()
session_repo = SessionRepository()
template_repo = TemplateRepository()

# Shared service instances
permission_service = WorkspacePermissionService(member_repo=member_repo)
workspace_service = WorkspaceService(
    workspace_repo=workspace_repo,
    template_repo=template_repo,
    permission_service=permission_service,
)
member_service = MemberService(
    member_repo=member_repo,
    workspace_repo=workspace_repo,
    permission_service=permission_service,
)
session_service = SessionService(
    session_repo=session_repo,
    workspace_repo=workspace_repo,
    permission_service=permission_service,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_workspace_service() -> WorkspaceService:
    return workspace_service


def get_member_service() -> MemberService:
    return member_service


def get_session_service() -> SessionService:
    return session_service


def get_template_repo() -> TemplateRepository:
    return template_repo


def get_permission_service() -> WorkspacePermissionService:
    return permission_service


def get_workspace_repo() -> WorkspaceRepository:
    return workspace_repo
