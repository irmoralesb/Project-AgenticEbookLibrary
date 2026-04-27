"""FastAPI application entry point.

Start with:
    uv run uvicorn api.main:app --reload --port 8000
"""

import sys
from pathlib import Path

# Ensure ingestion/ sub-packages are importable when running from repo root.
_ingestion_root = Path(__file__).resolve().parent.parent / "ingestion"
if str(_ingestion_root) not in sys.path:
    sys.path.insert(0, str(_ingestion_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import ebooks, ingest, system

app = FastAPI(
    title="Agentic Ebook Library API",
    description="Metadata ingestion and management API for the Agentic Ebook Library.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:5173", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve extracted cover images at /covers/<filename>
_cover_dir = Path(__file__).resolve().parent.parent / "cover_images"
_cover_dir.mkdir(parents=True, exist_ok=True)
app.mount("/covers", StaticFiles(directory=str(_cover_dir)), name="covers")

app.include_router(ebooks.router)
app.include_router(ingest.router)
app.include_router(system.router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
