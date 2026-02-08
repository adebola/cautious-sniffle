"""Public-facing document endpoints (routed through the Gateway)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from chatcraft_common.auth import CurrentUser, get_current_user
from chatcraft_common.pagination import PaginationParams

from app.dependencies import get_document_service, get_session
from app.schemas.document import DocumentResponse, DocumentUpdate, DocumentUploadResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# ------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------


@router.post("/", response_model=dict, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Upload a single document."""
    result = await service.upload_document(
        session=session,
        organization_id=user.organization_id,
        user_id=user.user_id,
        file=file,
        title=title,
        description=description,
    )
    return {"data": result.model_dump(mode="json")}


@router.post("/batch", response_model=dict, status_code=201)
async def upload_documents_batch(
    files: list[UploadFile] = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Upload multiple documents in one request."""
    results = await service.upload_documents_batch(
        session=session,
        organization_id=user.organization_id,
        user_id=user.user_id,
        files=files,
        title=title,
        description=description,
    )
    return {"data": [r.model_dump(mode="json") for r in results]}


# ------------------------------------------------------------------
# List
# ------------------------------------------------------------------


@router.get("/", response_model=dict)
async def list_documents(
    pagination: PaginationParams = Depends(),
    search: str | None = Query(None, description="Search filename, title, or description"),
    status: str | None = Query(None, description="Filter by processing status"),
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """List documents for the current organization."""
    result = await service.list_documents(
        session=session,
        organization_id=user.organization_id,
        page=pagination.page,
        page_size=pagination.page_size,
        search=search,
        status=status,
        sort_by=pagination.sort_by,
        sort_order=pagination.sort_order,
    )
    return result.model_dump(mode="json")


# ------------------------------------------------------------------
# Single document operations
# ------------------------------------------------------------------


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Retrieve a single document by ID."""
    result = await service.get_document(session, user.organization_id, document_id)
    return {"data": result.model_dump(mode="json")}


@router.put("/{document_id}", response_model=dict)
async def update_document(
    document_id: UUID,
    body: DocumentUpdate,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Update document metadata (title, description, document_type)."""
    result = await service.update_document(
        session=session,
        organization_id=user.organization_id,
        document_id=document_id,
        title=body.title,
        description=body.description,
        document_type=body.document_type,
    )
    return {"data": result.model_dump(mode="json")}


@router.delete("/{document_id}", response_model=dict)
async def delete_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Soft-delete a document and remove the file from storage."""
    await service.delete_document(session, user.organization_id, document_id)
    return {"data": {"deleted": True}}


@router.get("/{document_id}/download", response_model=dict)
async def get_download_url(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Get a presigned download URL for the document file."""
    url = await service.get_download_url(session, user.organization_id, document_id)
    return {"data": {"url": url}}


@router.post("/{document_id}/reprocess", response_model=dict)
async def reprocess_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    session=Depends(get_session),
    service: DocumentService = Depends(get_document_service),
):
    """Trigger reprocessing of an existing document."""
    result = await service.reprocess_document(session, user.organization_id, document_id)
    return {"data": result.model_dump(mode="json")}
