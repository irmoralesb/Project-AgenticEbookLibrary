"""CRUD endpoints for the ebooks resource."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencies import get_repository
from api.schemas import EbookResponse, EbookUpdateRequest
from persistence.repositories.ebook_repository import EbookRepository

router = APIRouter(prefix="/api/ebooks", tags=["ebooks"])


@router.get("", response_model=list[EbookResponse])
def list_ebooks(
    skip: int = 0,
    limit: int = 100,
    repo: EbookRepository = Depends(get_repository),
) -> list[EbookResponse]:
    rows = repo.list_all(skip=skip, limit=limit)
    return [EbookResponse.model_validate(r) for r in rows]


@router.get("/{ebook_id}/cover")
def get_ebook_cover(
    ebook_id: uuid.UUID,
    repo: EbookRepository = Depends(get_repository),
) -> FileResponse:
    """Stream the extracted cover image from its on-disk path (sidecar PNG)."""
    row = repo.get_by_id(ebook_id)
    if row is None or not row.cover_image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover not found.")

    cover_path = Path(row.cover_image_path).expanduser().resolve()
    if not cover_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover file missing.")

    media_type = row.cover_image_mime_type or "image/png"
    return FileResponse(cover_path, media_type=media_type)


@router.get("/{ebook_id}", response_model=EbookResponse)
def get_ebook(
    ebook_id: uuid.UUID,
    repo: EbookRepository = Depends(get_repository),
) -> EbookResponse:
    row = repo.get_by_id(ebook_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found.")
    return EbookResponse.model_validate(row)


@router.put("/{ebook_id}", response_model=EbookResponse)
def update_ebook(
    ebook_id: uuid.UUID,
    body: EbookUpdateRequest,
    repo: EbookRepository = Depends(get_repository),
) -> EbookResponse:
    # Only send fields that were explicitly provided (exclude unset defaults).
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided for update.",
        )
    row = repo.update(ebook_id, data)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found.")
    return EbookResponse.model_validate(row)


@router.delete("/{ebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ebook(
    ebook_id: uuid.UUID,
    repo: EbookRepository = Depends(get_repository),
) -> None:
    deleted = repo.delete(ebook_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found.")
