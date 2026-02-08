"""Templates router - /api/v1/workspace-templates."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from chatcraft_common.auth import CurrentUser, get_current_user

from app.dependencies import get_db, get_template_repo
from app.repositories.template_repository import TemplateRepository
from app.schemas.template import TemplateResponse

router = APIRouter(prefix="/api/v1/workspace-templates", tags=["templates"])


@router.get("/")
async def list_templates(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    repo: TemplateRepository = Depends(get_template_repo),
):
    """List all active workspace templates."""
    templates = await repo.list_active(db)
    return {
        "data": [
            TemplateResponse.model_validate(t).model_dump(mode="json")
            for t in templates
        ]
    }
