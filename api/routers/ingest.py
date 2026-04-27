"""Ingestion trigger and SSE progress-stream endpoints.

Design:
- POST /api/ingest/start  stores the IngestRequest in an in-process registry
  keyed by a job_id UUID and returns immediately.
- GET  /api/ingest/stream runs the ingestion synchronously inside a
  ThreadPoolExecutor so the blocking LLM calls do not stall the event loop,
  and streams each progress message as an SSE event to the caller.
"""

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from api.schemas import IngestRequest, IngestStartResponse

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")

# In-process job store: job_id -> IngestRequest.
# A single-worker executor guarantees at most one job runs at a time.
_pending_jobs: dict[str, IngestRequest] = {}


@router.post("/start", response_model=IngestStartResponse, status_code=202)
def start_ingest(body: IngestRequest) -> IngestStartResponse:
    """Enqueue an ingestion job and return a job_id to pass to /stream."""
    job_id = str(uuid.uuid4())
    _pending_jobs[job_id] = body
    return IngestStartResponse(
        job_id=job_id,
        message="Ingestion job enqueued. Connect to /api/ingest/stream?job_id={job_id} to follow progress.",
    )


async def _run_ingestion_stream(job_id: str):
    """Async generator that runs ingestion in a thread and yields SSE lines."""
    request = _pending_jobs.pop(job_id, None)
    if request is None:
        yield f"data: {json.dumps({'error': 'Unknown job_id'})}\n\n"
        return

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_progress(msg: str) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, msg)

    def run_blocking() -> None:
        # Imported inside the thread function to keep the ingestion package
        # free of any FastAPI import at module load time.
        from ingestion.main import run_ingestion  # noqa: PLC0415

        try:
            run_ingestion(
                path=request.path,
                extension=request.extension,
                limit=request.limit,
                cover_image_path=request.cover_image_path,
                on_progress=on_progress,
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    future = loop.run_in_executor(_executor, run_blocking)

    while True:
        msg = await queue.get()
        if msg is None:
            break
        payload = json.dumps({"message": msg})
        yield f"data: {payload}\n\n"

    await future  # propagate any exception from the thread
    yield f"data: {json.dumps({'message': 'stream-end'})}\n\n"


@router.get("/stream")
async def stream_ingest(job_id: str) -> StreamingResponse:
    """Stream ingestion progress for *job_id* as Server-Sent Events."""
    return StreamingResponse(
        _run_ingestion_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
