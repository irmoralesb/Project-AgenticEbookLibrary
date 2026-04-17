from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def book_slug(source_path: Path) -> str:
    stem = source_path.stem
    s = re.sub(r"[^\w\s\-]", "", stem, flags=re.UNICODE)
    s = re.sub(r"[\s\-]+", "_", s.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:120] or "book").lower()


def write_book(
    storage_root: Path,
    slug: str,
    metadata: dict[str, Any],
    chunks: list[dict[str, Any]],
) -> None:
    out_dir = storage_root / "books" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    chunks_path = out_dir / "chunks.jsonl"
    with chunks_path.open("w", encoding="utf-8") as f:
        for row in chunks:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
