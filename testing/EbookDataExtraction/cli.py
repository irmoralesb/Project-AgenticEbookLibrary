from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from EbookDataExtraction.extract import process_pdf


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Extract PDF ebooks into output for RAG.")
    p.add_argument(
        "--input",
        type=Path,
        default=Path("ebooks"),
        help="Directory containing PDF files (default: ./ebooks)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output root (default: ./output)",
    )
    p.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Project root for relative source_file paths (default: cwd)",
    )
    p.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        metavar="URL",
        help="PostgreSQL URL (default: DATABASE_URL env; if unset, skip DB)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    project_root = (args.project_root or Path.cwd()).resolve()
    input_dir = args.input.resolve()
    output_root = args.output.resolve()

    if not input_dir.is_dir():
        print(f"Input is not a directory: {input_dir}", file=sys.stderr)
        return 1

    pdfs = sorted(input_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files in {input_dir}", file=sys.stderr)
        return 1

    ok = 0
    for pdf in pdfs:
        try:
            meta, n = process_pdf(
                pdf, project_root, output_root, database_url=args.database_url
            )
            if args.verbose:
                print(
                    f"OK {pdf.name}: {n} chunks, title={meta.get('title')!r}, "
                    f"isbn={meta.get('isbn')!r}"
                )
            else:
                print(f"OK {pdf.name} ({n} chunks)")
            ok += 1
        except Exception as e:
            print(f"FAIL {pdf.name}: {e}", file=sys.stderr)

    if ok == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
