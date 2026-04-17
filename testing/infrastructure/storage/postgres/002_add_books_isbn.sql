-- Add ISBN to books (apply if you already ran 001_schema.sql before isbn existed).
ALTER TABLE books ADD COLUMN IF NOT EXISTS isbn text;

COMMENT ON COLUMN books.isbn IS 'ISBN-13 or ISBN-10, normalized (typically digits-only).';

CREATE INDEX IF NOT EXISTS idx_books_isbn ON books (isbn) WHERE isbn IS NOT NULL;
