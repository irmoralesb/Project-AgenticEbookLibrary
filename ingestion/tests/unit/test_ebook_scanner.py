from scanners.ebook_scanner import EbookScanner


def test_get_ebooks_from_path_returns_matching_files_recursively(tmp_path) -> None:
    root = tmp_path / "library"
    nested = root / "nested"
    nested.mkdir(parents=True)

    pdf_1 = root / "book-1.pdf"
    pdf_2 = nested / "book-2.PDF"
    epub = nested / "book-3.epub"
    pdf_1.write_text("dummy", encoding="utf-8")
    pdf_2.write_text("dummy", encoding="utf-8")
    epub.write_text("dummy", encoding="utf-8")

    scanner = EbookScanner()

    found = scanner.get_ebooks_from_path(str(root), ".pdf")
    assert sorted(found) == sorted([str(pdf_1), str(pdf_2)])
