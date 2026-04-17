from __future__ import annotations

from typing import Any

import psycopg


def _isbn_for_db(raw: str | None) -> str | None:
    s = (raw or "").strip()
    return s if s else None


def save_book_to_postgres(
    dsn: str,
    slug: str,
    metadata: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    paragraph_batch_size: int = 1000,
) -> None:
    """Persist one book: upsert ``books``, replace ``book_chapters`` and ``book_paragraphs``."""
    source_file = metadata["source_file"]
    title = metadata["title"]
    author = metadata.get("author") or ""
    language = metadata.get("language") or ""
    year = metadata.get("year")
    isbn = _isbn_for_db(metadata.get("isbn"))
    page_count = int(metadata["page_count"])
    chapters: list[str] = list(metadata["chapters"])
    raw_starts = metadata.get("chapter_start_pages")
    if isinstance(raw_starts, list) and len(raw_starts) == len(chapters):
        start_pages: list[int | None] = [x if isinstance(x, int) else None for x in raw_starts]
    else:
        start_pages = [None] * len(chapters)

    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            row = conn.execute(
                """
                INSERT INTO books (
                    slug, source_file, title, author, language, year, isbn, page_count,
                    processed, processed_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    true, now()
                )
                ON CONFLICT (slug) DO UPDATE SET
                    source_file = EXCLUDED.source_file,
                    title = EXCLUDED.title,
                    author = EXCLUDED.author,
                    language = EXCLUDED.language,
                    year = EXCLUDED.year,
                    isbn = EXCLUDED.isbn,
                    page_count = EXCLUDED.page_count,
                    processed = true,
                    processed_at = now()
                RETURNING id
                """,
                (
                    slug,
                    source_file,
                    title,
                    author,
                    language,
                    year,
                    isbn,
                    page_count,
                ),
            ).fetchone()
            if row is None:
                raise RuntimeError("upsert books returned no row")
            book_id = row[0]

            conn.execute(
                "DELETE FROM book_chapters WHERE book_id = %s",
                (book_id,),
            )
            conn.execute(
                "DELETE FROM book_paragraphs WHERE book_id = %s",
                (book_id,),
            )

            for sort_order, ch_title in enumerate(chapters):
                start_page = start_pages[sort_order]
                conn.execute(
                    """
                    INSERT INTO book_chapters (book_id, sort_order, title, start_page)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (book_id, sort_order, ch_title, start_page),
                )

            if chunks:
                with conn.cursor() as cur:
                    for i in range(0, len(chunks), paragraph_batch_size):
                        batch = chunks[i : i + paragraph_batch_size]
                        cur.executemany(
                            """
                            INSERT INTO book_paragraphs (
                                book_id, chapter, section, paragraph_index,
                                page_start, page_end, text
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            [
                                (
                                    book_id,
                                    c["chapter"],
                                    c["section"],
                                    c["paragraph_index"],
                                    c["page_start"],
                                    c["page_end"],
                                    c["text"],
                                )
                                for c in batch
                            ],
                        )
