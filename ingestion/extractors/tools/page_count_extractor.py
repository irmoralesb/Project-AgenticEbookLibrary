from fitz import Document
from ebooklib import epub


class PageCounterExtractor():

    def get_total_page_number_for_pdf(self, pdf_file: Document) -> int:
        return len(pdf_file)

    def get_total_spine_items_for_epub(self, book: epub.EpubBook) -> int:
        return len(list(book.spine))
