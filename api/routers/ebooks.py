"""CRUD endpoints for the ebooks resource."""

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from api.dependencies import get_repository
from api.schemas import (
    BatchReextractFieldJobRequest,
    EbookResponse,
    EbookUpdateRequest,
    IngestStartResponse,
    ReextractFieldRequest,
    ReextractFieldResponse,
)
from api.services.batch_reextract_field_service import run_batch_reextract_field_job
from api.services.field_reextract_service import reextract_field_for_ebook
from persistence.repositories.ebook_repository import EbookRepository

router = APIRouter(prefix="/api/ebooks", tags=["ebooks"])

_batch_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="batch_reextract")
_pending_batch_jobs: dict[str, BatchReextractFieldJobRequest] = {}


@router.get("", response_model=list[EbookResponse])
def list_ebooks(
    skip: int = 0,
    limit: int = 100,
    publisher: str | None = None,
    category: str | None = None,
    tags: str | None = None,
    tags_empty: bool | None = Query(default=None),
    has_errors: bool | None = Query(default=None),
    repo: EbookRepository = Depends(get_repository),
) -> list[EbookResponse]:
    rows = repo.list_all(
        skip=skip,
        limit=limit,
        publisher_contains=publisher.strip() if publisher else None,
        category_contains=category.strip() if category else None,
        tags_contains=tags.strip() if tags else None,
        tags_empty=tags_empty,
        has_errors=has_errors,
    )
    return [EbookResponse.model_validate(r) for r in rows]


@router.post(
    "/batch-reextract-field/start",
    response_model=IngestStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_batch_reextract_field(body: BatchReextractFieldJobRequest) -> IngestStartResponse:
    """Enqueue a batch re-extract job; connect to ``/batch-reextract-field/stream`` for progress."""
    job_id = str(uuid.uuid4())
    _pending_batch_jobs[job_id] = body
    return IngestStartResponse(
        job_id=job_id,
        message="Batch job enqueued. Connect to /api/ebooks/batch-reextract-field/stream?job_id={job_id} to follow progress.",
    )


async def _run_batch_reextract_stream(job_id: str):
    """Async generator: runs batch job in a thread and yields SSE lines."""
    request = _pending_batch_jobs.pop(job_id, None)
    if request is None:
        yield f"data: {json.dumps({'error': 'Unknown job_id'})}\n\n"
        return

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_progress(msg: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    def run_blocking() -> None:
        try:
            run_batch_reextract_field_job(request, on_progress=on_progress)
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)

    future = loop.run_in_executor(_batch_executor, run_blocking)

    while True:
        msg = await queue.get()
        if msg is None:
            break
        payload = json.dumps({"message": msg})
        yield f"data: {payload}\n\n"

    await future
    yield f"data: {json.dumps({'message': 'stream-end'})}\n\n"


@router.get("/batch-reextract-field/stream")
async def stream_batch_reextract_field(job_id: str) -> StreamingResponse:
    """Stream batch re-extract progress for *job_id* as Server-Sent Events."""
    return StreamingResponse(
        _run_batch_reextract_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.post("/{ebook_id}/reextract-field", response_model=ReextractFieldResponse)
def reextract_field(
    ebook_id: uuid.UUID,
    body: ReextractFieldRequest,
    repo: EbookRepository = Depends(get_repository),
) -> ReextractFieldResponse:
    row = repo.get_by_id(ebook_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found.")

    result = reextract_field_for_ebook(
        ebook=row,
        field=body.field,
        page_range=body.page_range,
        direction=body.direction,
    )
    return ReextractFieldResponse(
        field=result.field,
        value=result.value,
        used_start_page=result.used_start_page,
        used_end_page=result.used_end_page,
        direction=result.direction,
        message=result.message,
    )


@router.delete("/{ebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ebook(
    ebook_id: uuid.UUID,
    repo: EbookRepository = Depends(get_repository),
) -> None:
    deleted = repo.delete(ebook_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ebook not found.")
