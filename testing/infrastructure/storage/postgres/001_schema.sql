-- Library ebook storage: metadata, chapter outline, extracted text.
-- Target: PostgreSQL 14+ (uses gen_random_uuid()).

-- -----------------------------------------------------------------------------
-- Books: one row per source PDF / ebook file.
-- -----------------------------------------------------------------------------
CREATE TABLE books (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Stable id derived from filename (see book_slug in application code).
    slug text NOT NULL,

    -- Relative path under the project, POSIX-style (matches metadata.source_file).
    source_file text NOT NULL,

    title text NOT NULL,
    author text NOT NULL DEFAULT '',
    language text NOT NULL DEFAULT '',
    year smallint,

    -- Normalized digits-only ISBN-13 (preferred) or ISBN-10; empty in app = NULL in DB.
    isbn text,

    page_count integer NOT NULL CHECK (page_count >= 0),

    -- Processing pipeline: set processed = true and processed_at when extraction finished.
    processed boolean NOT NULL DEFAULT false,
    processed_at timestamptz,

    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT books_slug_unique UNIQUE (slug),
    CONSTRAINT books_source_file_unique UNIQUE (source_file),
    CONSTRAINT books_processed_at_consistent CHECK (
        (processed = false AND processed_at IS NULL)
        OR (processed = true AND processed_at IS NOT NULL)
    )
);

CREATE INDEX idx_books_processed ON books (processed) WHERE NOT processed;
CREATE INDEX idx_books_isbn ON books (isbn) WHERE isbn IS NOT NULL;

COMMENT ON COLUMN books.isbn IS 'ISBN-13 or ISBN-10, normalized (typically digits-only).';

COMMENT ON TABLE books IS 'Ebook metadata and processing status.';
COMMENT ON COLUMN books.processed IS 'True when metadata and text extraction completed successfully.';
COMMENT ON COLUMN books.processed_at IS 'Timestamp when processing completed; NULL if not yet processed or failed before completion.';

-- -----------------------------------------------------------------------------
-- Chapter list per book (from TOC / outline; order matches metadata.chapters).
-- -----------------------------------------------------------------------------
CREATE TABLE book_chapters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    book_id uuid NOT NULL REFERENCES books (id) ON DELETE CASCADE,

    sort_order integer NOT NULL CHECK (sort_order >= 0),
    title text NOT NULL,

    -- Optional: PDF page where the chapter starts (from TOC when available).
    start_page integer CHECK (start_page IS NULL OR start_page >= 1),

    CONSTRAINT book_chapters_book_sort_unique UNIQUE (book_id, sort_order)
);

CREATE INDEX idx_book_chapters_book_id ON book_chapters (book_id);

COMMENT ON TABLE book_chapters IS 'Ordered chapter titles for each book (outline).';

-- -----------------------------------------------------------------------------
-- Extracted text: paragraph-level chunks (matches chunks.jsonl rows).
-- -----------------------------------------------------------------------------
CREATE TABLE book_paragraphs (
    id bigserial PRIMARY KEY,
    book_id uuid NOT NULL REFERENCES books (id) ON DELETE CASCADE,

    chapter text NOT NULL DEFAULT '',
    section text NOT NULL DEFAULT '',
    paragraph_index integer NOT NULL CHECK (paragraph_index > 0),

    page_start integer NOT NULL CHECK (page_start >= 1),
    page_end integer NOT NULL CHECK (page_end >= 1),

    text text NOT NULL,

    CONSTRAINT book_paragraphs_page_range CHECK (page_end >= page_start),
    CONSTRAINT book_paragraphs_book_chapter_paragraph_unique UNIQUE (book_id, chapter, section, paragraph_index)
);

CREATE INDEX idx_book_paragraphs_book_id ON book_paragraphs (book_id);

COMMENT ON TABLE book_paragraphs IS 'Extracted paragraph text with chapter/section labels and page span.';

-- -----------------------------------------------------------------------------
-- Keep updated_at in sync on books (optional; application may also set it).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_books_updated_at
    BEFORE UPDATE ON books
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();
